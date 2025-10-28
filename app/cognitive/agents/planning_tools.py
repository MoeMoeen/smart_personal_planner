"""
Planning tools (skeletons) for the Phase 7 ReAct planning agent.

These are minimal, import-safe stubs with Pydantic I/O and metadata, designed
to be wired into a LangGraph agent. They intentionally avoid external
dependencies and do not perform real LLM calls yet.

All tools return a common envelope:
    {"ok": bool, "confidence": float, "explanations": list[str], "data": dict}

Each tool exposes `prerequisites` and `produces` metadata for controller checks.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────
# Common I/O schemas
# ─────────────────────────────────────────────────────────────

class ToolResult(BaseModel):
    ok: bool = True
    confidence: float = 0.0
    explanations: List[str] = Field(default_factory=list)
    data: Dict[str, Any] = Field(default_factory=dict)


# ─────────────────────────────────────────────────────────────
# Core tools (skeletons)
# ─────────────────────────────────────────────────────────────

class PatternSelectorInput(BaseModel):
    goal_text: str
    hints: Optional[Dict[str, Any]] = None


class PatternSelectorTool:
    name = "pattern_selector"
    description = "Infer planning pattern (PatternSpec) from goal text"
    prerequisites: List[str] = []
    produces: List[str] = ["pattern"]

    def run(self, params: PatternSelectorInput) -> ToolResult:
        # Skeleton implementation (no LLM): return not-OK placeholder
        return ToolResult(
            ok=False,
            confidence=0.0,
            explanations=[
                "PatternSelectorTool is a stub; integrate LLM and PatternSpec construction in Phase 7b."
            ],
            data={},
        )


class GrammarValidatorInput(BaseModel):
    outline: Dict[str, Any]  # Expect PlanOutline.model_dump()


class GrammarValidatorTool:
    name = "grammar_validator"
    description = "Validate plan outline grammar invariants and dual-axis rules"
    prerequisites: List[str] = ["outline"]
    produces: List[str] = ["validation_report"]

    def run(self, params: GrammarValidatorInput) -> ToolResult:
        # Skeleton: not-OK placeholder; real rules come later
        return ToolResult(
            ok=False,
            confidence=0.0,
            explanations=["GrammarValidatorTool is a stub; implement rules in Phase 7b."],
            data={"valid": False, "violations": []},
        )


class NodeGeneratorInput(BaseModel):
    goal_text: str
    pattern: Dict[str, Any]  # Expect PatternSpec.model_dump()
    plan_context: Optional[Dict[str, Any]] = None


class NodeGeneratorTool:
    name = "node_generator"
    description = "Generate PlanOutline nodes given pattern and goal context"
    prerequisites: List[str] = ["pattern"]
    produces: List[str] = ["outline"]

    def run(self, params: NodeGeneratorInput) -> ToolResult:
        # Skeleton: not-OK placeholder; will emit a minimal valid outline in Phase 7b
        return ToolResult(
            ok=False,
            confidence=0.0,
            explanations=["NodeGeneratorTool is a stub; implement structure in Phase 7b."],
            data={},
        )


# ─────────────────────────────────────────────────────────────
# Utility tools (policy-aware helpers)
# ─────────────────────────────────────────────────────────────

class BrainstormerInput(BaseModel):
    topic: str
    max_ideas: int = 3
    style: Optional[str] = None  # e.g., concise, coach


class BrainstormerTool:
    name = "brainstormer"
    description = "Produce a quick set of ideas or variants for the user to pick from"
    prerequisites: List[str] = []
    produces: List[str] = ["ideas"]

    def run(self, params: BrainstormerInput) -> ToolResult:
        # Minimal, deterministic stub (no LLM): echo variations of the topic
        ideas = [f"Idea {i+1}: {params.topic}" for i in range(max(1, min(params.max_ideas, 3)))]
        if params.style == "concise":
            explanations = ["Condensed brainstorm per conversation_style=concise."]
        else:
            explanations = ["Default brainstorm (stub)."]
        return ToolResult(ok=True, confidence=0.6, explanations=explanations, data={"ideas": ideas})


class OptionCrafterInput(BaseModel):
    brief: str
    max_options: int = 2
    style: Optional[str] = None


class OptionCrafterTool:
    name = "option_crafter"
    description = "Craft 2–3 concise options for a plan/action with clear differences"
    prerequisites: List[str] = []
    produces: List[str] = ["options"]

    def run(self, params: OptionCrafterInput) -> ToolResult:
        count = max(1, min(params.max_options, 3))
        options = [
            {
                "label": f"Option {i+1}",
                "summary": f"{params.brief} — variant {i+1}",
            }
            for i in range(count)
        ]
        expl = [
            "OptionCrafter stub produced concise variants; integrate LLM later for richer differences."
        ]
        if params.style == "concise":
            expl.append("Kept options succinct due to conversation_style=concise.")
        return ToolResult(ok=True, confidence=0.6, explanations=expl, data={"options": options})


# Registry helper (optional)
def get_planning_tool_skeletons():
    """Return a list of tool instances for initial wiring tests.

    Note: These are skeletons and will not perform real planning.
    """
    return [
        PatternSelectorTool(),
        GrammarValidatorTool(),
        NodeGeneratorTool(),
        BrainstormerTool(),
        OptionCrafterTool(),
    ]
