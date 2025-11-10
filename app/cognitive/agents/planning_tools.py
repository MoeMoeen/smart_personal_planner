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

from typing import Any, Dict, List, Optional, cast
from uuid import uuid4
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel, Field
import os
import time

# Import contracts to build valid structures deterministically
from app.cognitive.contracts.types import (
    PatternSpec,
    PlanOutline,
    PlanNode,
    PlanContext,
    StrategyProfile,
    NodeStatus,
)
from app.cognitive.contracts.schema_models import (
    PatternSpecSchema,
    PlanOutlineSchema,
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
    grammar_validator_system_prompt,
)
import json
from app.utils.logging import PlanningLogger, log_llm_call, log_operation
import uuid


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
# Converters: schema models -> internal rich models
# ─────────────────────────────────────────────────────────────

_UUID_NS = uuid.NAMESPACE_URL


def _uuid_from_str(stable_id: str) -> uuid.UUID:
    # Deterministic UUID for stable string ids
    return uuid.uuid5(_UUID_NS, f"planning:{stable_id}")


def _outline_from_schema(schema_obj: PlanOutlineSchema) -> PlanOutline:
    # Map string ids to UUIDs deterministically
    id_map: Dict[str, uuid.UUID] = {}
    for n in schema_obj.nodes:
        id_map[n.id] = _uuid_from_str(n.id)

    nodes: List[PlanNode] = []
    for n in schema_obj.nodes:
        status_val = n.status if n.status in {"pending", "in_progress", "done", "blocked"} else "pending"
        node = PlanNode(
            id=id_map[n.id],
            parent_id=(id_map[n.parent_id] if n.parent_id else None),
            node_type=n.node_type.value,  # aligns with internal Literal
            level=int(n.level),
            title=n.title,
            status=cast(NodeStatus, status_val),
            progress=float(n.progress),
            dependencies=[],
            tags=n.tags or [],
            metadata={},
        )
        nodes.append(node)

    root_uuid = id_map.get(schema_obj.root_id, _uuid_from_str(schema_obj.root_id))

    ctx = PlanContext(
        strategy_profile=StrategyProfile(mode="push"),
        pattern=None,
        assumptions=None,
        constraints=None,
        user_prefs=None,
    )

    return PlanOutline(
        root_id=root_uuid,
        plan_context=ctx,
        nodes=nodes,
        pattern=None,
    )


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

    def __init__(self):
        self.logger = PlanningLogger("pattern_selector_tool")

    @log_llm_call
    def run(self, params: PatternSelectorInput) -> ToolResult:
        from app.utils.run_events import record_event
        record_event("tool_start", name=self.name, label=self.name)
        with log_operation(self.logger, "pattern_selection",
                          goal_text=params.goal_text[:100],
                          has_hints=bool(params.hints)) as operation_id:
            
            # Gate behind feature flag and API key
            if not get_flag("PLANNING_USE_LLM_TOOLS", False):
                self.logger.info("tool_disabled", operation_id=operation_id, reason="feature_flag_disabled")
                return ToolResult(ok=False, confidence=0.0, explanations=["llm_tools_disabled"], data={})
            
            if not os.getenv("OPENAI_API_KEY"):
                self.logger.warning("api_key_missing", operation_id=operation_id)
                return ToolResult(ok=False, confidence=0.0, explanations=["missing_openai_api_key"], data={})
            
            model = _get_chat_model()
            if model is None:
                self.logger.error("model_unavailable", operation_id=operation_id)
                return ToolResult(ok=False, confidence=0.0, explanations=["llm_unavailable"], data={})

        sys_prompt = pattern_selector_system_prompt()
        # Try structured output with JSON schema (preferred when OPENAI_JSON_MODE)
        structured = None
        try:
            method = "json_schema" if bool(LLM_CONFIG.get("json_mode", True)) else "function_calling"
            structured = model.with_structured_output(PatternSpecSchema, method=method)  # type: ignore[attr-defined]
        except Exception:
            structured = None
        if structured is not None:
            try:
                result = structured.invoke([
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": json.dumps({"goal_text": params.goal_text, "hints": params.hints or {}}, ensure_ascii=False)},
                ])
                # Convert schema result into internal PatternSpec
                payload = getattr(result, "model_dump", lambda: result)()
                spec = PatternSpec.model_validate(payload)
                conf = float(spec.confidence or 0.7)
                tool_result = ToolResult(ok=True, confidence=max(0.0, min(conf, 1.0)), explanations=["pattern_selected_by_llm"], data={"pattern": spec.model_dump()})
                record_event("tool_complete", name=self.name, ok=True)
                return tool_result
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
                tool_result = ToolResult(
                    ok=True,
                    confidence=max(0.0, min(conf, 1.0)),
                    explanations=["pattern_selected_by_llm"],
                    data={"pattern": spec.model_dump()},
                )
                record_event("tool_complete", name=self.name, ok=True)
                return tool_result
            except Exception as e:
                last_error = str(e)
                # tighten instructions and retry once
                messages.append(("system", "Respond with a single JSON object only. No prose, no markdown."))
                continue
        record_event("tool_complete", name=self.name, ok=False, error=last_error)
        return ToolResult(ok=False, confidence=0.0, explanations=[f"pattern_selector_llm_error: {last_error}"], data={})


