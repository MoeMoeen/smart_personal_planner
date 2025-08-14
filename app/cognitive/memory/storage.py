# app/cognitive/memory/storage.py

# app/memory/storage.py

from sqlalchemy.orm import Session
from .schemas import MemoryORM, MemoryType
from app.cognitive.contracts.types import MemoryObject, MemoryContext
from datetime import datetime
from typing import Optional

def write_memory(db: Session, memory: MemoryObject) -> str:
    orm_obj = MemoryORM(
        user_id=memory.user_id,
        goal_id=memory.goal_id,
        type=memory.type,
        content=memory.content,
        metadata=memory.metadata or {},
        timestamp=memory.timestamp or datetime.utcnow()
    )
    db.add(orm_obj)
    db.commit()
    db.refresh(orm_obj)

    # Return the memory ID
    return str(orm_obj.memory_id)


def retrieve_memory(
    db: Session,
    user_id: str,
    goal_id: Optional[str] = None,
    types: list[str] = ["episodic", "semantic", "procedural"]
) -> MemoryContext:
    filters = [
        MemoryORM.user_id == user_id,
        MemoryORM.type.in_(types)
    ]
    if goal_id:
        filters.append(MemoryORM.goal_id == goal_id)

    results = db.query(MemoryORM).filter(*filters).order_by(MemoryORM.timestamp.desc()).all()

    # Map results to MemoryContext - MemoryContext is a container for different types of memory
    context = MemoryContext()
    for item in results:
        obj = MemoryObject(
            memory_id=str(getattr(item, "memory_id")),
            user_id=str(getattr(item, "user_id")),
            goal_id=str(getattr(item, "goal_id")) if getattr(item, "goal_id") is not None else None,
            type=getattr(item, "type"),
            content=getattr(item, "content"),
            metadata=getattr(item, "metadata"),
            timestamp=getattr(item, "timestamp")
        )
        getattr(context, obj.type).append(obj)

    # Return the populated MemoryContext
    return context
