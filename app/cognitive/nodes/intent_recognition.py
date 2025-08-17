# app/cognitive/nodes/intent_recognition.py
"""
TODO: Self-Learning Intent Discovery Pipeline (Design Note):
-----------------------------------------------------
When the LLM cannot confidently map user input to a known intent (e.g., returns "ask_question" or ambiguous intent),
the system logs the input, LLM output, and context into semantic memory for later analysis. Periodically, these logs
are mined for new intent patterns using clustering, LLM-based summarization, or human review. New intent candidates
are proposed, validated (optionally via dialogue with the user), and integrated into the supported intents and LLM prompt.
This enables the system to dynamically expand its intent vocabulary and become more adaptive over time.
"""

import json
import logging
from app.cognitive.contracts.types import MemoryContext
from app.cognitive.utils.prompt_utils import build_intent_prompt
from typing import Any
from app.cognitive.contracts.results import IntentResult
from app.cognitive.utils.llm_utils import llm_retry_and_log
from app.cognitive.utils.llm_backend import get_llm_backend, LLMResponse
from app.cognitive.memory.semantic import create_semantic_memory

# Intent Recognition Node
# - Analyzes each user input to determine intent (e.g., create plan, update task, feedback, etc.)
# - Routes to the appropriate workflow/chain of nodes
# - Enables non-linear, conversational, context-aware interaction



# --- Class-based node for graph integration ---
from app.cognitive.langgraph_flow.base import BaseNode

class IntentRecognitionNode(BaseNode[IntentResult]):
    """LLM-based intent recognition node for CognitiveGraph."""
    def __init__(self, memory_context):
        super().__init__(name="intent_recognition")
        self.memory_context = memory_context

    def run(self, input_data: str, context: Any = None) -> IntentResult:
        """
        Args:
            input_data: user input (str)
            context: dict, should contain 'memory_context' if available
        Returns:
            IntentResult
        """
        mc = self.memory_context
        if context and "memory_context" in context:
            mc = context["memory_context"]
        return intent_recognition_node(str(input_data), mc)

    def after_run(self, output_data: IntentResult, context: Any = None) -> None:
        """
        TODO: Optional lifecycle hook for memory updates, feedback, etc. after node execution.
        """
        # No-op for now; implement memory/feedback updates here in future
        pass



# Intent schema and supported intents with explanations
INTENT_SCHEMA = {
    "intent": "str, one of the supported intents below",
    "parameters": "dict, extracted entities or context relevant to the intent"
}


@llm_retry_and_log(max_retries=3, delay=1.0, logger_name="llm_call")
def _call_openai_llm(user_input: str, memory_context: MemoryContext) -> LLMResponse:
    # Compose the full prompt using the prompt_utils helper
    full_prompt = build_intent_prompt(user_input, memory_context)
    backend = get_llm_backend()
    response = backend.call(full_prompt)
    if response and response.content:
        return response
    else:
        # Return a default fallback if the LLM response is malformed
        return LLMResponse(content=json.dumps({"intent": "ask_question", "parameters": {"message": user_input}}))

def _call_local_llm_stub(prompt: str, user_input: str, memory_context: MemoryContext) -> str:
    # TODO: Stub for local LLM fallback
    return json.dumps({"intent": "ask_question", "parameters": {"message": user_input}})