class GrammarValidatorInput(BaseModel):
    outline: Dict[str, Any]  # Expect PlanOutline.model_dump()


class GrammarValidationReport(BaseModel):
    valid: bool
    violations: List[str] = Field(default_factory=list)
    repaired_outline: Optional[Dict[str, Any]] = None
    repair_notes: List[str] = Field(default_factory=list)


class GrammarValidatorTool:
    name = "grammar_validator"
    description = "Validate plan outline grammar invariants and (optionally) repair via LLM"
    prerequisites: List[str] = ["outline"]
    produces: List[str] = ["validation_report"]

    def _deterministic_checks(self, outline_dict: Dict[str, Any]) -> List[str]:
        violations: List[str] = []
        try:
            outline = PlanOutline.model_validate(outline_dict)
        except Exception as e:
            return [f"schema_invalid: {e}"]

        nodes = outline.nodes
        ids = [n.id for n in nodes]
        if len(set(ids)) != len(ids):
            violations.append("duplicate_node_ids")

        if not outline.root_id:
            violations.append("missing_root_id")
        else:
            root_nodes = [n for n in nodes if n.id == outline.root_id]
            if not root_nodes:
                violations.append("root_id_not_found_in_nodes")
            else:
                root = root_nodes[0]
                if root.parent_id is not None:
                    violations.append("root_parent_must_be_null")
                if getattr(root, "level", None) != 1:
                    violations.append("root_level_must_be_1")
                if getattr(root, "node_type", None) != "goal":
                    violations.append("root_type_must_be_goal")

        # Ensure non-root nodes have a parent and level >= 2
        id_set = set(ids)
        for n in nodes:
            if n.id == outline.root_id:
                continue
            if n.parent_id is None:
                violations.append(f"node_missing_parent:{n.id}")
            elif n.parent_id not in id_set:
                violations.append(f"parent_not_found:{n.id}->{n.parent_id}")
            if getattr(n, "level", 0) is not None and getattr(n, "level", 0) < 2:
                violations.append(f"level_too_low:{n.id}")

        return violations

    def _attempt_llm_repair(self, outline_dict: Dict[str, Any]) -> tuple[Optional[Dict[str, Any]], List[str]]:
        if not get_flag("PLANNING_USE_LLM_TOOLS", False):
            return None, ["llm_tools_disabled"]
        if not os.getenv("OPENAI_API_KEY"):
            return None, ["missing_openai_api_key"]
        model = _get_chat_model()
        if model is None:
            return None, ["llm_unavailable"]

        sys_prompt = grammar_validator_system_prompt()
        # Prefer structured output to a PlanOutline (JSON schema preferred)
        structured = None
        try:
            method = "json_schema" if bool(LLM_CONFIG.get("json_mode", True)) else "function_calling"
            structured = model.with_structured_output(PlanOutlineSchema, method=method)  # type: ignore[attr-defined]
        except Exception:
            structured = None
        user_payload = json.dumps({"outline": outline_dict}, ensure_ascii=False)
        if structured is not None:
            try:
                result = structured.invoke([
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": user_payload},
                ])
                payload = getattr(result, "model_dump", lambda: result)()
                # Convert schema payload to internal outline
                try:
                    schema_outline = PlanOutlineSchema.model_validate(payload)
                    outline_obj = _outline_from_schema(schema_outline)
                    return outline_obj.model_dump(), ["repaired_via_llm_structured_output"]
                except Exception:
                    # last attempt: try direct internal validation
                    outline = PlanOutline.model_validate(payload)
                    return outline.model_dump(), ["repaired_via_llm_structured_output"]
            except Exception:
                pass

        # Fallback: ask for pure JSON object
        msgs = [
            ("system", sys_prompt + " Respond with a single JSON object only."),
            ("user", user_payload),
        ]
        try:
            resp = model.invoke([{"role": r, "content": c} for r, c in msgs])
            content = getattr(resp, "content", "") or ""
            content = _strip_code_fences(content)
            payload = json.loads(content)
            try:
                # first try schema -> internal
                schema_outline = PlanOutlineSchema.model_validate(payload)
                outline = _outline_from_schema(schema_outline)
                return outline.model_dump(), ["repaired_via_llm_json_mode"]
            except Exception:
                # fallback to internal directly
                outline = PlanOutline.model_validate(payload)
                return outline.model_dump(), ["repaired_via_llm_json_mode"]
        except Exception as e:
            return None, [f"llm_repair_failed:{e}"]

    def run(self, params: GrammarValidatorInput) -> ToolResult:
        from app.utils.run_events import record_event
        record_event("tool_start", name=self.name, label=self.name)
        outline_dict = params.outline or {}
        violations = self._deterministic_checks(outline_dict)
        if not violations:
            report = GrammarValidationReport(valid=True, violations=[])
            record_event("tool_complete", name=self.name, ok=True, valid=True)
            return ToolResult(ok=True, confidence=0.85, explanations=["outline_valid"], data=report.model_dump())

        # Try to repair with LLM; if repaired outline passes checks, return valid with repaired_outline
        repaired, notes = self._attempt_llm_repair(outline_dict)
        explanations = ["outline_invalid"] + notes
        if repaired is not None:
            post = self._deterministic_checks(repaired)
            if not post:
                report = GrammarValidationReport(valid=True, violations=[], repaired_outline=repaired, repair_notes=notes)
                record_event("tool_complete", name=self.name, ok=True, repaired=True)
                return ToolResult(ok=True, confidence=0.7, explanations=explanations + ["repaired_ok"], data=report.model_dump())
            else:
                explanations.append("repair_still_invalid")
                violations.extend(post)

        report = GrammarValidationReport(valid=False, violations=violations, repair_notes=notes)
        record_event("tool_complete", name=self.name, ok=False, violations=violations)
        return ToolResult(ok=False, confidence=0.0, explanations=explanations, data=report.model_dump())


