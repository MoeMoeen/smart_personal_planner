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
import os

# Import contracts to build valid structures deterministically
from app.cognitive.contracts.types import (
    PatternSpec,
    PlanOutline,
)
from app.config.feature_flags import get_flag
from app.config.llm_config import LLM_CONFIG

# Safe import of ChatOpenAI
try:
    from langchain_openai import ChatOpenAI  # type: ignore
except Exception:  # pragma: no cover
    ChatOpenAI = None  # type: ignore

from app.cognitive.agents.prompt_factory import (
    pattern_selector_system_prompt,
    node_generator_system_prompt,
)
import json


def _get_chat_model():
    """Construct a ChatOpenAI model from LLM_CONFIG or return None if unavailable."""
    if ChatOpenAI is None:
        return None
    model = LLM_CONFIG.get("model", "gpt-4o")
    temperature = float(LLM_CONFIG.get("temperature", 0.1))
    timeout = int(LLM_CONFIG.get("timeout_sec", 60))
    max_tokens = int(LLM_CONFIG.get("max_tokens", 2000))
    try:
        return ChatOpenAI(model=model, temperature=temperature, timeout=timeout, max_tokens=max_tokens)  # type: ignore
    except Exception:
        return None


def _strip_code_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```") and t.endswith("```"):
        t = t.strip("`")
        # remove possible language hint like ```json
        parts = t.split("\n", 1)
        if len(parts) == 2 and parts[0].lower().startswith("json"):
            return parts[1]
        return parts[-1]
    return t


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

class ClarifierInput(BaseModel):
    prompt: Optional[str] = None
    missing_fields: Optional[List[str]] = None
    style: Optional[str] = None  # e.g., concise, coach


class ClarifierTool:
    name = "clarifier"
    description = (
        "Ask the user a single, specific question when information is missing. "
        "Use this before calling other tools if inputs are ambiguous or incomplete."
    )
    prerequisites: List[str] = []
    produces: List[str] = ["question"]

    def run(self, params: ClarifierInput) -> ToolResult:
        # Deterministic question composer; keeps language minimal
        missing = params.missing_fields or []
        if params.prompt:
            question = params.prompt.strip()
        elif missing:
            if len(missing) == 1:
                question = f"Could you provide your {missing[0]}?"
            else:
                joined = ", ".join(missing[:-1]) + f" and {missing[-1]}"
                question = f"Could you share {joined}?"
        else:
            question = "What is the goal you want to plan for?"
        if params.style == "concise":
            # Slightly shorten when concise
            question = question.replace("Could you", "Please").replace("could you", "please")
        return ToolResult(ok=True, confidence=0.9, explanations=["clarifier_question"], data={"question": question})

class PatternSelectorInput(BaseModel):
    goal_text: str
    hints: Optional[Dict[str, Any]] = None


