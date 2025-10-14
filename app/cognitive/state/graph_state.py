# app/cognitive/state/graph_state.py

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
    Tracks all relevant session variables, user memory, intermediate outputs, and final results.
    """

    user_input: Optional[str] = Field(
        default=None, description="The latest user input message."
    )
    memory_context: Optional[MemoryContext] = Field(
        default=None, description="User's memory context object."
    )

    recognized_intent: Optional[Dict[str, Any]] = Field(
        default=None, description="Output of intent recognition: {'intent': ..., 'parameters': ...}"
    )

    # Modern artifacts produced by agentic planning
    plan_outline: Optional[PlanOutline] = Field(
        default=None, description="Conceptual skeleton of the plan (PlanOutline)."
    )
    roadmap: Optional[Roadmap] = Field(
        default=None, description="Operational realization of the outline (Roadmap)."
    )
    schedule: Optional[Schedule] = Field(
        default=None, description="Time-bound instantiation of the plan (Schedule)."
    )

    validation_result: Optional[Dict[str, Any]] = Field(
        default=None, description="Validation results for the plan (if any)."
    )
    run_metadata: Dict[str, Any] = Field(
        default_factory=dict, description="System metadata for this run."
    )

    world_model: Optional[Dict[str, Any]] = Field(
        default=None, description="Integrated world state (calendar, constraints, etc.)."
    )
    memory_updates: Dict[str, Any] = Field(
        default_factory=dict, description="Updates to user memory."
    )

    user_feedback: Optional[str] = Field(
        default=None, description="User feedback during planning loop (if any)."
    )
    # Agentic planning approvals + status
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
    retry_count: int = Field(
        default=0, description="Number of retries for the current step."
    )
    max_retries: int = Field(
        default=3, description="Maximum allowed retries before aborting or fallback."
    )
    error_message: Optional[str] = Field(
        default=None, description="Error message if any step fails."
    )

    response_text: Optional[str] = Field(
        default=None, description="Human-readable text to return to the user (e.g. for Telegram)."
    )
    # Observability and adaptation trace
    adaptation_log: List[AdaptationLogEntry] = Field(
        default_factory=list, description="Versioned log of structural/timing changes."
    )
    planning_trace: List[Dict[str, Any]] = Field(
        default_factory=list, description="Compact per-iteration trace; capped externally."
    )
