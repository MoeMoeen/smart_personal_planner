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

from app.utils.logging import PlanningLogger, log_operation, TokenUsageTracker

from app.cognitive.state.graph_state import GraphState
from app.cognitive.contracts.types import InteractionPolicy
from app.config.agent_config import SOFT_BUDGET_PER_TURN_USD, PLANNING_DEBUG
from app.cognitive.agents.react_agent import create_planning_react_agent
from app.utils.run_events import start_run as _events_start_run, end_run as _events_end_run


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
        self.logger = PlanningLogger("planning_controller")
        self.token_tracker = TokenUsageTracker()

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
        # Set up logging context
        session_id = getattr(state, 'session_id', None) or (state.memory_context.session_id if state.memory_context else None)
        user_id = getattr(state, 'user_id', None) or (state.memory_context.user_id if state.memory_context else None)
        
        if session_id:
            self.logger.session_id = session_id
            self.logger._context["session_id"] = session_id
        if user_id:
            self.logger.user_id = user_id
            self.logger._context["user_id"] = user_id

        with log_operation(self.logger, "planning_session",
                          goal_title=state.goal_context.get('title', 'unknown') if state.goal_context else (state.user_input[:100] if state.user_input else 'unknown'),
                          current_status=state.planning_status,
                          user_input_length=len(state.user_input) if state.user_input else 0) as operation_id:
            
            turn_budget = TurnBudget()
            policy = self._policy(state)
            
            self.logger.info("session_initialized",
                operation_id=operation_id,
                policy_conversation_style=policy.conversation_style,
                policy_autonomy_level=policy.autonomy,
                policy_talkativeness=policy.talkativeness,
                budget_soft_limit=turn_budget.soft_limit,
                budget_spent=turn_budget.spent
            )

            user_message = state.user_input
            if not user_message:
                self.logger.warning("missing_user_input",
                    operation_id=operation_id,
                    thread_id=None
                )
                state.planning_status = "needs_clarification"
                state.response_text = "Please share your goal or what you want to plan for."
                self._trace(state, stage="AGENT_ENTRY", event="missing_user_input", thread_id=None)
                return state
            
            if not os.getenv("OPENAI_API_KEY"):
                self.logger.error("missing_api_key",
                    operation_id=operation_id,
                    thread_id=None
                )
                state.planning_status = "needs_clarification"
                state.response_text = "LLM not configured. Set OPENAI_API_KEY to enable agent."
                self._trace(state, stage="AGENT_ENTRY", event="missing_api_key", thread_id=None)
                return state

            # High-Autonomy Path: Agent handles everything with user's interaction policy
            self.logger.info("creating_agent", operation_id=operation_id)
            graph, cfg = create_planning_react_agent(interaction_policy=policy)
            if graph is None:
                self.logger.error("agent_creation_failed", 
                    operation_id=operation_id,
                    reason="graph_is_none"
                )
                state.planning_status = "needs_clarification"
                state.response_text = "Agent unavailable. Check LangGraph dependencies."
                self._trace(state, stage="AGENT_ENTRY", event="react_agent_unavailable")
                return state
            
            self.logger.info("agent_created_successfully", 
                operation_id=operation_id,
                graph_type=type(graph).__name__,
                config_keys=list(cfg.keys()) if cfg else []
            )

            # Prepare thread id and config
            thread_id = None
            try:
                uid = state.memory_context.user_id if state.memory_context else None
                gid = None
                thread_id = f"user_{uid}:{gid or 'planning'}" if uid else None
            except Exception as e:
                self.logger.warning("thread_id_generation_failed",
                    operation_id=operation_id,
                    error=str(e)
                )
                thread_id = None
            
            if cfg and isinstance(cfg, dict) and "config" in cfg:
                cfg["config"]["configurable"]["thread_id"] = thread_id
            
            self.logger.info("thread_configured",
                operation_id=operation_id,
                thread_id=thread_id,
                has_memory_context=state.memory_context is not None
            )

            # Budget pre-check (soft)
            if not turn_budget.can_spend(0.0):
                self.logger.warning("budget_limit_reached",
                    operation_id=operation_id,
                    thread_id=thread_id,
                    spent=turn_budget.spent,
                    limit=turn_budget.soft_limit
                )
                state.planning_status = "needs_clarification"
                state.response_text = "Budget soft limit reached. Reply 'continue' to proceed."
                self._trace(state, stage="AGENT_ENTRY", event="soft_budget_pause")
                return state

            # Invoke agent once; agent owns internal tool sequencing. Use messages-based state.
            self.logger.info(
                "agent_invocation_start",
                operation_id=operation_id,
                thread_id=thread_id,
                user_message_length=len(user_message),
                user_message_preview=user_message[:200],
            )

            agent_start = time.time()
            try:
                conf = cfg.get("config", {}) if isinstance(cfg, dict) else {}
                messages_state = {"messages": [{"role": "user", "content": user_message}]}
                _events_start_run()
                result = graph.invoke(messages_state, config=conf)  # type: ignore
                duration_ms = int((time.time() - agent_start) * 1000)

                # Extract agent output from messages
                agent_output = ""
                if isinstance(result, dict) and "messages" in result and result["messages"]:
                    last_msg = result["messages"][-1]
                    if hasattr(last_msg, "content"):
                        agent_output = str(last_msg.content)
                    elif isinstance(last_msg, dict) and "content" in last_msg:
                        agent_output = str(last_msg["content"])
                elif isinstance(result, dict) and "output" in result:
                    agent_output = str(result["output"])

                preview = agent_output[:500] if agent_output else None

                self.logger.info(
                    "agent_invocation_success",
                    operation_id=operation_id,
                    thread_id=thread_id,
                    duration_ms=duration_ms,
                    result_type=type(result).__name__,
                    output_length=len(agent_output),
                    output_preview=agent_output[:200] if agent_output else "no_output",
                )

                # Token/cost estimate (very rough)
                estimated_tokens = len(user_message) + len(agent_output)
                estimated_cost = estimated_tokens * 0.00002
                self.token_tracker.record_call("react_agent", estimated_tokens, estimated_cost)
                turn_budget.add_cost(estimated_cost)

                state.response_text = preview or "Agent finished."
                state.planning_status = state.planning_status or "needs_clarification"
                self._trace(
                    state,
                    stage="AGENT_EXIT",
                    event="react_agent_ok",
                    thread_id=thread_id,
                    duration_ms=duration_ms,
                    agent_output_preview=preview,
                )

                usage_summary = self.token_tracker.get_summary()
                self.logger.info(
                    "session_metrics",
                    operation_id=operation_id,
                    **usage_summary,
                    final_status=state.planning_status,
                )

                # Collect and optionally echo compact run events
                try:
                    run_events = _events_end_run()
                except Exception:
                    run_events = []
                state.run_metadata["run_events"] = run_events
                if PLANNING_DEBUG and run_events:
                    print("Compact run events:")
                    for ev in run_events:
                        label = ev.get("label") or ev.get("name") or ev.get("stage") or ev.get("type")
                        outcome = ev.get("qc_action") or ev.get("ok") or ev.get("outcome")
                        print(f" - {label}: {outcome}")
                return state

            except Exception as e:
                duration_ms = int((time.time() - agent_start) * 1000)
                self.logger.error(
                    "agent_invocation_failed",
                    operation_id=operation_id,
                    thread_id=thread_id,
                    duration_ms=duration_ms,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                state.planning_status = "needs_clarification"
                state.response_text = f"Agent error: {e}"
                # End & attach any collected events on error
                try:
                    run_events = _events_end_run()
                except Exception:
                    run_events = []
                state.run_metadata["run_events"] = run_events
                self._trace(
                    state,
                    stage="AGENT_EXIT",
                    event="react_agent_error",
                    error=str(e),
                    duration_ms=duration_ms,
                    thread_id=thread_id,
                )
                return state

