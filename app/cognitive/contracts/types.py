from typing import List, Literal, Optional, Union, Dict
from datetime import datetime, timezone
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator

# ─────────────────────────────────────────────────────────────
# Canonical enums / type aliases
# ─────────────────────────────────────────────────────────────

NodeType = Literal["goal", "phase", "cycle", "sub_goal", "task", "sub_task", "micro_goal"]
Recurrence = Literal["none", "daily", "weekly", "monthly", "quarterly", "yearly"]
NodeStatus = Literal["pending", "in_progress", "done", "blocked"]
Origin = Literal["system", "user_feedback", "ai_adaptation"]
StrategyMode = Literal["push", "relax", "hybrid", "manual"]

# Plan pattern taxonomy (v1.2)
PatternType = Literal[
    "milestone_project",
    "recurring_cycle",
    "progressive_accumulation_arc",
    "hybrid_project_cycle",
    "strategic_transformation",
]
PatternSubtype = Literal[
    "learning_arc",
    "training_arc",
    "creative_arc",
    "career_arc",
    "therapeutic_arc",
    "financial_arc",
]

DependencyType = Literal["finish_to_start", "start_to_start", "finish_to_finish", "start_to_finish"]


# ─────────────────────────────────────────────────────────────
# Pattern specification & Interaction policy
# ─────────────────────────────────────────────────────────────

class PatternSpec(BaseModel):
    """Selected planning pattern with optional subtype/variant and confidence.

    Note: pattern_type must be one of the canonical top-level patterns.
    Subtypes may include proposed:<name> to indicate an RFC-style proposal.
    """
    model_config = ConfigDict(extra="forbid")

    pattern_type: PatternType
    subtype: Optional[str] = None  # e.g., "protocol_routine" or "proposed:daily_health_protocol_v2"
    variant: Optional[str] = None  # e.g., "acute_recovery_1-2w"
    confidence: Optional[float] = None
    introduced_by: Optional[Origin] = None  # who proposed/selected this pattern
    source_pattern: Optional[str] = None  # when proposing, note the closest existing subtype/pattern
    rfc: Optional[str] = None  # rationale when proposing a new subtype


ConversationStyle = Literal["concise", "standard", "conversational", "coach"]
AutonomyLevel = Literal["high", "medium", "low"]
BrainstormingPref = Literal["on_demand", "suggest_when_uncertain", "always_offer"]
ApprovalPolicy = Literal["single_final", "milestone_approvals", "strict_every_step"]
Tone = Literal["neutral", "friendly", "clinical"]


class InteractionPolicy(BaseModel):
    """User interaction preferences that modulate agent behavior each turn.

    Stored long-term in MemoryContext; session overrides in GraphState.
    """
    model_config = ConfigDict(extra="forbid")

    conversation_style: ConversationStyle = "standard"
    talkativeness: float = 0.5  # 0..1
    autonomy: AutonomyLevel = "medium"
    brainstorming_preference: BrainstormingPref = "suggest_when_uncertain"
    approval_policy: ApprovalPolicy = "milestone_approvals"
    probing_depth: int = 1  # 0..3 typical range
    tone: Tone = "friendly"


class Dependency(BaseModel):
    """Directed relationship from this node to 'node_id' with a precedence rule."""
    model_config = ConfigDict(extra="forbid")

    node_id: UUID
    type: DependencyType = "finish_to_start"
    lag_lead_minutes: int = 0  # positive = lag, negative = lead

    @field_validator("lag_lead_minutes")
    @classmethod
    def _reasonable_lag(cls, v: int) -> int:
        # Optional guardrail; adjust if you want broader range
        if abs(v) > 60 * 24 * 60:  # 60 days in minutes upper bound
            raise ValueError("lag_lead_minutes is unreasonably large")
        return v


# ─────────────────────────────────────────────────────────────
# PlanNode and Hierarchy Models
# ─────────────────────────────────────────────────────────────

