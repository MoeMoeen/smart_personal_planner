"""
Detailed Task Generation Node
- Expands PlanOutline into OccurrenceTasks
- Uses memory context for task style and preferences
- Returns OccurrenceTasks for downstream nodes
"""
from app.cognitive.contracts.types import PlanOutline, OccurrenceTasks, MemoryContext

def task_generation_node(plan_outline: PlanOutline, memory_context: MemoryContext) -> list[OccurrenceTasks]:
    """
    Stub for task generation node.
    Args:
        plan_outline: High-level plan structure
        memory_context: Injected memory context
    Returns:
        List[OccurrenceTasks]: Tasks for each occurrence
    """
    # TODO: Implement LLM-based task generation
    raise NotImplementedError("Task generation node not implemented yet.")
