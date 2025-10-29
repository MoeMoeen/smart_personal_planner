"""
Planning Controller (State Machine Scaffold) — Phase 7 Step 4

Purpose:
- Provide an explicit controller around the inner ReAct agent/tools.
- Enforce caps (turns/retries/wall-time/budget per turn) and policy-aware routing.
- Sequence tool calls based on prerequisites/produces metadata.

Notes:
- This scaffold is import-safe and does not perform real LLM calls.
- Core tools are stubs; controller returns a safe needs_clarification until
  tools are implemented in subsequent steps.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict
import time
import os
import hashlib

from app.cognitive.state.graph_state import GraphState
from app.cognitive.contracts.types import InteractionPolicy
from app.config.agent_config import (
    TURN_LIMIT,
    WALL_TIME_SEC,
    SOFT_BUDGET_PER_TURN_USD,
)
from app.cognitive.agents.planning_tools import (
    PatternSelectorTool,
    GrammarValidatorTool,
    NodeGeneratorTool,
    BrainstormerTool,
    OptionCrafterTool,
    PatternSelectorInput,
    GrammarValidatorInput,
    NodeGeneratorInput,
    BrainstormerInput,
    ToolResult,
    RoadmapBuilderTool,
    ScheduleGeneratorTool,
    PortfolioProbeTool,
    RoadmapBuilderInput,
    ScheduleGeneratorInput,
    PortfolioProbeInput,
    ApprovalHandlerTool,
    ApprovalHandlerInput,
)
from app.cognitive.contracts.types import Roadmap, Schedule
from app.config.feature_flags import get_flag
from app.cognitive.agents.react_agent import create_planning_react_agent
from app.cognitive.agents.prompts import AGENT_SYSTEM_PROMPT


# ─────────────────────────────────────────────────────────────
# Controller States (string constants for clarity)
# ─────────────────────────────────────────────────────────────

COLLECT_CONTEXT = "COLLECT_CONTEXT"
DRAFT_OUTLINE = "DRAFT_OUTLINE"
VALIDATE_OUTLINE = "VALIDATE_OUTLINE"
DRAFT_ROADMAP = "DRAFT_ROADMAP"
VALIDATE_ROADMAP = "VALIDATE_ROADMAP"
DRAFT_SCHEDULE = "DRAFT_SCHEDULE"
VALIDATE_SCHEDULE = "VALIDATE_SCHEDULE"
SEEK_APPROVAL = "SEEK_APPROVAL"


@dataclass
class TurnBudget:
    soft_limit: float = SOFT_BUDGET_PER_TURN_USD
    spent: float = 0.0

    def can_spend(self, estimate: float) -> bool:
        return (self.spent + estimate) <= self.soft_limit

    def add_cost(self, cost: float) -> None:
        self.spent += max(0.0, cost)


class ToolExecutor:
    """Safe tool runner with simple in-memory caching.

    Cache key incorporates tool name and a stable hash of the params dict.
    """

    def __init__(self):
        self._cache: Dict[str, ToolResult] = {}

    @staticmethod
    def _stable_hash(data: Dict[str, Any]) -> str:
        payload = repr(sorted(data.items())).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def run(self, tool: Any, params_model: Any) -> ToolResult:
        params_dict = params_model.model_dump()
        key = f"{getattr(tool, 'name', tool.__class__.__name__)}::{self._stable_hash(params_dict)}"
        if key in self._cache:
            return self._cache[key]
        try:
            result: ToolResult = tool.run(params_model)
        except Exception as e:
            result = ToolResult(ok=False, confidence=0.0, explanations=[f"tool_error: {e}"], data={})
        self._cache[key] = result
        return result


class PlanningController:
    """Explicit state machine driving the planning flow.

    This scaffold executes a minimal path and returns needs_clarification until
    core tools are implemented. It records trace entries and respects caps.
    """

    def __init__(self):
        self.tools = {
            "pattern_selector": PatternSelectorTool(),
            "grammar_validator": GrammarValidatorTool(),
            "node_generator": NodeGeneratorTool(),
            "brainstormer": BrainstormerTool(),
            "option_crafter": OptionCrafterTool(),
            "roadmap_builder": RoadmapBuilderTool(),
            "schedule_generator": ScheduleGeneratorTool(),
            "portfolio_probe": PortfolioProbeTool(),
            "approval_handler": ApprovalHandlerTool(),
        }
        self.exec = ToolExecutor()

    def _policy(self, state: GraphState) -> InteractionPolicy:
        # Session override wins, else MemoryContext default, else safe defaults
        if state.interaction_policy:
            return state.interaction_policy
        if state.memory_context and state.memory_context.interaction_policy:
            return state.memory_context.interaction_policy
        return InteractionPolicy()  # defaults

    def _trace(self, state: GraphState, **fields: Any) -> None:
        record = {
            **fields,
        }
        state.planning_trace.append(record)

    def run(self, state: GraphState) -> GraphState:
        start = time.time()
        turn_budget = TurnBudget()
        policy = self._policy(state)

        # Agent-first path: when enabled, delegate the entire flow to the ReAct agent.
        if get_flag("PLANNING_USE_REACT_AGENT", False):
            graph, cfg = create_planning_react_agent(system_prompt=AGENT_SYSTEM_PROMPT)
            if graph is None:
                # Agent unavailable; fall back to deterministic path below
                self._trace(state, stage="AGENT_ENTRY", event="react_agent_unavailable")
            else:
                # Prepare thread id and config
                thread_id = None
                try:
                    uid = state.memory_context.user_id if state.memory_context else None
                    gid = None
                    thread_id = f"user_{uid}:{gid or 'planning'}" if uid else None
                except Exception:
                    thread_id = None
                if cfg and isinstance(cfg, dict) and "config" in cfg:
                    cfg["config"]["configurable"]["thread_id"] = thread_id

                user_message = state.user_input
                if not user_message:
                    state.planning_status = "needs_clarification"
                    state.response_text = "Please share your goal or what you want to plan for."
                    self._trace(state, stage="AGENT_ENTRY", event="missing_user_input", thread_id=thread_id)
                    return state
                if not os.getenv("OPENAI_API_KEY"):
                    state.planning_status = "needs_clarification"
                    state.response_text = "LLM not configured. Set OPENAI_API_KEY to enable agent."
                    self._trace(state, stage="AGENT_ENTRY", event="missing_api_key", thread_id=thread_id)
                    return state

                # Budget pre-check (soft)
                if not turn_budget.can_spend(0.0):
                    state.planning_status = "needs_clarification"
                    state.response_text = "Budget soft limit reached. Reply 'continue' to proceed."
                    self._trace(state, stage="AGENT_ENTRY", event="soft_budget_pause")
                    return state

                # Invoke agent once; agent owns internal tool sequencing
                agent_start = time.time()
                try:
                    conf = cfg.get("config", {}) if isinstance(cfg, dict) else {}
                    result = graph.invoke({"input": user_message}, config=conf)  # type: ignore
                    duration_ms = int((time.time() - agent_start) * 1000)
                    preview = (str(result)[:500] if result is not None else None)
                    state.response_text = preview or "Agent finished."
                    # Do not force-complete; agent may ask a question—let UI route next turn
                    state.planning_status = state.planning_status or "needs_clarification"
                    self._trace(
                        state,
                        stage="AGENT_EXIT",
                        event="react_agent_ok",
                        thread_id=thread_id,
                        duration_ms=duration_ms,
                        agent_output_preview=preview,
                    )
                    return state
                except Exception as e:
                    duration_ms = int((time.time() - agent_start) * 1000)
                    state.planning_status = "needs_clarification"
                    state.response_text = f"Agent error: {e}"
                    self._trace(
                        state,
                        stage="AGENT_EXIT",
                        event="react_agent_error",
                        error=str(e),
                        duration_ms=duration_ms,
                        thread_id=thread_id,
                    )
                    # Fall through to deterministic path if needed (no early return)

        # Start in COLLECT_CONTEXT stage
        current_stage = COLLECT_CONTEXT
        turn = 0

        while turn < TURN_LIMIT and (time.time() - start) < WALL_TIME_SEC:
            turn += 1

            # Soft per-turn budget check (no real costs yet; placeholder)
            if not turn_budget.can_spend(0.0):
                # Ask user to allow continuing; for scaffold, we pause
                state.planning_status = "needs_clarification"
                state.response_text = (
                    "Budget soft limit reached this turn. Reply 'continue' to proceed or 'pause' to stop."
                )
                self._trace(state, stage=current_stage, event="soft_budget_pause", cost_delta=0.0)
                return state

            if current_stage == COLLECT_CONTEXT:
                # Use policy to decide if we brainstorm variants first (stubbed)
                if policy.brainstorming_preference != "on_demand":
                    gc: Dict[str, Any] = state.goal_context or {}
                    topic = str(gc.get("description", "goal"))
                    ideas = self.exec.run(
                        self.tools["brainstormer"],
                        BrainstormerInput(topic=topic, max_ideas=2, style=policy.conversation_style),
                    )
                    self._trace(state, stage=current_stage, tool="brainstormer", confidence=ideas.confidence)

                # Move to DRAFT_OUTLINE
                current_stage = DRAFT_OUTLINE
                continue

            if current_stage == DRAFT_OUTLINE:
                # Optional: delegate to ReAct agent behind feature flag
                if get_flag("PLANNING_USE_REACT_AGENT", False):
                    graph, cfg = create_planning_react_agent(system_prompt=AGENT_SYSTEM_PROMPT)
                    if graph is not None:
                        # Prepare minimal config with optional thread id
                        thread_id = None
                        try:
                            uid = state.memory_context.user_id if state.memory_context else None
                            gid = None
                            thread_id = f"user_{uid}:{gid or 'new'}" if uid else None
                        except Exception:
                            thread_id = None
                        if cfg and isinstance(cfg, dict) and "config" in cfg:
                            cfg["config"]["configurable"]["thread_id"] = thread_id

                        # Only invoke when an API key is present AND we have real user input
                        user_message = state.user_input
                        if os.getenv("OPENAI_API_KEY") and user_message:
                            agent_start = time.time()
                            try:
                                conf = cfg.get("config", {}) if isinstance(cfg, dict) else {}
                                _result = graph.invoke({"input": user_message}, config=conf)  # type: ignore
                                duration_ms = int((time.time() - agent_start) * 1000)
                                # We are not consuming outputs yet; record trace only
                                self._trace(
                                    state,
                                    stage=current_stage,
                                    event="react_agent_invoked",
                                    thread_id=thread_id,
                                    duration_ms=duration_ms,
                                    cost_delta=0.0,
                                    agent_output_preview=(str(_result)[:200] if _result is not None else None),
                                )
                            except Exception as e:
                                duration_ms = int((time.time() - agent_start) * 1000)
                                self._trace(
                                    state,
                                    stage=current_stage,
                                    event="react_agent_error",
                                    error=str(e),
                                    thread_id=thread_id,
                                    duration_ms=duration_ms,
                                )
                        elif not user_message:
                            self._trace(
                                state,
                                stage=current_stage,
                                event="react_agent_skipped_no_user_input",
                                thread_id=thread_id,
                            )
                        else:
                            self._trace(
                                state,
                                stage=current_stage,
                                event="react_agent_skipped_no_api_key",
                                thread_id=thread_id,
                            )
                    else:
                        self._trace(state, stage=current_stage, event="react_agent_unavailable")
                # Attempt pattern selection (stub returns ok=False)
                ps = self.exec.run(
                    self.tools["pattern_selector"],
                    PatternSelectorInput(goal_text=str(state.goal_context or {}), hints=None),
                )
                self._trace(state, stage=current_stage, tool="pattern_selector", confidence=ps.confidence)

                if ps.ok and ps.data.get("pattern"):
                    # Consume selected pattern into state
                    try:
                        from app.cognitive.contracts.types import PatternSpec  # local import to avoid cycles at module import
                        spec = PatternSpec.model_validate(ps.data["pattern"])  # type: ignore
                        state.selected_pattern = spec
                        # RFC signaling: require approval if proposing a new subtype
                        maybe_sub = (spec.subtype or "")
                        state.pattern_rfc_required = bool(maybe_sub.startswith("proposed:"))
                        state.pattern_rfc_text = spec.rfc
                    except Exception as e:
                        # Pattern invalid; request clarification
                        state.planning_status = "needs_clarification"
                        state.response_text = f"Pattern selection failed validation: {e}"
                        self._trace(state, stage=current_stage, event="pattern_validation_error", error=str(e))
                        return state

                    # Proceed to NodeGenerator
                    ng = self.exec.run(
                        self.tools["node_generator"],
                        NodeGeneratorInput(
                            goal_text=str(state.goal_context or {}),
                            pattern=spec.model_dump(),
                            plan_context=(state.plan_outline.plan_context.model_dump() if state.plan_outline else None),
                        ),
                    )
                    self._trace(state, stage=current_stage, tool="node_generator", confidence=ng.confidence)

                    if ng.ok and ng.data.get("outline"):
                        try:
                            from app.cognitive.contracts.types import PlanOutline  # avoid top-level circular imports
                            outline = PlanOutline.model_validate(ng.data["outline"])  # type: ignore
                            # Ensure outline.pattern carries the selected pattern if missing
                            if outline.pattern is None:
                                outline.pattern = state.selected_pattern
                            state.plan_outline = outline
                            current_stage = VALIDATE_OUTLINE
                        except Exception as e:
                            state.planning_status = "needs_clarification"
                            state.response_text = f"Outline generation failed validation: {e}"
                            self._trace(state, stage=current_stage, event="outline_validation_error", error=str(e))
                            return state
                    else:
                        state.planning_status = "needs_clarification"
                        state.response_text = "Outline generator returned no result."
                        self._trace(state, stage=current_stage, event="outline_generator_empty")
                        return state
                else:
                    # Stubbed path: ask for clarification and exit cleanly
                    state.planning_status = "needs_clarification"
                    state.response_text = (
                        "Planning controller is initialized. Core tools are not yet active. "
                        "Please confirm to proceed once tools are available."
                    )
                    self._trace(state, stage=current_stage, event="stub_exit", reason="pattern_selector_not_ready")
                    return state

            if current_stage == VALIDATE_OUTLINE:
                # Validate outline (stub returns not OK)
                # If outline exists, attempt grammar validation; allow soft-pass when LLM tools are disabled
                outline_dump = state.plan_outline.model_dump() if state.plan_outline else {}
                gv = self.exec.run(
                    self.tools["grammar_validator"],
                    GrammarValidatorInput(outline=outline_dump),
                )
                self._trace(state, stage=current_stage, tool="grammar_validator", confidence=gv.confidence)

                from app.config.feature_flags import get_flag as _get_flag
                llm_tools_on = bool(_get_flag("PLANNING_USE_LLM_TOOLS", False))

                if (gv.ok and gv.data.get("valid")) or (not llm_tools_on and bool(state.plan_outline)):
                    # Accept outline as valid (either explicit OK or soft-pass when LLM tools are off)
                    state.validation_result = gv.data if gv and gv.data else {"validator": "grammar", "status": "soft_pass"}
                    current_stage = DRAFT_ROADMAP
                else:
                    # Attempt a minimal auto-repair if possible (ensure root and at least one child)
                    try:
                        if state.plan_outline and not state.plan_outline.nodes:
                            # unreachable in normal flow; safeguard
                            state.plan_outline.nodes = []  # type: ignore
                        # If still invalid or validator strongly objects, pause
                    except Exception:
                        pass
                    state.planning_status = "needs_clarification"
                    state.response_text = (
                        "Outline requires validation and repair. Please provide more context or wait for tool enablement."
                    )
                    self._trace(state, stage=current_stage, event="outline_validation_blocked")
                    return state

            if current_stage == DRAFT_ROADMAP:
                if not state.plan_outline:
                    state.planning_status = "needs_clarification"
                    state.response_text = "Missing outline; cannot draft roadmap yet."
                    self._trace(state, stage=current_stage, event="missing_outline")
                    return state
                # Optional: delegate to ReAct agent behind feature flag (Roadmap stage)
                if get_flag("PLANNING_USE_REACT_AGENT", False):
                    graph, cfg = create_planning_react_agent(system_prompt=AGENT_SYSTEM_PROMPT)
                    if graph is not None:
                        thread_id = None
                        try:
                            uid = state.memory_context.user_id if state.memory_context else None
                            gid = None
                            thread_id = f"user_{uid}:{gid or 'new'}" if uid else None
                        except Exception:
                            thread_id = None
                        if cfg and isinstance(cfg, dict) and "config" in cfg:
                            cfg["config"]["configurable"]["thread_id"] = thread_id

                        user_message = state.user_input
                        if os.getenv("OPENAI_API_KEY") and user_message:
                            agent_start = time.time()
                            try:
                                conf = cfg.get("config", {}) if isinstance(cfg, dict) else {}
                                _result = graph.invoke({"input": user_message}, config=conf)  # type: ignore
                                duration_ms = int((time.time() - agent_start) * 1000)
                                self._trace(
                                    state,
                                    stage=current_stage,
                                    event="react_agent_invoked",
                                    thread_id=thread_id,
                                    duration_ms=duration_ms,
                                    cost_delta=0.0,
                                    agent_output_preview=(str(_result)[:200] if _result is not None else None),
                                )
                            except Exception as e:
                                duration_ms = int((time.time() - agent_start) * 1000)
                                self._trace(
                                    state,
                                    stage=current_stage,
                                    event="react_agent_error",
                                    error=str(e),
                                    thread_id=thread_id,
                                    duration_ms=duration_ms,
                                )
                        elif not user_message:
                            self._trace(state, stage=current_stage, event="react_agent_skipped_no_user_input", thread_id=thread_id)
                        else:
                            self._trace(state, stage=current_stage, event="react_agent_skipped_no_api_key", thread_id=thread_id)
                    else:
                        self._trace(state, stage=current_stage, event="react_agent_unavailable")
                rb = self.exec.run(
                    self.tools["roadmap_builder"],
                    RoadmapBuilderInput(outline=state.plan_outline.model_dump(), roadmap_context={}),
                )
                self._trace(state, stage=current_stage, tool="roadmap_builder", confidence=rb.confidence)
                if rb.ok and rb.data.get("roadmap"):
                    try:
                        state.roadmap = Roadmap.model_validate(rb.data["roadmap"])  # type: ignore
                    except Exception:
                        # If validation fails, request clarification
                        state.planning_status = "needs_clarification"
                        state.response_text = "Roadmap generation failed validation (stub)."
                        return state
                    current_stage = VALIDATE_ROADMAP
                else:
                    state.planning_status = "needs_clarification"
                    state.response_text = "Roadmap builder not ready."
                    return state

            if current_stage == VALIDATE_ROADMAP:
                # Minimal validation: ensure roadmap has nodes
                if not state.roadmap or not state.roadmap.nodes:
                    state.planning_status = "needs_clarification"
                    state.response_text = "Roadmap is empty; cannot continue."
                    self._trace(state, stage=current_stage, event="empty_roadmap")
                    return state
                # Proceed to schedule drafting
                current_stage = DRAFT_SCHEDULE

            if current_stage == DRAFT_SCHEDULE:
                if not state.roadmap:
                    state.planning_status = "needs_clarification"
                    state.response_text = "Missing roadmap; cannot draft schedule."
                    self._trace(state, stage=current_stage, event="missing_roadmap")
                    return state
                # Optional: delegate to ReAct agent behind feature flag (Schedule stage)
                if get_flag("PLANNING_USE_REACT_AGENT", False):
                    graph, cfg = create_planning_react_agent(system_prompt=AGENT_SYSTEM_PROMPT)
                    if graph is not None:
                        thread_id = None
                        try:
                            uid = state.memory_context.user_id if state.memory_context else None
                            gid = None
                            thread_id = f"user_{uid}:{gid or 'new'}" if uid else None
                        except Exception:
                            thread_id = None
                        if cfg and isinstance(cfg, dict) and "config" in cfg:
                            cfg["config"]["configurable"]["thread_id"] = thread_id

                        user_message = state.user_input
                        if os.getenv("OPENAI_API_KEY") and user_message:
                            agent_start = time.time()
                            try:
                                conf = cfg.get("config", {}) if isinstance(cfg, dict) else {}
                                _result = graph.invoke({"input": user_message}, config=conf)  # type: ignore
                                duration_ms = int((time.time() - agent_start) * 1000)
                                self._trace(
                                    state,
                                    stage=current_stage,
                                    event="react_agent_invoked",
                                    thread_id=thread_id,
                                    duration_ms=duration_ms,
                                    cost_delta=0.0,
                                    agent_output_preview=(str(_result)[:200] if _result is not None else None),
                                )
                            except Exception as e:
                                duration_ms = int((time.time() - agent_start) * 1000)
                                self._trace(
                                    state,
                                    stage=current_stage,
                                    event="react_agent_error",
                                    error=str(e),
                                    thread_id=thread_id,
                                    duration_ms=duration_ms,
                                )
                        elif not user_message:
                            self._trace(state, stage=current_stage, event="react_agent_skipped_no_user_input", thread_id=thread_id)
                        else:
                            self._trace(state, stage=current_stage, event="react_agent_skipped_no_api_key", thread_id=thread_id)
                    else:
                        self._trace(state, stage=current_stage, event="react_agent_unavailable")
                sg = self.exec.run(
                    self.tools["schedule_generator"],
                    ScheduleGeneratorInput(roadmap=state.roadmap.model_dump()),
                )
                self._trace(state, stage=current_stage, tool="schedule_generator", confidence=sg.confidence)
                if sg.ok and sg.data.get("schedule"):
                    try:
                        state.schedule = Schedule.model_validate(sg.data["schedule"])  # type: ignore
                    except Exception:
                        state.planning_status = "needs_clarification"
                        state.response_text = "Schedule generation failed validation (stub)."
                        return state
                    current_stage = VALIDATE_SCHEDULE
                else:
                    state.planning_status = "needs_clarification"
                    state.response_text = "Schedule generator not ready."
                    return state

            if current_stage == VALIDATE_SCHEDULE:
                if not state.schedule:
                    state.planning_status = "needs_clarification"
                    state.response_text = "Missing schedule for validation."
                    self._trace(state, stage=current_stage, event="missing_schedule")
                    return state
                pp = self.exec.run(
                    self.tools["portfolio_probe"],
                    PortfolioProbeInput(schedule=state.schedule.model_dump(), world_model=state.world_model),
                )
                self._trace(state, stage=current_stage, tool="portfolio_probe", confidence=pp.confidence)
                conflicts = (pp.data or {}).get("conflicts", [])
                if conflicts:
                    state.planning_status = "needs_scheduling_escalation"
                    state.escalate_reason = "conflicts_detected"
                    state.response_text = "Schedule has conflicts; escalation required."
                    return state
                # Proceed to approval step (Step 6)
                current_stage = SEEK_APPROVAL

            if current_stage == SEEK_APPROVAL:
                policy = self._policy(state)
                ah = self.exec.run(
                    self.tools["approval_handler"],
                    ApprovalHandlerInput(
                        approval_policy=policy.approval_policy,
                        pattern_rfc_required=bool(state.pattern_rfc_required),
                        pattern_rfc_text=state.pattern_rfc_text,
                        user_feedback=state.user_feedback,
                    ),
                )
                self._trace(state, stage=current_stage, tool="approval_handler", confidence=ah.confidence)
                decision = (ah.data or {}).get("decision")
                if decision == "approved":
                    state.outline_approved = True
                    state.roadmap_approved = True
                    state.schedule_approved = True
                    state.pattern_rfc_required = False
                    state.planning_status = "complete"
                    state.response_text = "Approved. Plan ready to proceed."
                    return state
                # Pending: request clarification with CTA
                cta = (ah.data or {}).get("cta") or "Reply 'approve' to proceed or 'propose changes: …'"
                state.planning_status = "needs_clarification"
                state.response_text = cta
                return state

        # Caps reached; abort gracefully
        state.planning_status = "aborted"
        state.response_text = "Controller caps reached before completion."
        self._trace(state, stage="CAPS_EXIT", event="aborted", turns=turn)
        return state