class NodeGeneratorInput(BaseModel):
    goal_text: str
    pattern: Dict[str, Any]  # Expect PatternSpec.model_dump()
    plan_context: Optional[Dict[str, Any]] = None
    hints: Optional[List[str]] = None  # Targeted repair hints from SemanticCritic


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
        # Try structured output (JSON schema preferred)
        structured = None
        try:
            method = "json_schema" if bool(LLM_CONFIG.get("json_mode", True)) else "function_calling"
            structured = model.with_structured_output(PlanOutlineSchema, method=method)  # type: ignore[attr-defined]
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
                        "hints": params.hints or [],
                    }, ensure_ascii=False)},
                ])
                payload = getattr(result, "model_dump", lambda: result)()
                try:
                    schema_outline = PlanOutlineSchema.model_validate(payload)
                    outline_obj = _outline_from_schema(schema_outline)
                    return ToolResult(ok=True, confidence=0.75, explanations=["outline_generated_by_llm"], data={"outline": outline_obj.model_dump()})
                except Exception:
                    outline = PlanOutline.model_validate(payload)
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
                "hints": params.hints or [],
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
                # Try schema then internal
                try:
                    schema_outline = PlanOutlineSchema.model_validate(payload)
                    outline_obj = _outline_from_schema(schema_outline)
                except Exception:
                    outline_obj = PlanOutline.model_validate(payload)
                # Confidence baseline if valid
                conf = 0.7
                return ToolResult(
                    ok=True,
                    confidence=conf,
                    explanations=["outline_generated_by_llm"],
                    data={"outline": outline_obj.model_dump()},
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


class OntologySnapshotTool:
    name = "ontology_snapshot"
    description = "Return planning ontology: hierarchy levels, grammar rules, pattern metadata."
    prerequisites: List[str] = []
    produces: List[str] = ["ontology"]

    def run(self, _params: Optional[BaseModel] = None) -> ToolResult:
        """Deterministic canonical ontology snapshot so SemanticCritic always has full context."""
        ontology = {
            "hierarchy_levels": ["goal", "phase", "sub_goal", "task", "sub_task", "micro_goal"],
            "grammar_rules": [
                "L1 is node_type=goal with parent_id=null and level=1",
                "Goal must have ≥1 descendant task",
                "Non-root nodes must have valid parent and level>=2",
            ],
            "pattern_metadata": {
                "learning_arc": {
                    "must_include": ["practice", "reflection"],
                    "hints": ["skill progression", "weekly checkpoints"],
                },
                "milestone_project": {
                    "must_include": ["deliverables", "dependencies", "quality gates"],
                    "hints": ["milestones", "acceptance criteria"],
                },
                "recurring_cycle": {
                    "must_include": ["cadence", "feedback"],
                    "hints": ["sustainable iteration", "review loop"],
                },
                "progressive_accumulation_arc": {
                    "must_include": ["incremental builds", "complexity progression"],
                    "hints": ["layering", "checkpoint consolidation"],
                },
                "hybrid_project_cycle": {
                    "must_include": ["project phases", "habit reinforcement"],
                    "hints": ["phase transitions", "ritual tasks"],
                },
                "strategic_transformation": {
                    "must_include": ["long-term vision", "capability development"],
                    "hints": ["maturity stages", "capability gaps"],
                },
            },
        }
        return ToolResult(ok=True, confidence=1.0, explanations=["ontology_snapshot"], data={"ontology": ontology})


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
    hints: Optional[List[str]] = None  # Targeted repair hints from SemanticCritic


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
    hints: Optional[List[str]] = None  # Targeted repair hints from SemanticCritic


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
        NodeGeneratorTool(),  # producer
        GrammarValidatorTool(),  # validator
        OntologySnapshotTool(),  # deterministic context provider
        SemanticCriticTool(),  # semantic evaluation
        RoadmapBuilderTool(),
        ScheduleGeneratorTool(),
        PortfolioProbeTool(),
        ApprovalHandlerTool(),
    ]


