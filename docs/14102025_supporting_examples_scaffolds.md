Perfect, brother 🙌 — let’s get your canonical JSON fixtures ready before we touch any code.
These will serve as your schema blueprints, test fixtures, and also sanity references while implementing types.py, models.py, and the stub planning_node.

We’ll provide realistic JSON examples for the key entities in the new design — all aligned with v1.2 (Planning Intelligence) + v1.3 (MegaGraph orchestration) and now with the aggressive cleanup path applied (no legacy entities anywhere).


---

🧱 Canonical JSON Blueprints for Core Entities

All examples below are syntactically valid JSON, so they can be dropped directly into test files, or printed from stubs during validation.


---

🧩 1. PlanNode (Atomic structural unit)

A single node in the plan hierarchy, used for everything from goals to micro-tasks.

{
  "id": "uuid-plan-node-1",
  "parent_id": null,
  "node_type": "goal",
  "level": 1,
  "title": "Learn Python and build practical AI projects",
  "description": "Develop Python programming skills over 6 months through structured phases and mini-projects.",
  "recurrence": "none",
  "dependencies": [],
  "status": "pending",
  "progress": 0.0,
  "origin": "system",
  "tags": ["learning", "career", "skill"],
  "metadata": {
    "pattern_type": "progressive_accumulation_arc",
    "subtype": "learning_arc",
    "estimated_duration_weeks": 24
  }
}

Sub-nodes (phases, tasks, etc.) reference this id as their parent_id.


---

🪜 2. Full PlanNode Hierarchy Example (L1–L5)

This example shows how one plan (Learn Python) can expand dynamically down to L5 micro-goals.

{
  "nodes": [
    {
      "id": "uuid-plan-node-1",
      "parent_id": null,
      "node_type": "goal",
      "level": 1,
      "title": "Learn Python and build practical AI projects",
      "description": "Develop Python programming skills over 6 months.",
      "origin": "system"
    },
    {
      "id": "uuid-plan-node-2",
      "parent_id": "uuid-plan-node-1",
      "node_type": "phase",
      "level": 2,
      "title": "Phase 1 — Python Fundamentals",
      "origin": "system"
    },
    {
      "id": "uuid-plan-node-3",
      "parent_id": "uuid-plan-node-2",
      "node_type": "sub_goal",
      "level": 3,
      "title": "Master basic syntax and data structures",
      "origin": "system"
    },
    {
      "id": "uuid-plan-node-4",
      "parent_id": "uuid-plan-node-3",
      "node_type": "task",
      "level": 4,
      "title": "Complete beginner Python course",
      "origin": "system",
      "status": "pending"
    },
    {
      "id": "uuid-plan-node-5",
      "parent_id": "uuid-plan-node-4",
      "node_type": "sub_task",
      "level": 5,
      "title": "Watch modules 1–5 and take notes",
      "origin": "system"
    },
    {
      "id": "uuid-plan-node-6",
      "parent_id": "uuid-plan-node-4",
      "node_type": "micro_goal",
      "level": 5,
      "title": "Write summary reflection after each module",
      "origin": "ai_adaptation"
    }
  ]
}

🧠 AI Adaptivity: notice how the micro_goal node (L5) was introduced later by the AI to improve retention (a per-module reflection).
This is a perfect example of dynamic expansion within the same plan.


---

🧭 3. PlanOutline (Conceptual skeleton)

{
  "root_id": "uuid-plan-node-1",
  "plan_context": {
    "strategy_profile": {
      "mode": "push",
      "weights": { "achievement": 0.7, "wellbeing": 0.2, "portfolio": 0.1 }
    },
    "assumptions": {
      "weekly_hours_available": 6,
      "preferred_learning_time": "evenings",
      "target_completion_date": "2026-04-30"
    },
    "constraints": {
      "max_parallel_phases": 1,
      "max_daily_time_minutes": 90
    },
    "user_prefs": {
      "interaction_style": "conversational",
      "reflection_style": "journal"
    }
  },
  "nodes": [
    { "id": "uuid-plan-node-1", "node_type": "goal", "level": 1, "title": "Learn Python" },
    { "id": "uuid-plan-node-2", "node_type": "phase", "level": 2, "title": "Fundamentals" },
    { "id": "uuid-plan-node-3", "node_type": "phase", "level": 2, "title": "APIs & Data" },
    { "id": "uuid-plan-node-4", "node_type": "phase", "level": 2, "title": "OOP & Projects" }
  ]
}

