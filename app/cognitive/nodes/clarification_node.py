# app/cognitive/nodes/clarification_node.py

def clarification_node(state):
    missing = state["recognized_intent"]["parameters"].get("missing", [])
    reason = state["recognized_intent"]["parameters"].get("reason", "")
    state["clarification_request"] = {
        "text": f"Please provide: {', '.join(missing)}",
        "reason": reason
    }
    return state
