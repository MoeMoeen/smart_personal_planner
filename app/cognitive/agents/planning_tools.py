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
from uuid import uuid4
from datetime import datetime, timedelta, timezone
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


# ─────────────────────────────────────────────────────────────
# Step 5 Tools: RoadmapBuilder, ScheduleGenerator, PortfolioProbe
# Minimal deterministic implementations (no LLM)
# ─────────────────────────────────────────────────────────────

class RoadmapBuilderInput(BaseModel):
    outline: Dict[str, Any]  # Expect PlanOutline.model_dump()
    roadmap_context: Optional[Dict[str, Any]] = None


class RoadmapBuilderTool:
    name = "roadmap_builder"
    description = "Transform PlanOutline to Roadmap with minimal adjustments"
    prerequisites: List[str] = ["outline"]
    produces: List[str] = ["roadmap"]

    def run(self, params: RoadmapBuilderInput) -> ToolResult:
        # Minimal transformation: mirror outline nodes into a Roadmap-like dict
        outline = params.outline or {}
        try:
            root_id = outline.get("root_id") or str(uuid4())
            nodes = outline.get("nodes") or []
            # Ensure nodes at least has a root goal for validity downstream
            if not nodes:
                nodes = [
                    {
                        "id": str(uuid4()),
                        "parent_id": None,
                        "node_type": "goal",
                        "level": 1,
                        "title": "Auto-root goal",
                        "status": "pending",
                        "progress": 0.0,
                        "origin": "system",
                        "dependencies": [],
                        "tags": [],
                        "metadata": {},
                    }
                ]
                root_id = nodes[0]["id"]
            roadmap_context = params.roadmap_context or {"scope": "auto", "cadence": "weekly"}
            data = {
                "root_id": root_id,
                "roadmap_context": roadmap_context,
                "nodes": nodes,
                # Pass through outline.pattern if present
                "pattern": outline.get("pattern"),
            }
            return ToolResult(ok=True, confidence=0.65, explanations=["Roadmap mirrored from outline (stub)."], data={"roadmap": data})
        except Exception as e:
            return ToolResult(ok=False, confidence=0.0, explanations=[f"roadmap_builder_error: {e}"], data={})


class ScheduleGeneratorInput(BaseModel):
    roadmap: Dict[str, Any]  # Expect Roadmap.model_dump()
    start_time: Optional[datetime] = None
    block_minutes: int = 60


class ScheduleGeneratorTool:
    name = "schedule_generator"
    description = "Generate a naive schedule: one block per leaf task node"
    prerequisites: List[str] = ["roadmap"]
    produces: List[str] = ["schedule"]

    def run(self, params: ScheduleGeneratorInput) -> ToolResult:
        try:
            tznow = params.start_time or datetime.now(timezone.utc)
            roadmap = params.roadmap or {}
            nodes = roadmap.get("nodes", [])
            # Pick up to 3 task-like nodes to schedule
            task_nodes = [n for n in nodes if n.get("node_type") in ("task", "sub_task")]
            if not task_nodes and nodes:
                # If there are no explicit tasks, schedule the first non-root node or root if only one
                task_nodes = nodes[1:2] or nodes[:1]
            blocks = []
            t = tznow
            for i, n in enumerate(task_nodes[:3]):
                start = t + timedelta(minutes=i * params.block_minutes)
                end = start + timedelta(minutes=params.block_minutes)
                blocks.append(
                    {
                        "plan_node_id": n.get("id", str(uuid4())),
                        "title": n.get("title", f"Task {i+1}"),
                        "start": start.isoformat(),
                        "end": end.isoformat(),
                        "estimated_minutes": params.block_minutes,
                        "tags": ["auto"],
                        "notes": "stub block",
                    }
                )
            return ToolResult(ok=True, confidence=0.6, explanations=["Generated naive schedule blocks (stub)."], data={"schedule": {"blocks": blocks}})
        except Exception as e:
            return ToolResult(ok=False, confidence=0.0, explanations=[f"schedule_generator_error: {e}"], data={})


class PortfolioProbeInput(BaseModel):
    schedule: Dict[str, Any]  # Expect Schedule.model_dump()
    world_model: Optional[Dict[str, Any]] = None


class PortfolioProbeTool:
    name = "portfolio_probe"
    description = "Check schedule for simple conflicts/utilization (stub)"
    prerequisites: List[str] = ["schedule"]
    produces: List[str] = ["portfolio_check"]

    def run(self, params: PortfolioProbeInput) -> ToolResult:
        # Minimal check: ensure no overlapping blocks in naive sequence
        try:
            blocks = params.schedule.get("blocks", [])
            # Since we create sequential blocks, assume no conflicts
            utilization = sum(b.get("estimated_minutes", 60) for b in blocks)
            data = {
                "conflicts": [],
                "utilization_minutes": utilization,
                "notes": "naive non-overlapping sequence (stub)",
            }
            return ToolResult(ok=True, confidence=0.7, explanations=["No conflicts detected (stub)."], data=data)
        except Exception as e:
            return ToolResult(ok=False, confidence=0.0, explanations=[f"portfolio_probe_error: {e}"], data={})


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
        RoadmapBuilderTool(),
        ScheduleGeneratorTool(),
        PortfolioProbeTool(),
    ]


# ─────────────────────────────────────────────────────────────
# Step 6 Tool: ApprovalHandler
# ─────────────────────────────────────────────────────────────

class ApprovalHandlerInput(BaseModel):
    approval_policy: Optional[str] = None  # single_final | milestone_approvals | strict_every_step
    pattern_rfc_required: bool = False
    pattern_rfc_text: Optional[str] = None
    user_feedback: Optional[str] = None  # e.g., "approve" or "propose changes: ..."


class ApprovalHandlerTool:
    name = "approval_handler"
    description = "Handle synchronous approval flow for outline/roadmap/schedule and RFCs"
    prerequisites: List[str] = ["artifacts_ready"]
    produces: List[str] = ["approval_state"]

    def run(self, params: ApprovalHandlerInput) -> ToolResult:
        fb = (params.user_feedback or "").strip().lower()
        policy = params.approval_policy or "milestone_approvals"

        # If policy is single_final and no RFC is required, auto-approve
        if not params.pattern_rfc_required and policy == "single_final":
            return ToolResult(ok=True, confidence=0.8, explanations=["Auto-approved per policy=single_final."], data={"decision": "approved"})

        # If user explicitly approves
        if fb.startswith("approve"):
            return ToolResult(ok=True, confidence=0.9, explanations=["User approved."], data={"decision": "approved"})

        # Otherwise, request approval with a concise CTA
        cta = "Reply 'approve' to proceed or 'propose changes: …'"
        if params.pattern_rfc_required:
            cta = "Reply 'approve' to accept the new subtype or 'propose changes: …'"
        return ToolResult(
            ok=True,
            confidence=0.6,
            explanations=["Awaiting user approval."],
            data={
                "decision": "pending",
                "cta": cta,
                "rfc": params.pattern_rfc_text,
            },
        )