🧩 Purpose: PlanOutline = “blueprint” (conceptual shape, no specific dates yet).


---

🗺️ 4. Roadmap (Concrete, contextualized version)

{
  "root_id": "uuid-plan-node-1",
  "roadmap_context": {
    "pattern_type": "progressive_accumulation_arc",
    "subtype": "learning_arc",
    "scope": "Develop intermediate-level Python skills with practical AI exposure",
    "cadence": "weekly study sessions + monthly mini-project",
    "stack": ["Python", "LangChain", "FastAPI"],
    "venue": "home workspace",
    "region": "remote",
    "time_horizon": "6 months",
    "budget": "£0 (self-study)"
  },
  "nodes": [
    { "id": "uuid-plan-node-1", "node_type": "goal", "level": 1, "title": "Learn Python" },
    { "id": "uuid-plan-node-2", "node_type": "phase", "level": 2, "title": "Phase 1 — Fundamentals" },
    { "id": "uuid-plan-node-7", "parent_id": "uuid-plan-node-2", "node_type": "task", "level": 4, "title": "Build CLI app: Daily Planner" },
    { "id": "uuid-plan-node-8", "parent_id": "uuid-plan-node-2", "node_type": "task", "level": 4, "title": "Complete notebook exercises (10 hrs)" }
  ]
}

🧭 Purpose: Roadmap = same structure as Outline, but now with real-world parameters (stack, cadence, etc.) before scheduling.


---

🕒 5. Schedule (time-bound instantiation)

{
  "blocks": [
    {
      "plan_node_id": "uuid-plan-node-7",
      "title": "Build CLI app: Daily Planner",
      "start": "2025-11-10T19:00:00Z",
      "end": "2025-11-15T21:00:00Z",
      "estimated_minutes": 480,
      "tags": ["phase:fundamentals", "project"],
      "notes": "Finish MVP by Saturday"
    },
    {
      "plan_node_id": "uuid-plan-node-8",
      "title": "Complete notebook exercises",
      "start": "2025-11-16T19:00:00Z",
      "end": "2025-11-18T20:30:00Z",
      "estimated_minutes": 180,
      "tags": ["learning"],
      "notes": "Review API module"
    }
  ]
}

🕓 Purpose: Schedule = real execution plan → connects each scheduled block directly to its PlanNode.


---

🎯 6. StrategyProfile (how AI should adapt)

{
  "mode": "hybrid",
  "weights": {
    "achievement": 0.6,
    "wellbeing": 0.3,
    "portfolio": 0.1
  }
}

📊 Meaning:

Push: catch up aggressively when behind.

Relax: reduce workload temporarily.

Hybrid: balance dynamically.

Manual: always confirm before changes.



---

🧠 7. AdaptationLogEntry (how AI logs changes)

{
  "timestamp": "2025-12-02T08:00:00Z",
  "node_ids": ["uuid-plan-node-8"],
  "action": "reschedule",
  "reason": "User missed study session due to travel",
  "origin": "ai_adaptation",
  "strategy_applied": "relax",
  "portfolio_impact": {
    "affected_goals": 2,
    "total_hours_shifted": 3.0
  }
}

🪶 Purpose: every adaptive decision leaves a transparent trace for learning and debugging.


---

🧠 8. GraphState Example (after planning completed)

{
  "intent": "create_new_plan",
  "goal_context": { "title": "Learn Python and build AI projects" },
  "plan_outline": { "...": "see PlanOutline above" },
  "roadmap": { "...": "see Roadmap above" },
  "schedule": { "...": "see Schedule above" },
  "outline_approved": true,
  "roadmap_approved": true,
  "schedule_approved": true,
  "planning_status": "complete",
  "escalate_reason": null,
  "response_text": "Plan successfully generated and scheduled.",
  "adaptation_log": []
}

