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
        self.logger.info("Embedding model initializing...")
        self.embedding_model = GoogleGenerativeAIEmbeddings(model=self.model_name)

    def load_notes(self, json_path: str, subject_id: str, user_id: int) -> List[NoteChunk]:
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
        self.logger.info(f"{len(chunks)} notes loaded and converted to NoteChunk objects for subject '{subject_id}' and user {user_id}.")
        return chunks

    def update_vector_db(self, note_chunks: List[NoteChunk], user_id: int):
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

        user_db_path = os.path.join(self.vector_db_directory, f"user_{user_id}")
        os.makedirs(user_db_path, exist_ok=True)  # 👈 Klasörü burada da garantile

        if os.listdir(user_db_path):  # 👈 içi doluysa yükle ve ekle
            self.logger.info(f"Loading existing vectorstore for user {user_id}")
            vectorstore = FAISS.load_local(
                user_db_path,
                self.embedding_model,
                allow_dangerous_deserialization=True
            )
            vectorstore.add_documents(documents)
        else:
            self.logger.info(f"Creating new vectorstore for user {user_id}")
            vectorstore = FAISS.from_documents(documents, self.embedding_model)

        vectorstore.save_local(user_db_path)  # 👈 dosyayı user_{id} klasörüne kaydet
        self.logger.info(f"Vectorstore saved to {user_db_path}")


    def query_with_scores(self, query: str, user_id: int, k: int = 3):

        user_db_path = os.path.join(self.vector_db_directory, f"user_{user_id}")
        if not os.path.exists(user_db_path):
            self.logger.warning(f"No vectorstore found for user {user_id}. Returning empty results.")
            return []

        vectorstore = FAISS.load_local(
            user_db_path,
            self.embedding_model,
            allow_dangerous_deserialization=True
        )

        self.logger.info(f"Querying vectorstore for user {user_id} with query: '{query}'")
        results_with_scores = vectorstore.similarity_search_with_score(query, k=k)
        return results_with_scores



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
    results_with_scores = pipeline.query_with_scores("tepkimede hız", k=3)
    for i, (doc, score) in enumerate(results_with_scores, start=1):
        print(f"[{i}] Skor: {score:.4f}")
        print(f"İçerik: {doc.page_content}")
        print(f"Etiket: {doc.metadata['label']}\n")