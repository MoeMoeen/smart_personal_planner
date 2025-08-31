# app/cognitive/nodes/plan_outline.py
"""
Plan Structure Outline Node
- Drafts PlanOutline from GoalSpec
- Uses memory context for user preferences and history
- Returns PlanOutline for downstream nodes
"""
from __future__ import annotations
from app.cognitive.contracts.types import GoalSpec, PlanOutline, MemoryContext
from typing import Any, Dict

def plan_outline_node(goal_spec: GoalSpec, memory_context: MemoryContext) -> PlanOutline:
    """
    Stub for plan outline node.
    Args:
        goal_spec: Structured goal specification
        memory_context: Injected memory context
    Returns:
        PlanOutline: High-level plan structure
    """
    # TODO: Implement LLM-based outline generation
    raise NotImplementedError("Plan outline node not implemented yet.")



# =============================
# app/nodes/plan_outline.py
# =============================


def plan_outline(state: Dict[str, Any]) -> Dict[str, Any]:
    """Draft a simple outline. In real code, call your LLM chain here."""
    history = state.setdefault("execution_history", [])
    history.append({"node": "plan_outline"})

    # Minimal demo payload
    state["outline"] = {
        "title": state.get("goal", "Untitled Plan"),
        "occurrences": 2,
        "cycles": "weekly",
    }
    state["last_node"] = "plan_outline"
    return state

