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


from app.cognitive.state.graph_state import GraphState

def plan_outline_node_test(state: GraphState) -> GraphState:
    """
    Generate a high-level plan outline.
    For demo: stub output with fake structure.
    """
    # Example outline
    outline = {
        "goal": "Fitness",
        "frequency": "3 times per week",
        "duration": "12 weeks",
        "phases": ["Warmup", "Workout", "Cooldown"]
    }

    state.plan_outline = outline
    state.response_text = (
        "📋 Here’s your proposed plan outline:\n"
        f"- Goal: {outline['goal']}\n"
        f"- Frequency: {outline['frequency']}\n"
        f"- Duration: {outline['duration']}\n"
        f"- Phases: {', '.join(outline['phases'])}\n\n"
        "Do you want to confirm this outline?"
    )
    return state
