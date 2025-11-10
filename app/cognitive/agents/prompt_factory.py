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
        "1–3 child nodes under the root are sufficient. Use structured output (no prose). "
        "Pattern consistency hints: learning_arc must include practice & reflection nodes; milestone_project should expose deliverables & dependencies; recurring_cycle should show cadence elements; progressive_accumulation_arc should show incremental layering; hybrid_project_cycle mixes project phases + habit tasks; strategic_transformation includes capability-building phases. "
        "Return strictly schema-valid JSON only."
    )


def grammar_validator_system_prompt() -> str:
    node_types = _csv(list(get_args(NodeType)))
    statuses = _csv(list(get_args(NodeStatus)))
    return (
        "You are a Plan Grammar Validator and Repairer. "
        "Given a PlanOutline JSON, validate these rules and, if invalid, return a corrected PlanOutline: "
        "1) root_id must exist in nodes. "
        "2) Root node must have parent_id=null, level=1, node_type=goal. "
        "3) All node ids are unique. "
        "4) Non-root nodes must have a valid parent_id and level>=2. "
        "5) Use allowed node_type values: [" + node_types + "] and statuses: [" + statuses + "]. "
        "If valid, return the same outline. Use structured output (PlanOutline). No prose."
    )


def semantic_critic_system_prompt(stage: str, ontology: dict) -> str:
    """
    Build a stage-specific rubric using ontology for semantic critique.
    Returns instructions to emit {ok, confidence, issues[], repair_hints[]}.
    """
    # Pull enums for extra guardrails
    node_types = _csv(list(get_args(NodeType)))
    pattern_types = _csv(list(get_args(PatternType)))
    
    # Stage-specific checks
    stage_clause = {
        "outline": (
            "Check: L1 goal exists and makes sense; phases/sub_goals/tasks are logical; "
            "tasks are actionable and specific; dependencies are reasonable; "
            "structure matches the selected pattern requirements."
        ),
        "roadmap": (
            "Check: roadmap respects outline's structure; cadence/scope/horizon consistent with pattern; "
            "sequence is plausible; trade-offs and constraints are noted; "
            "timeline is realistic given the goal complexity."
        ),
        "schedule": (
            "Check: respects roadmap cadence and dependencies; uses timezone-aware times; "
            "workload is feasible given availability; no impossible overlaps; "
            "time allocations match task complexity."
        ),
    }.get(stage, "Check artifact for conceptual consistency.")
    
    # Extract ontology components
    pattern_metadata = ontology.get("pattern_metadata", {})
    grammar_rules = ontology.get("grammar_rules", [])
    hierarchy_levels = ontology.get("hierarchy_levels", ["goal", "phase", "task"])
    
    return f"""You are a Semantic Critic for planning artifacts.

Stage: {stage}
Task: {stage_clause}

Context Guidelines:
- Hierarchy levels: {hierarchy_levels}
- Allowed node types: [{node_types}]
- Allowed pattern types: [{pattern_types}]
- Grammar rules: {grammar_rules}
- Pattern metadata (requirements): {pattern_metadata}

Evaluation Criteria:
1. Goal Alignment: Does the artifact serve the stated goal effectively?
2. Pattern Consistency: Does it follow the selected pattern's requirements and characteristics?
3. Logical Structure: Are the components well-organized and logically connected?
4. Actionability: Are tasks specific, measurable, and achievable?
5. Completeness: Are critical elements missing for this pattern type?
6. Feasibility: Is the timeline/scope realistic given typical constraints?

Pattern-Specific Requirements:
- learning_arc: Must include practice + reflection cycles, skill progression
- milestone_project: Clear deliverables, dependencies, quality gates
- recurring_cycle: Sustainable cadence, improvement feedback loops
- progressive_accumulation_arc: Incremental building, complexity progression
- hybrid_project_cycle: Mixed project + habit elements, phase transitions
- strategic_transformation: Long-term vision, capability development

Return ONLY this JSON structure:
{{"ok": boolean, "confidence": float (0.0-1.0), "issues": [string], "repair_hints": [string]}}

Where:
- ok: true if artifact passes semantic checks
- confidence: how certain you are (higher = more confident)
- issues: specific problems found (empty if ok=true)
- repair_hints: targeted suggestions for improvement (empty if ok=true)"""
