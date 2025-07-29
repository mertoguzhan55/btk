from dataclasses import dataclass
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv
import os 
 

@dataclass
class LabelExtractor:

    model_name: str # gemini-2.0-flash" or "gemini-pro"
    logger:any
    temperature: float = 0.2
    max_retries: int = 2

    def __post_init__(self):
        load_dotenv()
        self.GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
        if not self.GOOGLE_API_KEY:
            self.logger.error("GOOGLE_API_KEY environment variable not set.")
            raise ValueError("GOOGLE_API_KEY environment variable not set.")

    def extract(self, subject_id, text):
        """
        Gemini modelini kullanarak verilen metni etiketler.
        Metni temsil eden bir veya birkaç anahtar kelime/etiket döndürür.
        """
        llm = ChatGoogleGenerativeAI(model=self.model_name, temperature=self.temperature)

        prompt_template = PromptTemplate.from_template(
            f"""
            Read the following text about {subject_id} and label it with 1 to 3 comma-separated keywords or short phrases that best describe it.
            Return only the keywords/phrases, add nothing else.

            Text:
            {text}

            Labels:
            """
        )
        labeling_chain = prompt_template | llm | StrOutputParser()

        labels = labeling_chain.invoke({"text": text})
        label = labels.strip().split(",")[0]

        self.logger.info(f"extractor extract like this: {label}")
        return label



if __name__ == "__main__":
    from app.logger import Logger
    logger_config = {
        "filepath":"./logs/base.log",
        "rotation":"50MB"
    }
    logger = Logger(**logger_config)

    label_extractor_config = {
        "model_name" : "gemini-2.5-flash", # gemini-2.0-flash"
        "temperature" : 0.2,
        "max_retries" : 2
    }

    extractor = LabelExtractor(**label_extractor_config, logger=logger)
    text = """
    Karbon atomunun ayrı bir kimyasının olmasının nedeni; karbon atomunun elektroniközelliğinden ve bağ yapma kabiliyetinden ileri gelir.Karbon atomu kendisiyle düz zincir halinde, dallanmıĢ ve halkalı kararlı bileĢiklermeydana getirebilir. Karbon atomu bir baĢka karbon atomu veya oksijen, kükürt gibi baĢka biratomla tekli, ikili ve üçlü bağlar oluĢturarak sağlam yapılı bileĢikler oluĢtururlar. Bu önemliözellik baĢka atomlarda yoktur. Ġnorganik bileĢikler iyonik yapılı olduklarından suda iyiçözünürler. Organik bileĢikler ise kovalent yapılı olduklarından suda çözünmez. Fakat eter,benzen, karbontetraklorür gibi çözücülerde iyi çözünürler. Anorganik bileĢikler yanmaözelliği göstermezken, organik bileĢiklerde yanma özelliği gözlenir. Anorganik bileĢiklerdeizomere çok az rastlanır. Organik bileĢiklerde ise oldukça çok rastlanır. (Kapalı formülleriaynı açık formülleri farklı olan bileĢiklere izomer bileĢikler denir.) Anorganik bileĢikleriyonik reaksiyonlar verirken organik bileĢikler moleküler reaksiyon verirler. OrganikbileĢikleri karbon veya hidrojen bileĢikleri veya onların türevleri olarak tanımlamakmümkündür. Gerçekten hidrojen bulundurmayan organik bileĢiklerin sayısı çok azdır
    """
    
    extractor.extract(text)