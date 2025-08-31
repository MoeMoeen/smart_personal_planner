# app/flow/intent_routes.py
# # fallback deterministic map: intent -> [nodes]


# =============================
# app/flow/intent_routes.py
# =============================
from __future__ import annotations

# Fallback deterministic flows for when LLM planning is unavailable or fails.
DEFAULT_FLOW_REGISTRY = {
    "create_new_plan": [
        "plan_outline",
        "user_confirm_a",
        "task_generation",
        "world_model_integration",
        "calendarization",
        "validation",
        "user_confirm_b",
        "persistence",
    ],
    # Add more intents as needed
    "ask_question": ["plan_outline", "user_confirm_a"],  # sample shorter flow
}