# ─────────────────────────────────────────────────────────────
# Step 6 Tool: ApprovalHandler
# ─────────────────────────────────────────────────────────────

class SemanticCriticInput(BaseModel):
    stage: str  # "outline" | "roadmap" | "schedule"
    goal_text: str
    selected_pattern: Optional[Dict[str, Any]] = None  # PatternSpec.model_dump()
    artifact: Dict[str, Any]  # outline/roadmap/schedule JSON
    plan_context: Optional[Dict[str, Any]] = None
    ontology: Optional[Dict[str, Any]] = None  # hierarchy_levels, grammar_rules, pattern_metadata


class SemanticCriticTool:
    name = "semantic_critic"
    description = "Critique artifact for conceptual/semantic consistency and provide repair hints"
    prerequisites: List[str] = ["artifact"]
    produces: List[str] = ["semantic_report"]

    def __init__(self):
        self.logger = PlanningLogger("semantic_critic_tool")

    @log_llm_call
    def run(self, params: SemanticCriticInput) -> ToolResult:
        from app.utils.run_events import record_event
        record_event("tool_start", name=self.name, stage=params.stage, label=f"{self.name}:{params.stage}")
        with log_operation(self.logger, "semantic_critique",
                          stage=params.stage,
                          goal_preview=params.goal_text[:50],
                          has_pattern=bool(params.selected_pattern),
                          has_ontology=bool(params.ontology)) as operation_id:
            
            # Gate checks with logging
            if not get_flag("PLANNING_USE_LLM_TOOLS", False):
                self.logger.info("tool_disabled", operation_id=operation_id, reason="feature_flag_disabled")
                return ToolResult(ok=False, confidence=0.0, explanations=["llm_tools_disabled"], data={})
            
            if not os.getenv("OPENAI_API_KEY"):
                self.logger.warning("api_key_missing", operation_id=operation_id)
                return ToolResult(ok=False, confidence=0.0, explanations=["missing_openai_api_key"], data={})
            
            model = _get_chat_model()
            if model is None:
                self.logger.error("model_unavailable", operation_id=operation_id)
                return ToolResult(ok=False, confidence=0.0, explanations=["llm_unavailable"], data={})

            # Ensure ontology is available; deterministically fetch if missing
            if not params.ontology:
                try:
                    auto_onto = OntologySnapshotTool().run()
                    if auto_onto.ok:
                        params.ontology = auto_onto.data.get("ontology", {})
                        self.logger.info("ontology_auto_fetched", operation_id=operation_id)
                except Exception as _:
                    # If fetching ontology fails, proceed without but log
                    self.logger.warning("ontology_fetch_failed", operation_id=operation_id)

            # Get stage-specific rubric from prompt factory
            from app.cognitive.agents.prompt_factory import semantic_critic_system_prompt
            sys_prompt = semantic_critic_system_prompt(params.stage, params.ontology or {})

            # Prepare payload for critique
            payload = {
                "goal_text": params.goal_text,
                "selected_pattern": params.selected_pattern or {},
                "artifact": params.artifact,
                "plan_context": params.plan_context or {},
            }

            self.logger.info("critique_starting",
                operation_id=operation_id,
                stage=params.stage,
                artifact_keys=list(params.artifact.keys()) if isinstance(params.artifact, dict) else "non_dict",
                pattern_type=params.selected_pattern.get("pattern_type") if params.selected_pattern else None,
                ontology_keys=list(params.ontology.keys()) if params.ontology else [],
                payload_size=len(json.dumps(payload, default=str))
            )

            # Expect strict JSON verdict {ok, confidence, issues[], repair_hints[]}
            msgs = [
                ("system", sys_prompt + " Respond with a single JSON object only."),
                ("user", json.dumps(payload, ensure_ascii=False, default=str)),
            ]
            
            tries = 0
            last_error = None
            while tries < 2:
                tries += 1
                try:
                    start_time = time.time()
                    resp = model.invoke([{"role": r, "content": c} for r, c in msgs])
                    duration_ms = int((time.time() - start_time) * 1000)
                    
                    content = getattr(resp, "content", "") or ""
                    content = _strip_code_fences(content)
                    
                    self.logger.info("critique_response_received",
                        operation_id=operation_id,
                        attempt=tries,
                        duration_ms=duration_ms,
                        content_length=len(content)
                    )
                    
                    verdict = json.loads(content)
                    
                    ok = bool(verdict.get("ok", False))
                    conf = float(verdict.get("confidence", 0.5))
                    issues = verdict.get("issues", [])
                    hints = verdict.get("repair_hints", [])
                    
                    self.logger.info("critique_complete",
                        operation_id=operation_id,
                        ok=ok,
                        confidence=conf,
                        issues_count=len(issues),
                        hints_count=len(hints),
                        issues=issues[:3],  # Log first 3 issues
                        repair_hints=hints[:3]  # Log first 3 hints
                    )
                    
                    tool_result = ToolResult(ok=ok, confidence=conf, explanations=["semantic_critic"], data={
                        "semantic_report": {
                            "ok": ok,
                            "confidence": conf,
                            "issues": issues,
                            "repair_hints": hints,
                        }
                    })
                    record_event("tool_complete", name=self.name, stage=params.stage, ok=ok, issues=len(issues), hints=len(hints))
                    return tool_result
                except Exception as e:
                    last_error = str(e)
                    self.logger.warning("critique_attempt_failed",
                        operation_id=operation_id,
                        attempt=tries,
                        error=str(e),
                        error_type=type(e).__name__
                    )
                    msgs.append(("system", "Respond with JSON only: {'ok': bool, 'confidence': float, 'issues': [str], 'repair_hints': [str]}"))
                    continue
            
            self.logger.error("critique_failed",
                operation_id=operation_id,
                final_error=last_error,
                attempts_made=tries
            )
            record_event("tool_complete", name=self.name, stage=params.stage, ok=False, error=last_error)
            return ToolResult(ok=False, confidence=0.0, explanations=[f"semantic_critic_error:{last_error}"], data={})


