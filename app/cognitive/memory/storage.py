# app/cognitive/memory/storage.py
""" Memory storage and retrieval functions.
This module provides functionality to store and retrieve
different types of memory objects. 
"""

from sqlalchemy.orm import Session
from .schemas import MemoryORM, MemoryType
from app.cognitive.contracts.types import MemoryObject, MemoryContext
from datetime import datetime, timezone
from typing import Optional

def write_memory(db: Session, memory: MemoryObject) -> str:
    orm_obj = MemoryORM(
        user_id=memory.user_id,
        goal_id=memory.goal_id,
        type=memory.type,
        content=memory.content,
        memory_metadata=memory.metadata or {},  # Use correct column name
        timestamp=memory.timestamp or datetime.now(timezone.utc)
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
        # Extract and validate the type string
        if hasattr(item.type, 'value'):
            raw_type = item.type.value
        else:
            raw_type = str(item.type)
        
        # Ensure the type is valid for MemoryObject - explicit type casting
        if raw_type == 'episodic': 
            memory_type = MemoryType.episodic
        elif raw_type == 'procedural':
            memory_type = MemoryType.procedural
        else:
            memory_type = MemoryType.semantic  # Default fallback

        obj = MemoryObject(
            memory_id=str(item.memory_id),
            user_id=str(item.user_id),
            goal_id=str(item.goal_id) if item.goal_id is not None else None,
            type=memory_type.value,
            content=item.content,  # type: ignore  # SQLAlchemy returns actual values at runtime
            metadata=item.memory_metadata or {},  # type: ignore  # SQLAlchemy returns actual values at runtime
            timestamp=item.timestamp  # type: ignore  # SQLAlchemy returns actual values at runtime
        )
        getattr(context, obj.type).append(obj)

    # Return the populated MemoryContext
    return context
