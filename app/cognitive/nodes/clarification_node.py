# app/cognitive/nodes/clarification_node.py


from app.cognitive.state.graph_state import GraphState

def clarification_node_test(state: GraphState) -> GraphState:
    """
    Ask the user to clarify missing parameters (e.g., frequency, start date).
    For demo: just use a static prompt or inspect state.recognized_intent.parameters.
    """
    missing = state.recognized_intent.get("parameters", {}).get("missing", ["some detail"])
    reason = state.recognized_intent.get("parameters", {}).get("reason", "needed for planning")

    state.response_text = (
        "⚠️ I need a bit more information before continuing.\n"
        f"Missing: {', '.join(missing)}\n"
        f"Reason: {reason}\n\n"
        "Can you please provide these details?"
    )
    return state