def intent_recognition_node(user_input: str, memory_context: MemoryContext) -> IntentResult:
    """
    LLM-based intent recognition node.
    Args:
        user_input: Raw user message
        memory_context: Injected memory context
    Returns:
        IntentResult
    """
    logger = logging.getLogger("intent_recognition_node")
    try:
        llm_response = _call_openai_llm(user_input, memory_context)
        # Try to parse the LLM's response as JSON
        result = json.loads(llm_response.content)
        if "intent" not in result:
            raise ValueError("No 'intent' in LLM response")
        # If intent is unknown, log for self-learning
        if result["intent"] == "ask_question":
            _log_unknown_intent(user_input, memory_context, llm_response.content)
            # Store unknown/ambiguous intent in semantic memory for self-learning
            try:
                user_id = getattr(memory_context, "user_id", None)
                if user_id is not None:
                    semantic = create_semantic_memory(user_id)
                    semantic.log_operation(
                        operation_type="unknown_intent",
                        details={
                            "user_input": user_input,
                            "memory_context": memory_context.__dict__ if hasattr(memory_context, "__dict__") else str(memory_context),
                            "llm_output": llm_response.content,
                        }
                    )
            except Exception as e:
                logger = logging.getLogger("intent_recognition_node.unknown_intent")
                logger.warning(f"Failed to store unknown intent in semantic memory: {e}")
            # Also log for ops visibility
            logger = logging.getLogger("intent_recognition_node.unknown_intent")
            logger.warning({
                "event": "unknown_intent",
                "user_input": user_input,
                "memory_context": memory_context.__dict__ if hasattr(memory_context, "__dict__") else str(memory_context),
                "llm_output": llm_response.content,
                "timestamp": __import__('datetime').datetime.now().isoformat()
            })
        confidence = result.get("confidence", 1.0)
        llm_raw_response = llm_response.content if isinstance(llm_response.content, str) else json.dumps(llm_response.content)
        # Include token/cost info in output and logs
        logger.info({
            "event": "llm_call_result",
            "intent": result["intent"],
            "parameters": result.get("parameters", {}),
            "confidence": confidence,
            "token_usage": llm_response.token_usage,
            "llm_cost": llm_response.cost
        })
        return IntentResult(
            intent=result["intent"],
            parameters=result.get("parameters", {}),
            confidence=confidence,
            llm_raw_response=llm_raw_response,
            token_usage=llm_response.token_usage,
            llm_cost=llm_response.cost
        )
    except Exception as e:
        logger.warning(f"OpenAI LLM failed or returned invalid response: {e}. Falling back to local LLM stub.")
        # Fallback: local LLM stub
        try:
            fallback_prompt = build_intent_prompt(user_input, memory_context)
            fallback_response = _call_local_llm_stub(fallback_prompt, user_input, memory_context)
            # Always log unknown intent in fallback
            _log_unknown_intent(user_input, memory_context, fallback_response)
            fallback_result = json.loads(fallback_response)
            confidence = fallback_result.get("confidence", 0.5)
            llm_raw_response = fallback_response if isinstance(fallback_response, str) else json.dumps(fallback_response)
            logger.info({
                "event": "llm_call_result_fallback",
                "intent": fallback_result.get("intent", "ask_question"),
                "parameters": fallback_result.get("parameters", {}),
                "confidence": confidence,
                "token_usage": None,
                "llm_cost": None
            })
            return IntentResult(
                intent=fallback_result.get("intent", "ask_question"),
                parameters=fallback_result.get("parameters", {}),
                confidence=confidence,
                llm_raw_response=llm_raw_response,
                token_usage=None,
                llm_cost=None
            )
        except Exception as e2:
            logger.error(f"Local LLM stub also failed: {e2}")
            _log_unknown_intent(user_input, memory_context, str(e2))
            logger.info({
                "event": "llm_call_result_fallback_error",
                "intent": "ask_question",
                "parameters": {"message": user_input},
                "confidence": 0.0,
                "token_usage": None,
                "llm_cost": None
            })
            return IntentResult(
                intent="ask_question",
                parameters={"message": user_input},
                confidence=0.0,
                llm_raw_response=str(e2),
                token_usage=None,
                llm_cost=None
            )

# --- Unknown intent logging for self-learning ---
def _log_unknown_intent(user_input, memory_context, llm_output):
    logger = logging.getLogger("intent_recognition_node.unknown_intent")
    logger.warning({
        "event": "unknown_intent",
        "user_input": user_input,
        "memory_context": memory_context.__dict__ if hasattr(memory_context, "__dict__") else str(memory_context),
        "llm_output": llm_output,
        "timestamp": __import__('datetime').datetime.now().isoformat()
    })
