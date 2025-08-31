# app/cognitive/langgraph_flow/tools.py


import logging
from langchain_core.tools import tool
from app.cognitive.brain.intent_recognition.intent_recognition_node import intent_recognition_node
from app.cognitive.contracts.types import MemoryContext
from app.cognitive.contracts.results import IntentResult

logger = logging.getLogger(__name__)

@tool
def detect_intent(user_input: str, memory_context: MemoryContext) -> IntentResult:
    """
    Detect the user's intent and extract any relevant parameters.
    Handles errors and validates output type.
    """
    try:
        result = intent_recognition_node(user_input, memory_context)
        if not isinstance(result, IntentResult):
            logger.error(f"detect_intent: Output is not of type IntentResult: {type(result)}")
            raise TypeError("Output is not of type IntentResult")
        return result
    except Exception as e:
        logger.exception(f"Error in detect_intent: {e}")
        # Optionally, return a default IntentResult or re-raise
        raise
