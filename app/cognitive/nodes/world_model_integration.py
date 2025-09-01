# app/cognitive/nodes/world_model_integration.py
"""
World Model Integration Node
- Injects up-to-date world state (tasks, availability, capacity)
- Returns context-enriched OccurrenceTasks
"""
# =============================
# app/nodes/world_model_integration.py
# =============================
from __future__ import annotations
from typing import Any, Dict

def world_model_integration(state: Dict[str, Any]) -> Dict[str, Any]:
    history = state.setdefault("execution_history", [])
    history.append({"node": "world_model_integration"})

    # TODO: Stub: annotate tasks with fake constraints summary
    tasks = state.get("tasks", [])
    state["wm_enriched"] = {"tasks_count": len(tasks), "constraints": {"work_hours": "9-5", "blackouts": []}}
    state["last_node"] = "world_model_integration"
    return state