🧩 Purpose: shows how the planning_node outputs all artifacts and status flags in a single state object.


---

✅ Summary of Key Field Relationships

Entity	Connected To	Notes

PlanNode	Plan via FK; ScheduledTask via plan_node_id	Canonical structure unit
PlanOutline	Contains list of PlanNodes + PlanContext	Conceptual structure
Roadmap	Reuses same PlanNode graph + adds RoadmapContext	Operational version
Schedule	Links concrete dates to PlanNode IDs	Time binding
StrategyProfile	Embedded in PlanContext	Governs adaptation style
AdaptationLogEntry	Stored per plan	History of all dynamic changes
GraphState	Shared runtime container	Holds all artifacts + status flags



---

🧠 Optional Example — “Buy a House” PlanNode Skeleton

(Shorter pattern: milestone project, to test diversity of patterns.)

{
  "nodes": [
    { "id": "goal-1", "node_type": "goal", "level": 1, "title": "Buy a house in London by 2027" },
    { "id": "phase-1", "parent_id": "goal-1", "node_type": "phase", "level": 2, "title": "Financial Readiness" },
    { "id": "task-1", "parent_id": "phase-1", "node_type": "task", "level": 3, "title": "Save £2,000 monthly", "recurrence": "monthly" },
    { "id": "phase-2", "parent_id": "goal-1", "node_type": "phase", "level": 2, "title": "Market Research" },
    { "id": "task-2", "parent_id": "phase-2", "node_type": "task", "level": 3, "title": "Visit 3 properties per month", "recurrence": "monthly" }
  ],
  "plan_context": {
    "strategy_profile": { "mode": "push" },
    "constraints": { "monthly_budget": 2000 },
    "assumptions": { "location": "SW London", "target_price": 700000 }
  }
}


---

✅ How to use these

Each JSON can become a test fixture in /tests/fixtures/.

Each corresponds 1:1 to your upcoming Pydantic models in types.py.

The PlanNode schema drives both ORM (models.py) and API serialization.

The GraphState fixture can test both the stub planning_node and router logic.



---

Would you like me next to:

1. generate the SQLAlchemy DDL snippet (for PlanNode table + ScheduledTask update),


2. and then 3) provide Pydantic model skeletons (class definitions with field types + docstrings) directly aligned with these JSON examples?



That’ll let you implement Phases 2 and 4 seamlessly and with zero guessing.


Perfect brother 🙌 — let’s lock in the exact schema scaffolding now, so when we start coding types.py and models.py, everything will flow cleanly with zero uncertainty.

Below I’m giving you:

1. ✅ SQLAlchemy DDL snippet — ready for Alembic or Base.metadata.create_all().


2. ✅ Pydantic model skeletons — one-to-one with the JSON fixtures you just approved.


3. ✅ Quick field crosswalk table — mapping ORM ↔ Pydantic ↔ JSON fixture naming for consistency.




---

🧱 PART 1 — SQLAlchemy Schema (DDL snippet)

> File: app/db/models.py



