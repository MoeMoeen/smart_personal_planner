# app/cognitive/memory/schemas.py

from sqlalchemy import Column, String, DateTime, JSON, Enum, Integer, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
import uuid

# Import the main Base from models.py to ensure consistency
from app.models import Base

# Memory types
class MemoryType(str, enum.Enum):
    episodic = "episodic"
    semantic = "semantic"
    procedural = "procedural"

# Memory ORM - SQLAlchemy model - This represents the memory objects stored in the database
class MemoryORM(Base):
    __tablename__ = "memory_objects"

    memory_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, nullable=False)
    goal_id = Column(String, nullable=True)
    type = Column(Enum(MemoryType), nullable=False)
    content = Column(JSON, nullable=False)
    memory_metadata = Column(JSON, nullable=True)  # Renamed to avoid conflict with SQLAlchemy metadata
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    source_associations = relationship("MemoryAssociation", foreign_keys="MemoryAssociation.source_memory_id", back_populates="source_memory")
    target_associations = relationship("MemoryAssociation", foreign_keys="MemoryAssociation.target_memory_id", back_populates="target_memory")

# Memory Association ORM - This represents associations between memory objects
class MemoryAssociation(Base):
    __tablename__ = "memory_associations"
    
    id = Column(Integer, primary_key=True, index=True)
    source_memory_id = Column(UUID(as_uuid=True), ForeignKey("memory_objects.memory_id"), nullable=False)
    target_memory_id = Column(UUID(as_uuid=True), ForeignKey("memory_objects.memory_id"), nullable=False)
    association_type = Column(String(50), nullable=False)
    strength = Column(Float, nullable=False, default=1.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    source_memory = relationship("MemoryORM", foreign_keys=[source_memory_id], back_populates="source_associations")
    target_memory = relationship("MemoryORM", foreign_keys=[target_memory_id], back_populates="target_associations")