class QCDecisionInput(BaseModel):
    stage: str  # "outline" | "roadmap" | "schedule"
    grammar_report: Dict[str, Any]  # GrammarValidationReport.model_dump()
    semantic_report: Dict[str, Any]  # {ok, confidence, issues[], repair_hints[]}
    max_retries: int = 3
    attempts_made: int = 0


class QCDecisionTool:
    name = "qc_decision"
    description = "Deterministic accept/repair decision based on grammar + semantic verdicts"
    prerequisites: List[str] = ["grammar_report", "semantic_report"]
    produces: List[str] = ["qc_action"]

    def run(self, params: QCDecisionInput) -> ToolResult:
        from app.utils.run_events import record_event
        record_event("tool_start", name=self.name, stage=params.stage, label=f"qc_decision:{params.stage}")
        g = params.grammar_report or {}
        s = params.semantic_report or {}
        grammar_ok = bool(g.get("valid", False))
        semantic_ok = bool(s.get("ok", False))
        action = "accept"
        hints: List[str] = []

        if not grammar_ok or not semantic_ok:
            if params.attempts_made >= params.max_retries:
                action = "escalate"
            else:
                action = "retry"
                hints = (g.get("repair_notes", []) or []) + (s.get("repair_hints", []) or [])
        record_event("qc_decision", stage=params.stage, qc_action=action, grammar_ok=grammar_ok, semantic_ok=semantic_ok, hints=len(hints))
        record_event("tool_complete", name=self.name, stage=params.stage, ok=(action=="accept"))
        return ToolResult(
            ok=True,
            confidence=1.0,
            explanations=["qc_decision"],
            data={
                "qc_action": action,
                "hints": hints[:6],  # cap number of hints
            },
        )


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
