# app/flow/conditions.py
"""
Intelligent routing conditions for the flow compiler.
"""
from __future__ import annotations
from app.cognitive.brain.intent_registry_routes import map_intent_to_node
from typing import Any
import logging

from app.cognitive.brain.intent_recognition.intent_recognition_node import detect_intent
from app.cognitive.contracts.types import MemoryContext

logger = logging.getLogger(__name__)

def route_after_confirm_a(state: Any) -> str:
    """
    Intelligent router after user_confirm_a.
    Calls intent recognition brain (LLM) to decide the next node dynamically.
    Ask the intent recognition brain (LLM) where to go next.
    - Input: full GraphState (user message, memory, etc.)
    - Output: node name string, e.g. "task_generation" or "plan_outline" or "ask_question"
    """
    try:
        user_msg = getattr(state, "user_input", None) or state.get("user_input")
        memory_ctx: MemoryContext = getattr(state, "memory_context", None) or state.get("memory_context")

        # 1. detect intent using brain
        intent_result = detect_intent(user_msg, memory_ctx)
        intent = intent_result.intent

        # 2. map intent to next node
        next_node = map_intent_to_node(intent)
        logger.info(f"Router: intent={intent} → next_node={next_node}")
        return next_node

    except Exception as e:
        logger.error(f"route_after_confirm_a failed: {e}")
        # fallback: safe default
        return "plan_outline"


# def route_after_confirm_a(state):
    # intent_result = detect_intent(state["user_input"], state["memory_context"])
    # if intent_result.intent == "confirm_outline":
    #     return "task_generation"
    # elif intent_result.intent == "revise_outline":
    #     return "plan_outline"
    # elif intent_result.intent == "clarify":
    #     return "clarification_node"
    # else:
    #     return "plan_outline"
