# app/cognitive/nodes/planning_node.py
"""
Agentic Planning Node (placeholder)
- Contract: reads GraphState, writes plan_outline, roadmap, schedule and approvals
- Real implementation will be a ReAct-style agent; this is a stub placeholder.
"""
from __future__ import annotations
from app.cognitive.state.graph_state import GraphState


def planning_node(state: GraphState) -> GraphState:
    """Placeholder planning node that currently raises to prevent accidental use.
    The real agent will be implemented in later phases.
    """
    raise NotImplementedError("planning_node agent not implemented yet.")
