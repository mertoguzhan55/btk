from dataclasses import dataclass
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
class FlashCardAgent:

    logger: any

    def __post_init__(self):
        load_dotenv()
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=0.2
        )
        self.flashcard_prompt = PromptTemplate.from_template(
            "Sen bir eğitim uzmanısın. Öğrenci bu soruda hata yaptı:\n\n"
            "Soru: {question}\n"
            "Kullanıcı bu soruya bu cevabı verdi : {user_answer}"
            "Bu sorunun genel olarak konusu ne ise hızlı ve bilgilendirici flashcardlar içerisinde bunu anlat."
            "Bu sorunun konusunu çok uzun tutma, önemli noktaları anlat."
        )

    def generate_advice_for_wrong_answers(self, wrong_answers: List[dict]) -> List[str]:
        """
        LLM kullanarak her yanlış cevap için detaylı konu anlatımı üretir.

        Args:
            wrong_answers (List[dict]): Her biri {'question', 'user_answer', 'correct_answer'} içeren liste.

        Returns:
            List[str]: Her yanlış cevap için üretilen açıklamalar listesi.
        """
        explanations = []

        for item in wrong_answers:
            prompt = self.flashcard_prompt.format(
                question=item["question"],
                user_answer=item["user_answer"]
            )
            try:
                response = self.llm.invoke(prompt)
                explanations.append(response.content)
            except Exception as e:
                self.logger.error(f"LLM cevabı alınamadı: {e}")
                explanations.append("Açıklama üretilemedi.")
        
        return explanations