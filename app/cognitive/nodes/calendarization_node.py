# app/nodes/calendarization.py
"""
Calendarization / Time Allocation Node
- Assigns time slots to tasks using world state
- Returns CalendarizedPlan
"""
from __future__ import annotations
from typing import Any, Dict, List
from app.cognitive.contracts.types import OccurrenceTasks, CalendarizedPlan, MemoryContext
from app.cognitive.world.world_state import WorldState

def calendarization_node(occurrence_tasks: list[OccurrenceTasks], world_state: WorldState, memory_context: MemoryContext) -> CalendarizedPlan:
    """
    Stub for calendarization node.
    Args:
        occurrence_tasks: Tasks for each occurrence
        world_state: Current global world state
        memory_context: Injected memory context
    Returns:
        CalendarizedPlan: Tasks with assigned time slots
    """
    # TODO: Implement time allocation logic
    raise NotImplementedError("Calendarization node not implemented yet.")


# =============================
# app/nodes/calendarization.py
# =============================


def calendarization(state: Dict[str, Any]) -> Dict[str, Any]:
    history = state.setdefault("execution_history", [])
    history.append({"node": "calendarization"})

    tasks = state.get("tasks", [])
    schedule: List[Dict[str, Any]] = []
    # Stub: assign sequential slots
    for idx, t in enumerate(tasks):
        schedule.append({"title": t.get("title", f"Task {idx+1}"), "slot": f"Day {idx+1} 09:00-09:30"})
    state["schedule"] = schedule
    state["last_node"] = "calendarization"
    return state
