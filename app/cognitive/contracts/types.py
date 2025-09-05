# app/cognitive/contracts/types.py

"""Data models for the cognitive architecture of the smart personal planner."""

from typing import List, Literal, Optional, Union, Dict
from datetime import datetime, date, timezone
from pydantic import BaseModel, Field, ConfigDict

# === CORE PLANNING CONTRACTS ===

class GoalSpec(BaseModel):
    goal_id: Optional[str] = None
    user_id: str
    title: str
    description: Optional[str] = None
    goal_type: Literal["project", "habit"]
    start_date: date
    end_date: Optional[date] = None
    recurrence_count: Optional[int] = None
    constraints: Optional[List[str]] = []


class PlanOutline(BaseModel):
    goal_id: str
    num_cycles: int
    cycle_duration_days: int
    occurrences_per_cycle: int
    notes: Optional[str] = None


class OccurrenceTask(BaseModel):
    title: str
    type: Literal["core", "preparation", "recovery"]
    estimated_minutes: int
    notes: Optional[str] = None


class OccurrenceTasks(BaseModel):
    goal_id: str
    cycle_number: int
    occurrence_number: int
    tasks: List[OccurrenceTask]


class CalendarizedTask(BaseModel):
    title: str
    start_datetime: datetime
    end_datetime: datetime
    occurrence_id: Optional[str]
    notes: Optional[str] = None


class CalendarizedPlan(BaseModel):
    goal_id: str
    tasks: List[CalendarizedTask]


class PlanVerificationReport(BaseModel):
    goal_id: str
    passed: bool
    violations: List[str] = []


# === MEMORY MODELS ===

class MemoryObject(BaseModel):
    memory_id: Optional[str] = None
    user_id: str
    goal_id: Optional[str] = None
    type: Literal["episodic", "semantic", "procedural"]
    content: Union[str, dict]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Optional[dict] = {}


class MemoryContext(BaseModel):
    """
    Bundles all memory types for node injection and context sharing.
    Includes helper methods and metadata for robust, traceable, and extensible use.
    """
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        from_attributes=True,
        json_schema_extra={
            "example": {
                "episodic": [],
                "semantic": [],
                "procedural": [],
                "user_id": "user_123",
                "session_id": "sess_456",
                "timestamp": "2025-08-16T12:00:00Z",
                "source": "planner_node"
            }
        }
    )

    episodic: List[MemoryObject] = Field(default_factory=list)
    semantic: List[MemoryObject] = Field(default_factory=list)
    procedural: List[MemoryObject] = Field(default_factory=list)
    memory_updates: Dict[str, List[MemoryObject]] = Field(
        default_factory=lambda: {"episodic": [], "semantic": [], "procedural": []}
    )

    # Optional metadata for traceability and context
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: Optional[str] = None

    def add_memory(self, memory: MemoryObject):
        """Add a memory object to the correct list based on its type."""
        if memory.type == "episodic":
            self.episodic.append(memory)
        elif memory.type == "semantic":
            self.semantic.append(memory)
        elif memory.type == "procedural":
            self.procedural.append(memory)
        else:
            raise ValueError(f"Unknown memory type: {memory.type}")

    def get_memories(
        self,
        memory_type: Optional[str] = None,
        goal_id: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[MemoryObject]:
        """Retrieve memories by type, goal, and/or user, optionally limited by recency."""
        if memory_type == "episodic":
            memories = self.episodic
        elif memory_type == "semantic":
            memories = self.semantic
        elif memory_type == "procedural":
            memories = self.procedural
        else:
            memories = self.episodic + self.semantic + self.procedural

        if goal_id:
            memories = [m for m in memories if m.goal_id == goal_id]
        if user_id:
            memories = [m for m in memories if m.user_id == user_id]

        memories = sorted(memories, key=lambda m: m.timestamp, reverse=True)
        if limit:
            memories = memories[:limit]
        return memories

    def serialize(self) -> dict:
        """Serialize the context for logging or transfer."""
        return self.model_dump()

    @classmethod
    def deserialize(cls, data: dict) -> "MemoryContext":
        """Deserialize from dict."""
        return cls(**data)