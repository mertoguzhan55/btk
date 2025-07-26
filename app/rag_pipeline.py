from dataclasses import dataclass
import os
import json
from typing import List
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
import uuid


@dataclass
class Note:
    id: int
    label: str
    note: str

@dataclass
class NoteChunk:
    id: str
    subject_id: str
    label: str
    content: str


@dataclass
class RagPipeline:
    model_name: str
    vector_db_directory: str
    logger: any

    def __post_init__(self):
        self.logger.info("Initializing embedding model...")
        self.embedding_model = GoogleGenerativeAIEmbeddings(model=str(self.model_name))

        self.db_path = self.vector_db_directory
        self.vectorstore = None

        if os.path.exists(self.db_path) and os.listdir(self.db_path):
            self.logger.info(f"Loading existing FAISS vectorstore from {self.db_path}...")
            self.vectorstore = FAISS.load_local(
                self.db_path,
                self.embedding_model,
                allow_dangerous_deserialization=True
            )
            self.logger.info("Vectorstore loaded successfully.")
        else:
            self.logger.info("No existing vectorstore found. It will be initialized on first update.")
            self.vectorstore = None

    def load_notes(self, json_path: str, subject_id: str) -> List[NoteChunk]:
        self.logger.info(f"Loading notes from JSON file: {json_path}")
        with open(json_path, "r", encoding="utf-8") as f:
            notes = json.load(f)

        chunks = []
        for note in notes:
            chunks.append(NoteChunk(
                id=str(uuid.uuid4()),
                subject_id=subject_id,
                label=note["label"],
                content=note["note"]
            ))
        self.logger.info(f"{len(chunks)} notes loaded and converted to NoteChunk objects for subject '{subject_id}'.")
        return chunks

    def update_vector_db(self, note_chunks: List[NoteChunk]):
        if not note_chunks:
            self.logger.info("No note chunks provided. Skipping vectorstore update.")
            return

        self.logger.info(f"Updating vectorstore with {len(note_chunks)} new note chunks...")
        documents = [
            Document(
                page_content=chunk.content,
                metadata={"label": chunk.label, "subject_id": chunk.subject_id}
            )
            for chunk in note_chunks
        ]

        if self.vectorstore is None:
            self.logger.info("Creating new FAISS vectorstore from scratch.")
            self.vectorstore = FAISS.from_documents(documents, self.embedding_model)
        else:
            self.logger.info("Adding documents to existing vectorstore.")
            self.vectorstore.add_documents(documents)

        self.vectorstore.save_local(self.db_path)
        self.logger.info("Vectorstore saved successfully.")

    def query(self, query: str, k: int = 1):
        self.logger.info(f"Performing similarity search for query: '{query}' (top {k} results)")
        results = self.vectorstore.similarity_search(query, k=k)
        self.logger.info(f"{len(results)} results retrieved from vectorstore.")
        return results

if __name__ == "__main__":
    # Kullanıcı yeni not eklediğinde:
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
    pipeline = RagPipeline(**config, logger=logger)

    # Örneğin kimya.json gibi bir dosyadan oku
    note_chunks = pipeline.load_notes("app/data/kimya.json", subject_id="kimya")
    pipeline.update_vector_db(note_chunks)

    # Arama yapmak için:
    results = pipeline.query("tepkimede hız")
    for r in results:
        print(r.page_content, "→", r.metadata["label"])