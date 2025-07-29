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

    def _load_data(self, subject_id: str, user_id: int) -> List[NoteEntry]:
        filepath = os.path.join(self.directory, f"{subject_id}_{user_id}.json")
        if not os.path.exists(filepath):
            return []
        with open(filepath, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
        return [NoteEntry(**item) for item in raw_data]
    

    def _save_data(self, subject_id: str, user_id: int, data: List[NoteEntry]):
        filepath = os.path.join(self.directory, f"{subject_id}_{user_id}.json")
        json_data = [item.model_dump() for item in data]
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=4, ensure_ascii=False)


    def get_subject_notes(self, subject_id: str) -> List[NoteEntry]:
        """
        Belirtilen subject_id'ye ait tüm notları döndürür.
        """
        return self._load_data(subject_id)
        
    
    def add_note_to_subject(self, subject_id: str, user_id: int, label: str, note_text: str) -> NoteEntry:
        note_text = note_text.strip()
        existing_notes = self._load_data(subject_id, user_id)

        new_id = max((note.id for note in existing_notes), default=0) + 1
        new_note_entry = NoteEntry(id=new_id, label=label, note=note_text)

        existing_notes.append(new_note_entry)
        self._save_data(subject_id, user_id, existing_notes)
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