class PlanNode(BaseModel):
    """Atomic structural unit representing one node in a plan hierarchy."""
    model_config = ConfigDict(extra="forbid")

    id: UUID
    parent_id: Optional[UUID] = None
    node_type: NodeType
    level: int
    title: str
    description: Optional[str] = None
    recurrence: Optional[Recurrence] = None
    dependencies: List[Dependency] = Field(default_factory=list)
    status: NodeStatus = "pending"
    progress: float = 0.0
    origin: Origin = "system"
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Union[str, int, float, bool, dict, list]] = Field(default_factory=dict)

    @field_validator("progress")
    @classmethod
    def _progress_0_1(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("progress must be between 0 and 1")
        return v

    @model_validator(mode="after")
    def _root_invariants(self):
        # L1 goal invariants
        if self.level == 1:
            if self.parent_id is not None:
                raise ValueError("L1 node must not have a parent_id")
            if self.node_type != "goal":
                raise ValueError("L1 node must be of node_type='goal'")
        return self


# ─────────────────────────────────────────────────────────────
# Context Models
# ─────────────────────────────────────────────────────────────

class StrategyProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: StrategyMode
    weights: Optional[Dict[str, float]] = None  # {achievement, wellbeing, portfolio}


class PlanContext(BaseModel):
    model_config = ConfigDict(extra="forbid")
    strategy_profile: StrategyProfile
    pattern: Optional[PatternSpec] = None
    assumptions: Optional[Dict[str, object]] = None
    constraints: Optional[Dict[str, object]] = None
    user_prefs: Optional[Dict[str, object]] = None


class RoadmapContext(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # DEPRECATED: pattern_type/subtype retained for compatibility; source of truth is `pattern`.
    pattern_type: Optional[PatternType] = Field(
        default=None,
        description="DEPRECATED: present for backward compatibility—source of truth is `pattern`."
    )
    subtype: Optional[PatternSubtype] = None
    pattern: Optional[PatternSpec] = None
    scope: Optional[str] = None
    cadence: Optional[str] = None
    stack: Optional[List[str]] = None
    venue: Optional[str] = None
    region: Optional[str] = None
    time_horizon: Optional[str] = None
    budget: Optional[str] = None


# ─────────────────────────────────────────────────────────────
# Container Models (Outline, Roadmap, Schedule)
# ─────────────────────────────────────────────────────────────

class PlanOutline(BaseModel):
    model_config = ConfigDict(extra="forbid")
    root_id: UUID
    plan_context: PlanContext
    nodes: List[PlanNode]
    pattern: Optional[PatternSpec] = None

    @model_validator(mode="after")
    def _root_must_exist(self):
        if not any(n.id == self.root_id for n in self.nodes):
            raise ValueError("root_id must be present in nodes")
        return self


class Roadmap(BaseModel):
    model_config = ConfigDict(extra="forbid")
    root_id: UUID
    roadmap_context: RoadmapContext
    nodes: List[PlanNode]
    pattern: Optional[PatternSpec] = None

    @model_validator(mode="after")
    def _root_must_exist(self):
        if not any(n.id == self.root_id for n in self.nodes):
            raise ValueError("root_id must be present in nodes")
        return self


class ScheduledBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")
    plan_node_id: UUID
    title: str
    start: datetime
    end: datetime
    estimated_minutes: Optional[int] = None
    tags: List[str] = Field(default_factory=list)
    notes: Optional[str] = None

    @model_validator(mode="after")
    def _time_valid(self):
        if self.end <= self.start:
            raise ValueError("end must be after start")
        # enforce timezone-aware datetimes
        if self.start.tzinfo is None or self.end.tzinfo is None:
            raise ValueError("start/end must be timezone-aware")
        return self


class Schedule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    blocks: List[ScheduledBlock]


# ─────────────────────────────────────────────────────────────
# Adaptation & Logging
# ─────────────────────────────────────────────────────────────

class AdaptationLogEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    timestamp: datetime
    node_ids: List[UUID]
    action: str
    reason: Optional[str] = None
    origin: Origin
    strategy_applied: Optional[StrategyMode] = None
    portfolio_impact: Optional[Dict[str, object]] = None


# ─────────────────────────────────────────────────────────────
# MEMORY MODELS (as-is with safer defaults)
# ─────────────────────────────────────────────────────────────

class MemoryObject(BaseModel):
    model_config = ConfigDict(extra="forbid")
    memory_id: Optional[str] = None
    user_id: str
    goal_id: Optional[str] = None
    type: Literal["episodic", "semantic", "procedural"]
    content: Union[str, dict]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Optional[dict] = Field(default_factory=dict)


class MemoryContext(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        from_attributes=True,
        extra="forbid",
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
    # Long-term user interaction preferences; session overrides live in GraphState
    interaction_policy: Optional[InteractionPolicy] = None

    def add_memory(self, memory: MemoryObject):
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
        return self.model_dump()

    @classmethod
    def deserialize(cls, data: dict) -> "MemoryContext":
        return cls(**data)