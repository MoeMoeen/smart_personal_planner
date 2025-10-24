from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Literal
from app.cognitive.contracts.types import (
    MemoryContext,
    PlanOutline,
    Roadmap,
    Schedule,
    AdaptationLogEntry,
)

class GraphState(BaseModel):
    """
    Global state object passed between LangGraph nodes.
    Core fields are stable and minimal; extended fields support runtime ergonomics.
    """

    # ── Core (stable contract) ─────────────────────────────────────────────
    intent: Optional[str] = Field(
        default=None, description="Denormalized top-level intent name (e.g., 'create_new_plan')."
    )

    plan_outline: Optional[PlanOutline] = Field(
        default=None, description="Conceptual skeleton of the plan (PlanOutline)."
    )
    roadmap: Optional[Roadmap] = Field(
        default=None, description="Operational realization of the outline (Roadmap)."
    )
    schedule: Optional[Schedule] = Field(
        default=None, description="Time-bound instantiation of the plan (Schedule)."
    )

    outline_approved: bool = Field(
        default=False, description="PlanOutline approved by user within planning agent."
    )
    roadmap_approved: bool = Field(
        default=False, description="Roadmap approved by user within planning agent."
    )
    schedule_approved: bool = Field(
        default=False, description="Schedule approved by user within planning agent."
    )

    planning_status: Literal[
        "complete",
        "needs_clarification",
        "needs_scheduling_escalation",
        "aborted",
    ] = Field(default="needs_clarification", description="Router key for post-planning branching.")

    escalate_reason: Optional[str] = Field(
        default=None, description="Reason for scheduling escalation, if any."
    )
    response_text: Optional[str] = Field(
        default=None, description="Human-readable response to present to the user."
    )
    adaptation_log: List[AdaptationLogEntry] = Field(
        default_factory=list, description="Versioned log of structural/timing changes."
    )

    # ── Extended (runtime/diagnostic; flexible) ───────────────────────────
    user_input: Optional[str] = Field(
        default=None, description="Latest user input message."
    )
    recognized_intent: Optional[Dict[str, Any]] = Field(
        default=None, description="Raw intent classifier output: {'intent': ..., 'parameters': ...}."
    )
    goal_context: Optional[Dict[str, Any]] = Field(
        default=None, description="Denormalized goal params (title, horizon, etc.) for quick access."
    )

    memory_context: Optional[MemoryContext] = Field(
        default=None, description="User's memory context object."
    )
    memory_updates: Dict[str, Any] = Field(
        default_factory=dict, description="Pending updates to user memory."
    )
    world_model: Optional[Dict[str, Any]] = Field(
        default=None, description="Integrated world state (calendar, constraints, etc.)."
    )

    validation_result: Optional[Dict[str, Any]] = Field(
        default=None, description="Validation results for the plan (if any)."
    )
    run_metadata: Dict[str, Any] = Field(
        default_factory=dict, description="System/runtime metadata for this run."
    )

    user_feedback: Optional[str] = Field(
        default=None, description="User feedback captured during planning loop."
    )
    planning_trace: List[Dict[str, Any]] = Field(
        default_factory=list, description="Compact per-iteration trace; capped externally."
    )

    retry_count: int = Field(
        default=0, description="Retries for current step."
    )
    max_retries: int = Field(
        default=3, description="Maximum allowed retries before aborting or fallback."
    )
    error_message: Optional[str] = Field(
        default=None, description="Error message if a step fails."
    )