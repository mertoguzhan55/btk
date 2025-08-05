from dataclasses import dataclass
from langchain_core.runnables import Runnable
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.rag_pipeline import RagPipeline
from dotenv import load_dotenv

@dataclass
class Chatbot:
    
    rag_pipeline: RagPipeline
    model_name: str
    logger: any
    temperature: float = 0.2

    def __post_init__(self):
        load_dotenv()
        self.logger.info("Initializing Chat LLM...")
        self.llm = ChatGoogleGenerativeAI(model=self.model_name, temperature=self.temperature)

        self.prompt_template = PromptTemplate.from_template(
            """
            You are a helpful assistant specialized in the subject "{subject_id}".
            Only answer questions that are relevant to the subject "{subject_id}".
            If the question is unrelated, politely respond with something like:
            "I'm the assistant for the subject '{subject_id}'. Please ask questions related to this topic." if the question is in english,
            "ben {subject_id} asistanıyım. Bunun ile ilgili soru sormanızı rica ediyorum." if the question is in Turkish.

            If the question is in Turkish, answer in Turkish.
            If the question is in English, answer in English.

            Previous Conversation:
            {context}

            Context:
            {context}

            Question:
            {question}

            Answer:
            """
        )
        self.output_parser = StrOutputParser()

    def ask_question(self, subject_id: str, question: str, user_id: int, top_k: int = 3):

        self.logger.info(f"Asking question for subject '{subject_id}' by user {user_id}: {question}")
        
        results_with_scores = self.rag_pipeline.query_with_scores(question, user_id=user_id, k=top_k)

        self.logger.info(f"results from RAG: {results_with_scores}")

        filtered_results = [
            (doc, score) for doc, score in results_with_scores
            if doc.metadata.get("subject_id") == subject_id
        ]

        if not filtered_results:
            self.logger.warning("No relevant context found. Returning fallback answer.")
            # return "Bu konuda yeterli bilgi bulunamadı."

        context = "\n".join([doc.page_content for doc, _ in filtered_results])

        chain = self.prompt_template | self.llm | self.output_parser
        answer = chain.invoke({
            "context": context,
            "question": question,
            "subject_id": subject_id
        })

        return answer


if __name__ == "__main__":
    from app.logger import Logger

    logger_config = {
        "filepath":"./logs/base.log",
        "rotation":"50MB"
    }

    logger = Logger(**logger_config)

    config = {
        "model_name" : "models/gemini-embedding-exp-03-07", 
        "vector_db_directory": "vector_db"
    }
    rag_pipeline = RagPipeline(**config, logger=logger)

    chatbot = Chatbot(
        rag_pipeline=rag_pipeline,
        model_name="gemini-2.5-flash",
        logger=logger
    )

    response = chatbot.ask_question(subject_id="kimya", question="Amerikan başkanı kim?")
    print("Yanıt:", response)
