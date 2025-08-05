from dataclasses import dataclass
from langchain_community.document_loaders import PyPDFLoader

@dataclass
class PdfParser:

    def __post_init__(self):
        pass

    def parse(self, file_path):
        loader = PyPDFLoader(file_path)
        documents = loader.load()
        text = "\n\n".join([doc.page_content for doc in documents])
        return text


if __name__ == "__main__":
    pass