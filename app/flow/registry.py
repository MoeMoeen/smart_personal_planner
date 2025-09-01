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
    "world_model_integration": NodeSpec(
        name="world_model_integration",
        type="node",
        description="Enrich tasks with world model constraints (calendar, capacity, blackout)",
        inputs=["tasks"],
        outputs=["wm_enriched"],
        dependencies=["task_generation"],
        entrypoint_path="app.nodes.world_model_integration:world_model_integration",
    ),
    "calendarization": NodeSpec(
        name="calendarization",
        type="node",
        description="Assign time slots to tasks based on world constraints",
        inputs=["tasks", "wm_enriched"],
        outputs=["schedule"],
        dependencies=["world_model_integration"],
        entrypoint_path="app.nodes.calendarization:calendarization",
    ),
    "validation": NodeSpec(
        name="validation",
        type="node",
        description="Check schedule for overlaps/violations and fixable issues",
        inputs=["schedule"],
        outputs=["validation_ok", "violations"],
        dependencies=["calendarization"],
        entrypoint_path="app.nodes.validation:validation",
    ),
    "user_confirm_b": NodeSpec(
        name="user_confirm_b",
        type="node",
        description="Present final plan for approval (B).",
        inputs=["schedule", "violations"],
        dependencies=["validation"],
        entrypoint_path="app.nodes.user_confirmation:user_confirm_b",
    ),
    "persistence": NodeSpec(
        name="persistence",
        type="node",
        description="Persist plan to DB and external calendars",
        inputs=["schedule"],
        outputs=["persisted"],
        dependencies=["user_confirm_b"],
        entrypoint_path="app.nodes.persistence:persistence",
    ),
}

