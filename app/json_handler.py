from dataclasses import dataclass
import json
import os
from typing import List, Dict, Union
from pydantic import BaseModel, Field


class NoteEntry(BaseModel):
    """
    JSON dosyasına kaydedilecek her bir not kaydını temsil eder.
    """
    id: int
    label: str
    note: str

@dataclass
class JsonHandler:

    directory: str
    logger: any

    def __post_init__(self):
        pass

    def _load_data(self, subject_id: str) -> List[NoteEntry]:
        """
        Belirtilen subject_id'ye ait JSON dosyasını yükler.
        Dosya yoksa boş bir liste döndürür.
        """
        filepath = self.directory + f"/{subject_id}.json"

        print(f"file_path: {filepath}")

        if not os.path.exists(filepath):
            raise FileNotFoundError(f"{subject_id}.json dosyası bulunamadı: {filepath}")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)

            return [NoteEntry(**item) for item in raw_data]
        
    
    def _save_data(self, subject_id: str, data: List[NoteEntry]):
        """
        Veriyi belirtilen subject_id'ye ait JSON dosyasına kaydeder.
        """
        filepath = self.directory + f"/{subject_id}.json"
        # Pydantic objelerini JSON uyumlu dict'lere dönüştür
        json_data = [item.model_dump() for item in data]
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=4, ensure_ascii=False)


    def get_subject_notes(self, subject_id: str) -> List[NoteEntry]:
        """
        Belirtilen subject_id'ye ait tüm notları döndürür.
        """
        return self._load_data(subject_id)
        
    
    def add_note_to_subject(self, subject_id: str, label: str, note_text: str) -> NoteEntry:
        """
        Yeni bir notu belirli bir konunun JSON dosyasına ekler.
        """
        note_text = note_text.strip()
        existing_notes = self._load_data(subject_id)

        # Yeni ID'yi belirle
        if existing_notes:
            max_id = max(note.id for note in existing_notes)
            new_id = max_id + 1
        else:
            new_id = 1
        
        # Yeni not kaydını oluştur
        new_note_entry = NoteEntry(id=new_id, label=label, note=note_text)
        
        # Mevcut notlara yeni notu ekle
        existing_notes.append(new_note_entry)
        
        # Güncellenmiş veriyi kaydet
        self._save_data(subject_id, existing_notes)
        print(f"Not '{new_id}' ID'si ile '{subject_id}.json' dosyasına başarıyla eklendi.")
        return new_note_entry
    
    def get_all_notes(self) -> Dict[str, List[NoteEntry]]:
        all_notes_by_subject = {}
        # Data dizinindeki tüm json dosyalarını listele
        for filename in os.listdir(self.data_directory):
            if filename.endswith(".json"):
                subject_id = filename.replace(".json", "")
                all_notes_by_subject[subject_id] = self._load_data(subject_id)
        return all_notes_by_subject


if __name__ == "__main__":
    pass