from sqlalchemy import (
    Column, String, Integer, Float, Text, DateTime, Boolean,
    ForeignKey, JSON, Enum
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime
from uuid import uuid4
from app.db.base import Base  # adjust import to your setup


class PlanNode(Base):
    __tablename__ = "plan_nodes"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    plan_id: Mapped[str] = mapped_column(String, ForeignKey("plans.id", ondelete="CASCADE"))
    parent_id: Mapped[str | None] = mapped_column(String, ForeignKey("plan_nodes.id"), nullable=True)

    node_type: Mapped[str] = mapped_column(String(20))  # goal, phase, cycle, sub_goal, task, sub_task, micro_goal
    level: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    recurrence: Mapped[str | None] = mapped_column(String(20), nullable=True)  # daily, weekly, etc.
    dependencies: Mapped[dict | None] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, in_progress, done, blocked
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    origin: Mapped[str] = mapped_column(String(30), default="system")  # system, user_feedback, ai_adaptation
    order_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tags: Mapped[list | None] = mapped_column(JSON, default=list)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Self-referential relationship
    parent = relationship("PlanNode", remote_side=[id], backref="children")


class ScheduledTask(Base):
    __tablename__ = "scheduled_tasks"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    plan_id: Mapped[str] = mapped_column(String, ForeignKey("plans.id", ondelete="CASCADE"))
    plan_node_id: Mapped[str] = mapped_column(
        String, ForeignKey("plan_nodes.id", ondelete="CASCADE"), nullable=False
    )

    title: Mapped[str] = mapped_column(String(255))
    start_datetime: Mapped[datetime] = mapped_column(DateTime)
    end_datetime: Mapped[datetime] = mapped_column(DateTime)
    estimated_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tags: Mapped[list | None] = mapped_column(JSON, default=list)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    plan_node = relationship("PlanNode", backref="scheduled_tasks")

✅ DDL Summary:

PlanNode = single source of truth for structure.

ScheduledTask = canonical calendar layer, FK → PlanNode.

Task, HabitCycle, GoalOccurrence dropped entirely.

Goal and Plan remain as higher-level containers.



---

🧩 PART 2 — Pydantic Model Skeletons

> File: app/cognitive/contracts/types.py



All models follow Pydantic v2+ style and mirror the new JSON fixtures.

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Literal, Dict
from datetime import datetime


# ─────────────────────────────────────────────────────────────
# PlanNode and Hierarchy Models
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
    recurrence: Optional[str] = None
    dependencies: List[Dict[str, str]] = Field(default_factory=list)
    status: Literal["pending", "in_progress", "done", "blocked"] = "pending"
    progress: float = 0.0
    origin: Literal["system", "user_feedback", "ai_adaptation"] = "system"
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, object] = Field(default_factory=dict)


# ─────────────────────────────────────────────────────────────
# Context Models
# ─────────────────────────────────────────────────────────────

class StrategyProfile(BaseModel):
    """User’s adaptive strategy mode."""
    mode: Literal["push", "relax", "hybrid", "manual"]
    weights: Optional[Dict[str, float]] = None


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


# ─────────────────────────────────────────────────────────────
# Container Models (Outline, Roadmap, Schedule)
# ─────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────
# Adaptation & Logging
# ─────────────────────────────────────────────────────────────

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
# Unified GraphState Schema
# ─────────────────────────────────────────────────────────────

class GraphState(BaseModel):
    """Shared cognitive state across the MegaGraph."""
    intent: str
    goal_context: Optional[Dict[str, object]] = None
    plan_outline: Optional[PlanOutline] = None
    roadmap: Optional[Roadmap] = None
    schedule: Optional[Schedule] = None
    outline_approved: bool = False
    roadmap_approved: bool = False
    schedule_approved: bool = False
    planning_status: Literal[
        "complete", "needs_clarification", "needs_scheduling_escalation", "aborted"
    ] = "needs_clarification"
    escalate_reason: Optional[str] = None
    response_text: Optional[str] = None
    adaptation_log: List[AdaptationLogEntry] = Field(default_factory=list)


---

🔗 PART 3 — ORM ↔ Pydantic Crosswalk

Concept	ORM Table	Pydantic Model	Key Relationship

Structural Node	plan_nodes	PlanNode	Plan.plan_nodes
Conceptual Skeleton	—	PlanOutline	purely cognitive; not persisted
Operational Plan	—	Roadmap	not persisted; ephemeral before scheduling
Scheduled Event	scheduled_tasks	ScheduledBlock	linked by plan_node_id
Full Schedule	—	Schedule	1:N ScheduledBlock
Strategy Mode	—	StrategyProfile	embedded in PlanContext
Adaptation History	—	AdaptationLogEntry	stored per Plan in state
Runtime Graph	—	GraphState	orchestration layer in memory



---

⚙️ Recommended Next Steps

Step	Action	Output

1	Copy DDL snippet → models.py	drop/recreate DB; PlanNode table appears
2	Copy Pydantic models → types.py	all entities compile & type-check
3	Create /tests/fixtures/plan_outline.json	paste one of the JSON blueprints
4	Run unit test to instantiate GraphState with fixture data	confirms end-to-end serialization
5	Implement stub planning_node → returns dummy GraphState populated with valid objects	ready for router wiring



---

