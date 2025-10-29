"""
Prompt factory utilities that derive allowable values from contracts/models.

Avoid hardcoding enums in prompts; build them dynamically from Literal types
so changes in contracts propagate automatically.
"""

from __future__ import annotations

from typing import get_args

from app.cognitive.contracts.types import (
    PatternType,
    PatternSubtype,
    StrategyMode,
    NodeType,
    NodeStatus,
)


def _csv(values: list[str]) -> str:
    return ", ".join(values)


def pattern_selector_system_prompt() -> str:
    types = _csv(list(get_args(PatternType)))
    subtypes = _csv(list(get_args(PatternSubtype)))
    return (
        "You are a Pattern Selector for planning. Select the best-fitting canonical pattern. "
        f"Allowed pattern_type: [{types}]. "
        f"Optional subtype: one of [{subtypes}] or omit if N/A. "
        "Output must be a valid PatternSpec via structured output. Keep responses minimal."
    )


def node_generator_system_prompt() -> str:
    modes = _csv(list(get_args(StrategyMode)))
    node_types = _csv(list(get_args(NodeType)))
    statuses = _csv(list(get_args(NodeStatus)))
    return (
        "You are an Outline Generator. Produce a minimal but valid PlanOutline. "
        f"Strategy modes: [{modes}]. Node types: [{node_types}]. Statuses: [{statuses}]. "
        "Include exactly one level=1 root goal with parent_id=null; root_id must equal that node's id. "
        "1–3 child nodes under the root are sufficient. Use structured output (no prose)."
    )
