"""
Strategy Interpretation Node
- Converts user input into structured GoalSpec
- Injects relevant memory context (MemoryContext)
- Returns GoalSpec for downstream nodes
"""
from app.cognitive.contracts.types import GoalSpec, MemoryContext

def strategy_interpretation_node(user_input: str, memory_context: MemoryContext) -> GoalSpec:
    """
    Stub for strategy interpretation node.
    Args:
        user_input: Raw user request
        memory_context: Injected memory context
    Returns:
        GoalSpec: Structured goal specification
    """
    # TODO: Implement LLM-based interpretation
    raise NotImplementedError("Strategy interpretation node not implemented yet.")