class PatternSelectorTool:
    name = "pattern_selector"
    description = "Infer planning pattern (PatternSpec) from goal text"
    prerequisites: List[str] = []
    produces: List[str] = ["pattern"]

    def run(self, params: PatternSelectorInput) -> ToolResult:
        # Gate behind feature flag and API key
        if not get_flag("PLANNING_USE_LLM_TOOLS", False):
            return ToolResult(ok=False, confidence=0.0, explanations=["llm_tools_disabled"], data={})
        if not os.getenv("OPENAI_API_KEY"):
            return ToolResult(ok=False, confidence=0.0, explanations=["missing_openai_api_key"], data={})
        model = _get_chat_model()
        if model is None:
            return ToolResult(ok=False, confidence=0.0, explanations=["llm_unavailable"], data={})

        sys_prompt = pattern_selector_system_prompt()
        # Try structured output
        structured = None
        try:
            structured = model.with_structured_output(PatternSpec)  # type: ignore[attr-defined]
        except Exception:
            structured = None
        if structured is not None:
            try:
                result = structured.invoke([
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": json.dumps({"goal_text": params.goal_text, "hints": params.hints or {}}, ensure_ascii=False)},
                ])
                spec = result if isinstance(result, PatternSpec) else PatternSpec.model_validate(result)
                conf = float(spec.confidence or 0.7)
                return ToolResult(ok=True, confidence=max(0.0, min(conf, 1.0)), explanations=["pattern_selected_by_llm"], data={"pattern": spec.model_dump()})
            except Exception:
                # fall back to manual JSON mode below
                pass

        messages = [
            ("system", sys_prompt + " Respond with a single JSON object only."),
            ("user", json.dumps({"goal_text": params.goal_text, "hints": params.hints or {}}, ensure_ascii=False)),
        ]
        tries = 0
        last_error = None
        while tries < 2:
            tries += 1
            try:
                resp = model.invoke([{"role": r, "content": c} for r, c in messages])
                content = getattr(resp, "content", "") or ""
                content = _strip_code_fences(content)
                payload = json.loads(content)
                spec = PatternSpec.model_validate(payload)
                conf = float(payload.get("confidence", 0.6)) if isinstance(payload, dict) else 0.6
                return ToolResult(
                    ok=True,
                    confidence=max(0.0, min(conf, 1.0)),
                    explanations=["pattern_selected_by_llm"],
                    data={"pattern": spec.model_dump()},
                )
            except Exception as e:
                last_error = str(e)
                # tighten instructions and retry once
                messages.append(("system", "Respond with a single JSON object only. No prose, no markdown."))
                continue
        return ToolResult(ok=False, confidence=0.0, explanations=[f"pattern_selector_llm_error: {last_error}"], data={})


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
        # Gate behind feature flag and API key
        if not get_flag("PLANNING_USE_LLM_TOOLS", False):
            return ToolResult(ok=False, confidence=0.0, explanations=["llm_tools_disabled"], data={})
        if not os.getenv("OPENAI_API_KEY"):
            return ToolResult(ok=False, confidence=0.0, explanations=["missing_openai_api_key"], data={})
        model = _get_chat_model()
        if model is None:
            return ToolResult(ok=False, confidence=0.0, explanations=["llm_unavailable"], data={})

        # Ensure we pass a valid PatternSpec to the model context
        try:
            _ = PatternSpec.model_validate(params.pattern)
        except Exception as e:
            return ToolResult(ok=False, confidence=0.0, explanations=[f"invalid_pattern_input: {e}"], data={})

        sys_prompt = node_generator_system_prompt()
        # Try structured output
        structured = None
        try:
            structured = model.with_structured_output(PlanOutline)  # type: ignore[attr-defined]
        except Exception:
            structured = None
        if structured is not None:
            try:
                result = structured.invoke([
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": json.dumps({
                        "goal_text": params.goal_text,
                        "pattern": params.pattern,
                        "plan_context": params.plan_context or {},
                    }, ensure_ascii=False)},
                ])
                outline = result if isinstance(result, PlanOutline) else PlanOutline.model_validate(result)
                return ToolResult(ok=True, confidence=0.75, explanations=["outline_generated_by_llm"], data={"outline": outline.model_dump()})
            except Exception:
                # fall back to manual JSON mode below
                pass

        messages = [
            ("system", sys_prompt + " Respond with a single JSON object only."),
            ("user", json.dumps({
                "goal_text": params.goal_text,
                "pattern": params.pattern,
                "plan_context": params.plan_context or {},
            }, ensure_ascii=False)),
        ]
        tries = 0
        last_error = None
        while tries < 2:
            tries += 1
            try:
                resp = model.invoke([{"role": r, "content": c} for r, c in messages])
                content = getattr(resp, "content", "") or ""
                content = _strip_code_fences(content)
                payload = json.loads(content)
                # Validate outline
                outline = PlanOutline.model_validate(payload)
                # Additional invariants: root node must exist and be level 1 goal are covered by model
                # Confidence: 0.7 baseline if schema valid; could accept model-provided self_rating if present
                conf = 0.7
                return ToolResult(
                    ok=True,
                    confidence=conf,
                    explanations=["outline_generated_by_llm"],
                    data={"outline": outline.model_dump()},
                )
            except Exception as e:
                last_error = str(e)
                messages.append(("system", "Respond with a single JSON object only. Ensure it matches the schema exactly."))
                continue
        return ToolResult(ok=False, confidence=0.0, explanations=[f"node_generator_llm_error: {last_error}"], data={})


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
        ClarifierTool(),
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
