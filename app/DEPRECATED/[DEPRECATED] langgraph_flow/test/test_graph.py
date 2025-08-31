# app/cognitive/langgraph_flow/graph.py

"""
LangGraph node system scaffold for modular, LLM-driven cognitive AI.
This is a clean, modern implementation (legacy agent/graph/tools are not used).
"""

from typing import Any, Dict
from langgraph.graph import StateGraph, END
from app.cognitive.brain.intent_recognition.intent_recognition_node import IntentRecognitionNode
from app.cognitive.contracts.results import IntentResult


# --- LangGraph workflow setup ---
def build_cognitive_graph(memory_context):
    """
    Build a LangGraph workflow with intent recognition as the entry point.
    Returns a LangGraph workflow ready for execution.
    """
    # 1. Define the state schema (can be extended for more nodes/branches)
    class CognitiveState(dict):
        """State object passed between nodes. Extend as needed."""
        pass

    # 2. Define the intent recognition node as a LangGraph node
    def intent_recognition_node(state: CognitiveState) -> CognitiveState:
        user_input = state.get("user_input")
        if user_input is None:
            user_input = ""
        node = IntentRecognitionNode(memory_context=memory_context)
        result: IntentResult = node.run(user_input)
        state["intent_result"] = result
        return state

    # 3. Build the LangGraph workflow
    workflow = StateGraph(CognitiveState)
    workflow.add_node("intent_recognition", intent_recognition_node)
    # For now, end after intent recognition; add more nodes/branches as needed
    workflow.set_entry_point("intent_recognition")
    workflow.add_edge("intent_recognition", END)
    return workflow.compile()

# Usage example (for test/demo):
# from app.cognitive.contracts.types import MemoryContext
# memory_context = MemoryContext(...)
# workflow = build_cognitive_graph(memory_context)
# result = workflow.invoke({"user_input": "I want to create a new plan for my fitness goal."})
# print(result["intent_result"])

# Usage example (for test/demo):
# from app.cognitive.contracts.types import MemoryContext
# memory_context = MemoryContext(...)
# graph = build_cognitive_graph(memory_context)
# result = graph.run(user_input, context={})
