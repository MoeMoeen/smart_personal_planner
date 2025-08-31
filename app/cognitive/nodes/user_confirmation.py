# app/cognitive/nodes/user_confirmation.py
"""
User Confirmation Node
- Presents plan or outline to user for approval or revision
- Logs feedback as episodic memory
"""
from __future__ import annotations
from typing import Any, Dict
from app.cognitive.contracts.types import PlanOutline, CalendarizedPlan, MemoryContext

def user_confirmation_node(plan_or_plan_outline, memory_context: MemoryContext) -> dict:
    """
    Stub for user confirmation node.
    Args:
        plan_or_plan_outline: PlanOutline or CalendarizedPlan to present
        memory_context: Injected memory context
    Returns:
        dict: User feedback (approved: bool, corrections: str, etc.)
    """
    # TODO: Implement user interaction and feedback logging
    raise NotImplementedError("User confirmation node not implemented yet.")




# =============================
# app/nodes/user_confirmation.py
# =============================


def user_confirm_a(state: Dict[str, Any]) -> Dict[str, Any]:
    """Demo: auto-confirm unless caller set `force_reject_a=True` in state."""
    history = state.setdefault("execution_history", [])
    history.append({"node": "user_confirm_a"})

    confirmed = not state.get("force_reject_a", False)
    state["confirm_a"] = bool(confirmed)
    state["last_node"] = "user_confirm_a"

    # In a richer flow, a conditional edge would branch here. For v0 linear demo, just record.
    return state
