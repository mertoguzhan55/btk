from dataclasses import dataclass
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Union
import xml.etree.ElementTree as ET
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import AIMessage
from langchain.agents import AgentType, Tool, initialize_agent
from langchain.chains import LLMChain
import json
from langchain_core.tools import tool
from langchain.prompts import PromptTemplate
import requests
from app.rag_pipeline import RagPipeline
import os
from dotenv import load_dotenv

@dataclass
class ChallengeGenerator:

    logger: any

    def __post_init__(self):
        load_dotenv()
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=0.2
        )

        @tool
        def quiz_generate(student_quiz_keywords: str, user_id: str) -> dict:
            """
            Öğrencinin verdiği konuya göre Zor olan 10 çoktan seçmeli (MCQ) soru üret.
            Her soru A, B, C, D ve E şıkları içermeli ve doğru cevabı belirtmelidir.
            """

            prompt = f"""
            Sen bir öğretmen agentsin. Öğrencinin verdiği konuya göre 10 adet çoktan seçmeli (MCQ) soru üret.

            Konu: {student_quiz_keywords}

            Eğer Konu anlamsız bir kelime veya cümle ise çoktan seçmeli soru OLUŞTURMA.

            Kurallar:
            - Her soru 1 doğru ve 4 yanlış şık içermeli (toplam 5: A, B, C, D, E).
            - Şıkları karıştır.
            - Cevapları sondaki JSON formatında listele: 
            [
                {{
                    "question": "....",
                    "choices": {{"A": "...", "B": "...", "C": "...", "D": "...", "E": "..."}},
                    "correct_answer": "B"
                }},
                ...
            ]

            Sadece bu formatta dön.
            """
            result = self.llm.invoke(prompt)

            self.logger.info(f"Model output (raw): {repr(result.content)}")

            try:
                clean_content = self.extract_json_from_code_block(result.content)
                self.logger.info(f"Cleaned content: {clean_content}")
                questions = json.loads(clean_content)
                self.logger.info(f"Cleaned content questions: {questions}")
                return {"questions": questions}
            except Exception as e:
                self.logger.error(f"[JSON parse hatası: {e}]")
                return {"questions": []}

        self.quiz_generate = quiz_generate  # self'e atıyoruz


        @tool
        def evaluate_answer_tool(question: str, student_answer: str, correct_answer: str, user_id: str) -> dict:
            """
            Öğrencinin verdiği cevabı değerlendir.

            Doğruysa: 10 puan + tebrik mesajı  
            Yanlışsa: 0 puan + neden yanlış olduğunu açıklayan detaylı geri bildirim
            """
            if student_answer == correct_answer:
                return {
                    "feedback": f"✅ Doğru cevap! Cevabın ({student_answer}) doğru.",
                    "score": 10.0
                }
            
            # Eğer cevap yanlışsa, açıklayıcı geri bildirim ver
            prompt = f"""
            Sen bir öğretmensin. Aşağıda çoktan seçmeli bir soru, öğrencinin cevabı ve doğru cevap verilmiştir.

            Soru:
            {question}

            Öğrencinin cevabı: {student_answer}
            Doğru cevap: {correct_answer}

            Lütfen öğrenciye samimi, anlaşılır ve öğretici bir geri bildirim ver:

            - Neden bu cevabın doğru olmadığını açıkla.
            - Doğru cevabın neden doğru olduğunu sade bir dille belirt.
            - Öğrenciyi teşvik et, motive edici bir cümleyle bitir.
            - **Başlık veya yapay ayrımlar kullanma** (örneğin: "Doğru cevap:", "Yanlış cevap:", "Cesaretlendirme:" gibi ifadelerden kaçın).
            - Dil sade, profesyonel ve cesaret verici olsun.
            - doğru cevabın, doğru şıkkın {correct_answer} olduğunu mutlaka cümle içerisinde belirt.

            Geri bildirim:
            """

            try:
                response = self.llm.invoke(prompt)
                feedback = response.content.strip()
            except Exception as e:
                self.logger.error(f"LLM feedback hatası: {e}")
                feedback = "Cevabın yanlış. Doğru cevabı kontrol etmeni öneririm."

            return {
                "feedback": f"❌ {feedback}",
                "score": 0.0
            }

        self.evaluate_answer_tool = evaluate_answer_tool

    def extract_json_from_code_block(self, text: str) -> str:
        """
        LLM çıktısı eğer ```json ... ``` formatında gelirse, sadece JSON içeriğini çıkarır.
        """
        text = text.strip()

        if text.startswith("```json"):
            return text.removeprefix("```json").removesuffix("```").strip()
        elif text.startswith("```"):
            return text.removeprefix("```").removesuffix("```").strip()
        return text

    def run(self, student_quiz_keywords: str, user_id: str) -> dict:
        model = self.llm.bind_tools([self.quiz_generate, self.evaluate_answer_tool])

        prompt = f"""
            Use the tool `quiz_generate` to generate a quiz for the following topic and user_id.

            student_quiz_keywords: {student_quiz_keywords}
            user_id: {user_id}
        """

        response = model.invoke(prompt)
        self.logger.info(f"ai agent response: {response}")

        if isinstance(response, AIMessage) and response.tool_calls:
            for tool_call in response.tool_calls:
                if tool_call["name"] == "quiz_generate":
                    args = tool_call["args"]
                    quiz_result = self.quiz_generate.invoke(args)
                    return quiz_result  # {"questions": [...]}

        return {"questions": []}
    
    def evaluate(self, question: str, student_answer: str, correct_answer:str,  user_id: str) -> dict:
        return self.evaluate_answer_tool.invoke({
            "question": question,
            "student_answer": student_answer,
            "correct_answer": correct_answer,
            "user_id": user_id
        })

        




if __name__ == "__main__":
    pass