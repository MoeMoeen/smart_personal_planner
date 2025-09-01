# app/flow/conditions.py

from __future__ import annotations
from typing import Any

def route_after_confirm_a(state: Any) -> str:
    """
    If user rejected at confirm A, route back to 'plan_outline'; otherwise continue to 'task_generation'.
    Expects that 'user_confirm_a' set state['confirm_a'] = True/False.
    """
    try:
        confirmed = bool(state.get("confirm_a"))
    except Exception:
        confirmed = False
    return "task_generation" if confirmed else "plan_outline"
