"""
Router functions for post-node conditional branching in LangGraph flows.
"""

from __future__ import annotations
from typing import Literal
import logging
from app.cognitive.state.graph_state import GraphState

log = logging.getLogger(__name__)

RouteKey = Literal[
    "to_world_model",
    "to_scheduling_escalation", 
    "to_planning_loop",
    "to_summary_or_end",
]

# Post-planning edges keyed by router output
# POST_PLANNING_EDGES = {
#     "to_world_model": ["world_model_integration_node", "persistence_node"],
#     "to_scheduling_escalation": ["scheduling_escalation_node"],
#     "to_planning_loop": ["planning_node"],
#     "to_summary_or_end": ["summary_node"],
# }


def route_after_planning_result(state: GraphState) -> RouteKey:
    """
    Single point of truth for post-planning branching (Phase 5).
    Branches **only** on `planning_status` as agreed in v1.2/v1.3.

    Mapping:
      - complete                   -> to_world_model
      - needs_scheduling_escalation-> to_scheduling_escalation  
      - needs_clarification        -> to_planning_loop
      - aborted / anything else    -> to_summary_or_end
    """
    status = (state.planning_status or "").strip()
    route: RouteKey

    if status == "complete":
        route = "to_world_model"
    elif status == "needs_scheduling_escalation":
        route = "to_scheduling_escalation"
    elif status == "needs_clarification":
        route = "to_planning_loop"
    else:
        # Default safeguard: summarize and end
        route = "to_summary_or_end"

    log.info(
        "router.post_planning",
        extra={
            "intent": state.intent,
            "status": status,
            "route": route,
            "outline_approved": state.outline_approved,
            "roadmap_approved": state.roadmap_approved,
            "schedule_approved": state.schedule_approved,
            "has_outline": state.plan_outline is not None,
            "has_roadmap": state.roadmap is not None,
            "has_schedule": state.schedule is not None,
        }
    )
    return route