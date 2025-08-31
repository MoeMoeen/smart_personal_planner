# app/flow/registry.py   # Node registry and lookup utilities
# NodeSpec registry (+ decorators/introspection)


# =============================
# app/flow/registry.py
# =============================
from __future__ import annotations
from typing import Dict

from app.flow.flow_compiler import NodeSpec  # reuse the dataclass

# NOTE: We point to node callables via `entrypoint_path` so they are imported lazily.
NODE_REGISTRY: Dict[str, NodeSpec] = {
    "plan_outline": NodeSpec(
        name="plan_outline",
        type="node",
        description="Create a high-level plan outline",
        outputs=["outline"],
        entrypoint_path="app.nodes.plan_outline:plan_outline",
    ),
    "user_confirm_a": NodeSpec(
        name="user_confirm_a",
        type="node",
        description="Ask user to confirm or revise the outline",
        inputs=["outline"],
        dependencies=["plan_outline"],
        entrypoint_path="app.nodes.user_confirmation:user_confirm_a",
    ),
    "task_generation": NodeSpec(
        name="task_generation",
        type="node",
        description="Expand outline into concrete tasks",
        inputs=["outline"],
        dependencies=["user_confirm_a"],
        entrypoint_path="app.nodes.task_generation:task_generation",
    ),
    # You can add the rest later: world_model_integration, calendarization, validation, etc.
}
