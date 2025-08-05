from dataclasses import dataclass
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

@dataclass
class Summarizer:

    summarizer_model_name: str

    def __post_init__(self):
        load_dotenv()
        self.llm = ChatGoogleGenerativeAI(model=self.summarizer_model_name)


    def sumarize(self, text):
        prompt = f"Aşağıdaki metni açık, kısa ve öz bir şekilde özetle:\n\n{text}"
        response = self.llm.invoke(prompt)
        return response.content.strip() if response and hasattr(response, "content") else ""


if __name__ == "__main__":
    pass