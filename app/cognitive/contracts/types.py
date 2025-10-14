# app/cognitive/contracts/types.py

"""Data models for the cognitive architecture of the smart personal planner.

Aligned with v1.2 (patterns + grammar + dual-axis) and v1.3 (MegaGraph orchestration).
Implements aggressive cleanup: removes legacy OccurrenceTask(s) and CalendarizedPlan.
"""

from typing import List, Literal, Optional, Union, Dict
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict

# ─────────────────────────────────────────────────────────────
# Core structural entities (cognitive layer)
# ─────────────────────────────────────────────────────────────

class PlanNode(BaseModel):
    """Atomic structural unit representing one node in a plan hierarchy."""
    id: str
    parent_id: Optional[str] = None
    node_type: Literal[
        "goal", "phase", "cycle", "sub_goal", "task", "sub_task", "micro_goal"
    ]
    level: int
    title: str
    description: Optional[str] = None
    recurrence: Optional[Literal["none", "daily", "weekly", "monthly", "quarterly", "yearly"]] = None
    # Each dependency: {node_id, type, lag_lead_minutes?}
    dependencies: List[Dict[str, Union[str, int]]] = Field(default_factory=list)
    status: Literal["pending", "in_progress", "done", "blocked"] = "pending"
    progress: float = 0.0
    origin: Literal["system", "user_feedback", "ai_adaptation"] = "system"
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, object] = Field(default_factory=dict)


class StrategyProfile(BaseModel):
    """User’s adaptive strategy mode and weights."""
    mode: Literal["push", "relax", "hybrid", "manual"]
    weights: Optional[Dict[str, float]] = None  # {achievement, wellbeing, portfolio}


class PlanContext(BaseModel):
    """Meta assumptions and preferences for a plan."""
    strategy_profile: StrategyProfile
    assumptions: Optional[Dict[str, object]] = None
    constraints: Optional[Dict[str, object]] = None
    user_prefs: Optional[Dict[str, object]] = None


class RoadmapContext(BaseModel):
    """Real-world operational parameters for a plan."""
    pattern_type: str
    subtype: Optional[str] = None
    scope: Optional[str] = None
    cadence: Optional[str] = None
    stack: Optional[List[str]] = None
    venue: Optional[str] = None
    region: Optional[str] = None
    time_horizon: Optional[str] = None
    budget: Optional[str] = None


class PlanOutline(BaseModel):
    """Conceptual skeleton of a plan before scheduling."""
    root_id: str
    plan_context: PlanContext
    nodes: List[PlanNode]


class Roadmap(BaseModel):
    """Operational realization of the outline with context applied."""
    root_id: str
    roadmap_context: RoadmapContext
    nodes: List[PlanNode]


class ScheduledBlock(BaseModel):
    """One concrete scheduled block of time linked to a PlanNode."""
    plan_node_id: str
    title: str
    start: datetime
    end: datetime
    estimated_minutes: Optional[int] = None
    tags: List[str] = Field(default_factory=list)
    notes: Optional[str] = None


class Schedule(BaseModel):
    """Full calendar binding for a plan."""
    blocks: List[ScheduledBlock]


class AdaptationLogEntry(BaseModel):
    """Records every structural/timing change applied by AI or user."""
    timestamp: datetime
    node_ids: List[str]
    action: str
    reason: Optional[str] = None
    origin: Literal["system", "user_feedback", "ai_adaptation"]
    strategy_applied: Optional[str] = None
    portfolio_impact: Optional[Dict[str, object]] = None


# ─────────────────────────────────────────────────────────────
# MEMORY MODELS (kept as-is)
# ─────────────────────────────────────────────────────────────

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
