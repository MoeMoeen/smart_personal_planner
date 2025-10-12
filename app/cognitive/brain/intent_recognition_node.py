# app/cognitive/brain/intent_recognition/intent_recognition_node.py

from __future__ import annotations
import json
import logging
from typing import Any

from app.cognitive.utils.prompt_utils import build_intent_messages
from app.cognitive.contracts.types import MemoryContext
from app.cognitive.contracts.results import IntentResult
from app.cognitive.utils.llm_backend import get_llm_backend
from app.cognitive.memory.semantic import create_semantic_memory
from app.cognitive.nodes.base_node import BaseNode
from app.cognitive.brain.intent_registry_routes import ALL_INTENTS


logger = logging.getLogger(__name__)


# -------------------------------------------------------------------
# Core function
# -------------------------------------------------------------------

...

def detect_intent(user_message: str, memory_context: MemoryContext) -> IntentResult:
    """
    Call LLM to detect intent and extract parameters.
    Supports 'clarify' intent when required info is missing.
    Always returns a safe IntentResult even if LLM fails.
    """
    backend = get_llm_backend("openai")
    messages = build_intent_messages(user_message, memory_context)
    resp = backend.chat(messages=messages, temperature=0)

    try:
        data = json.loads(resp.content)
    except Exception as e:
        logger.error(f"[IntentRecognition] Failed to parse LLM JSON: {resp.content[:120]}... ({e})")
        return IntentResult(
            intent="ask_question",
            parameters={"raw_output": resp.content},
            confidence=0.0,
            notes="LLM returned invalid JSON",
            llm_raw_response=resp.content,
            token_usage=getattr(resp, "token_usage", {}) or {},
            llm_cost=getattr(resp, "cost", 0.0),
        )

    # Normalize and validate intent
    intent = str(data.get("intent", "ask_question")).strip().lower()
    valid_intents = {i["name"] for i in ALL_INTENTS}
    if intent not in valid_intents:
        logger.warning(f"[IntentRecognition] Unknown intent from LLM: {intent}, defaulting to 'ask_question'")
        intent = "ask_question"

    parameters = data.get("parameters", {})
    confidence = float(data.get("confidence", 0.0))
    notes = data.get("notes", "")

    # log every intent to semantic memory
    try:
        user_id = getattr(memory_context, "user_id", None)
        if user_id is not None:
            semantic = create_semantic_memory(user_id)
            semantic.log_operation(
                operation_type=f"{intent}_intent",
                details={
                    "user_input": user_message,
                    "memory_context": (
                        memory_context.__dict__
                        if hasattr(memory_context, "__dict__")
                        else str(memory_context)
                    ),
                    "llm_output": resp.content,
                },
            )
    except Exception as e:
        logger.warning(f"[IntentRecognition] Failed to store {intent} intent in semantic memory: {e}")

    return IntentResult(
        intent=intent,
        parameters=parameters,
        confidence=confidence,
        notes=notes,
        llm_raw_response=resp.content,
        token_usage=getattr(resp, "token_usage", {}) or {},
        llm_cost=getattr(resp, "cost", 0.0),
    )

# -------------------------------------------------------------------
# Class-based node wrapper (for FlowCompiler / Graph use)
# -------------------------------------------------------------------

class IntentRecognitionNode(BaseNode[IntentResult]):
    """Wraps detect_intent for graph integration."""

    def __init__(self, memory_context: MemoryContext):
        super().__init__(name="intent_recognition")
        self.memory_context = memory_context

    def run(self, input_data: Any, context: Any = None) -> IntentResult:
        # Extract user message safely from string, dict, or GraphState
        if isinstance(input_data, str):
            user_message = input_data
        elif isinstance(input_data, dict):
            user_message = input_data.get("user_input")
        else:
            user_message = getattr(input_data, "user_input", None)

        mc = self.memory_context
        if context and isinstance(context, dict) and "memory_context" in context:
            mc = context["memory_context"]

        return detect_intent(str(user_message), mc)

    def after_run(self, output_data: IntentResult, context: Any = None) -> None:
        # Optional: handle memory/feedback updates (not implemented yet)
        pass