"""
Plan Structure Outline Node
- Drafts PlanOutline from GoalSpec
- Uses memory context for user preferences and history
- Returns PlanOutline for downstream nodes
"""
from app.cognitive.contracts.types import GoalSpec, PlanOutline, MemoryContext

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
