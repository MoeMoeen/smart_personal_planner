# app/cognitive/nodes/task_generation.py
"""
Detailed Task Generation Node
- Expands PlanOutline into OccurrenceTasks
- Uses memory context for task style and preferences
- Returns OccurrenceTasks for downstream nodes
"""
from __future__ import annotations
from typing import Any, Dict, List
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




# =============================
# app/nodes/task_generation.py
# =============================


def task_generation(state: Dict[str, Any]) -> Dict[str, Any]:
    """Expand outline into tasks. Replace stub with LLM + rules when ready."""
    history = state.setdefault("execution_history", [])
    history.append({"node": "task_generation"})

    outline = state.get("outline", {})
    occ = outline.get("occurrences", 1)
    tasks: List[Dict[str, Any]] = []
    for i in range(1, occ + 1):
        tasks.append({"title": f"Task {i}", "duration_min": 30})
    state["tasks"] = tasks
    state["last_node"] = "task_generation"
    return state