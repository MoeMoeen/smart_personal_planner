# app/cognitive/state/graph_state.py

from pydantic import BaseModel, Field, model_validator
from typing import Optional, Dict, Any, List
from app.cognitive.contracts.types import MemoryContext

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

    goal_spec: Optional[Dict[str, Any]] = Field(
        default=None, description="Structured representation of the user's goal."
    )
    plan_outline: Optional[Dict[str, Any]] = Field(
        default=None, description="High-level plan outline (occurrences, cycles, structure)."
    )
    occurrence_tasks: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="Detailed tasks for each occurrence."
    )
    # For alignment with node I/O, include a generic schedule list
    schedule: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="Scheduled tasks list for the plan."
    )
    calendarized_plan: Optional[Dict[str, Any]] = Field(
        default=None, description="Plan with assigned time slots (legacy alias)."
    )

    validation_result: Optional[Dict[str, Any]] = Field(
        default=None, description="Validation results for the plan."
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
        default=None, description="User feedback at confirmation steps."
    )
    # Router-related flags
    confirmed_a: Optional[str] = Field(
        default=None, description='Decision at confirm A: "confirm" | "revise" | "cancel"'
    )
    validation_key: Optional[str] = Field(
        default=None, description='Validation branching key: "clean" | "minor" | "severe"'
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

    # 🆕 new field for user-facing output
    response_text: Optional[str] = Field(
        default=None, description="Human-readable text to return to the user (e.g. for Telegram)."
    )

    @model_validator(mode="after")
    def check_required_fields(self):
        if self.plan_outline is not None and self.goal_spec is None:
            raise ValueError("goal_spec must be set if plan_outline is set")
        return self
