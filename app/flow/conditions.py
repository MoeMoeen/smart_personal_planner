"""
Legacy router functions for fallback/deterministic flow conditional branching.

NOTE: For post-planning routing, use app.flow.router.route_after_planning_result
This module contains legacy routers used in deterministic fallback flows only.
"""

from __future__ import annotations
from typing import Any
import logging

log = logging.getLogger(__name__)


def route_after_confirm_a(state: Any) -> str:
    """
    Router after user_confirm_a_node.
    Expects state to expose either attributes or dict keys:
      - confirmed_a: "confirm" | "revise" | "cancel"
    Returns next node name or "END".
    """
    confirmed = None
    if hasattr(state, "confirmed_a"):
        confirmed = getattr(state, "confirmed_a")
    elif isinstance(state, dict):
        confirmed = state.get("confirmed_a")

    if confirmed == "confirm":
        return "task_generation_node"
    if confirmed == "revise":
        return "planning_node"
    if confirmed == "cancel":
        return "END"
    # Default safe branch
    return "clarification_node"


def route_after_validation_key(state: Any) -> str:
    """
    Key-producing router for validation branching.
    Returns one of: "clean", "minor", "severe"; used with a mapping in the adapter.
    """
    key = None
    if hasattr(state, "validation_key"):
        key = getattr(state, "validation_key")
    elif isinstance(state, dict):
        key = state.get("validation_key")
    return key or "clean"



