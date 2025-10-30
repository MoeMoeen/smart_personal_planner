"""
Planning Controller — High-Autonomy Agent Path

Purpose:
- Thin harness around the ReAct agent for budgets, caps, and tracing.
- Agent owns all conversation, cognition, and tool sequencing.
- Controller provides safety guardrails and checkpointing.

Notes:
- Simplified to focus on agent-first path only.
- Deterministic FSM path removed for clarity.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import time
import os

from app.cognitive.state.graph_state import GraphState
from app.cognitive.contracts.types import InteractionPolicy
from app.config.agent_config import SOFT_BUDGET_PER_TURN_USD
from app.cognitive.agents.react_agent import create_planning_react_agent


# TODO: Remove unused controller states once deterministic FSM path is fully removed

@dataclass
class TurnBudget:
    soft_limit: float = SOFT_BUDGET_PER_TURN_USD
    spent: float = 0.0

    def can_spend(self, estimate: float) -> bool:
        return (self.spent + estimate) <= self.soft_limit

    def add_cost(self, cost: float) -> None:
        self.spent += max(0.0, cost)


class PlanningController:
    """High-Autonomy Planning Controller
    
    Thin harness around the ReAct agent. Agent owns all conversation, cognition,
    and tool sequencing. Controller provides budgets, caps, and tracing only.
    """

    def __init__(self):
        # TODO: Remove tool registry once deterministic path is fully removed
        pass

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
        """High-Autonomy Planning Flow
        
        Delegates entirely to the ReAct agent. Agent owns conversation, cognition,
        and tool sequencing. Controller provides only safety harness.
        """
        turn_budget = TurnBudget()
        policy = self._policy(state)

        # High-Autonomy Path: Agent handles everything with user's interaction policy
        graph, cfg = create_planning_react_agent(interaction_policy=policy)
        if graph is None:
            state.planning_status = "needs_clarification"
            state.response_text = "Agent unavailable. Check LangGraph dependencies."
            self._trace(state, stage="AGENT_ENTRY", event="react_agent_unavailable")
            return state

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
            return state

        # TODO: The deterministic FSM path (COLLECT_CONTEXT -> DRAFT_OUTLINE -> VALIDATE_OUTLINE -> 
        # DRAFT_ROADMAP -> VALIDATE_ROADMAP -> DRAFT_SCHEDULE -> VALIDATE_SCHEDULE -> SEEK_APPROVAL)
        # has been removed to focus on the high-autonomy agent path only. This included:
        # - Tool registry and ToolExecutor
        # - Multi-stage FSM loop with turn limits and budget checks
        # - Pattern selection, node generation, grammar validation
        # - Roadmap building, schedule generation, portfolio probing
        # - Approval handling with various policies
        # If fallback behavior is needed, re-implement as minimal stub or delegate to agent.
