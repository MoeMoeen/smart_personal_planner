# app/flow/node_registry.py   # Node registry and lookup utilities
# NodeSpec registry (+ decorators/introspection)


from __future__ import annotations
from typing import Dict

from app.flow.flow_compiler import NodeSpec  # reuse the dataclass

# NOTE: We point to node callables via `entrypoint_path` so they are imported lazily.
NODE_REGISTRY: Dict[str, NodeSpec] = {
    "plan_outline_node": NodeSpec(
        name="plan_outline_node",
        type="node",
        description="Create a high-level plan outline",
        outputs=["outline"],
        entrypoint_path="app.cognitive.nodes.plan_outline:plan_outline",
    ),
    "user_confirm_a_node": NodeSpec(
        name="user_confirm_a_node",
        type="node",
        description="Ask user to confirm or revise the outline",
        inputs=["outline"],
        dependencies=["plan_outline_node"],
        entrypoint_path="app.cognitive.nodes.user_confirmation:user_confirm_a",
    ),
    "task_generation_node": NodeSpec(
        name="task_generation_node",
        type="node",
        description="Expand outline into concrete tasks",
        inputs=["outline"],
        dependencies=["user_confirm_a_node"],
        entrypoint_path="app.cognitive.nodes.task_generation:task_generation",
    ),
    "world_model_integration_node": NodeSpec(
        name="world_model_integration_node",
        type="node",
        description="Enrich tasks with world model constraints (calendar, capacity, blackout)",
        inputs=["tasks"],
        outputs=["wm_enriched"],
        dependencies=["task_generation_node"],
        entrypoint_path="app.cognitive.nodes.world_model_integration:world_model_integration",
    ),
    "calendarization_node": NodeSpec(
        name="calendarization_node",
        type="node",
        description="Assign time slots to tasks based on world constraints",
        inputs=["tasks", "wm_enriched"],
        outputs=["schedule"],
        dependencies=["world_model_integration_node"],
        entrypoint_path="app.cognitive.nodes.calendarization:calendarization",
    ),
    "validation_node": NodeSpec(
        name="validation_node",
        type="node",
        description="Check schedule for overlaps/violations and fixable issues",
        inputs=["schedule"],
        outputs=["validation_ok", "violations"],
        dependencies=["calendarization_node"],
        entrypoint_path="app.cognitive.nodes.validation:validation",
    ),
    "user_confirm_b_node": NodeSpec(
        name="user_confirm_b_node",
        type="node",
        description="Present final plan for approval (B).",
        inputs=["schedule", "violations"],
        dependencies=["validation_node"],
        entrypoint_path="app.cognitive.nodes.user_confirmation:user_confirm_b",
    ),
    "persistence_node": NodeSpec(
        name="persistence_node",
        type="node",
        description="Persist plan to DB and external calendars",
        inputs=["schedule"],
        outputs=["persisted"],
        dependencies=["user_confirm_b_node"],
        entrypoint_path="app.cognitive.nodes.persistence:persistence",
    ),
    "clarification_node": NodeSpec(
        name="clarification_node",
        type="node",
        description="Clarify user intent or gather more information.",
        inputs=["user_input"],
        outputs=["clarified_intent"],
        entrypoint_path="app.cognitive.nodes.clarification:clarification",
    ),
}

