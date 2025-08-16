# app/cognitive/memory/__init__.py

"""
Cognitive AI Memory System

Contains both SQLAlchemy models for database storage and semantic memory
using vector databases for fuzzy recall.
"""

# Export semantic memory components for easy access
from .semantic import SemanticMemory, MemoryPriority, SemanticMemoryType as SemanticMemoryType, MemoryEntry
from .schemas import MemoryORM, MemoryAssociation, MemoryType
from .storage import write_memory, retrieve_memory

__all__ = [
    # Semantic Memory (AI Learning)
    "SemanticMemory", 
    "MemoryPriority", 
    "SemanticMemoryType",
    "MemoryEntry",
    
    # Database Storage
    "MemoryORM", 
    "MemoryAssociation", 
    "MemoryType",
    "write_memory", 
    "retrieve_memory"
]
