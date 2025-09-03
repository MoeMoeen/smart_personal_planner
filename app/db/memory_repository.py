# app/db/memory_repository.py

from sqlalchemy.orm import Session
from app.models import EpisodicMemory, SemanticMemory, ProceduralMemory
from app.cognitive.contracts.types import MemoryContext


class MemoryRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_memory_context(self, user_id: int) -> MemoryContext:
        episodic = [e.orm_to_memory_object() for e in self.db.query(EpisodicMemory).filter_by(user_id=user_id)]
        semantic = [s.orm_to_memory_object() for s in self.db.query(SemanticMemory).filter_by(user_id=user_id)]
        procedural = [p.orm_to_memory_object() for p in self.db.query(ProceduralMemory).filter_by(user_id=user_id)]

        return MemoryContext(
            user_id=str(user_id),
            episodic=episodic,
            semantic=semantic,
            procedural=procedural,
        )


    def save_memory_updates(self, user_id: int, updates: dict):
        """Persist updates back to DB."""
        # episodic updates
        for e in updates.get("episodic", []):
            self.db.add(EpisodicMemory(user_id=user_id, content=e))

        # semantic updates
        for s in updates.get("semantic", []):
            self.db.add(SemanticMemory(user_id=user_id, content=s))

        # procedural updates
        for p in updates.get("procedural", []):
            self.db.add(ProceduralMemory(user_id=user_id, content=p))

        self.db.commit()
