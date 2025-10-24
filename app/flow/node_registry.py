# app/flow/node_registry.py   # Node registry and lookup utilities
# NodeSpec registry (+ decorators/introspection)


from __future__ import annotations
from typing import Dict

from app.flow.flow_compiler import NodeSpec  # reuse the dataclass

# NOTE: We point to node callables via `entrypoint_path` so they are imported lazily.
NODE_REGISTRY: Dict[str, NodeSpec] = {
    "planning_node": NodeSpec(
        name="planning_node",
        type="node",
        description="Agentic Planning Node: produce Outline → Roadmap → Schedule with internal approvals.",
        outputs=["plan_outline", "roadmap", "schedule"],
    entrypoint_path="app.cognitive.nodes.planning_node:planning_node",
    ),
    "user_confirm_a_node": NodeSpec(
        name="user_confirm_a_node",
        type="node",
        description="Ask user to confirm or revise the outline",
        inputs=["outline"],
        dependencies=["planning_node"],
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
    # Phase 5 POST_PLANNING_EDGES nodes
    "scheduling_escalation_node": NodeSpec(
        name="scheduling_escalation_node",
        type="node",
        description="Handle scheduling escalation with HITL/tooling support.",
        inputs=["escalate_reason"],
        outputs=["resolution"],
        entrypoint_path="app.cognitive.nodes.scheduling_escalation:scheduling_escalation",
    ),
    "summary_node": NodeSpec(
        name="summary_node",
        type="node", 
        description="Generate final summary and end graph execution.",
        inputs=["response_text"],
        outputs=["summary"],
        entrypoint_path="app.cognitive.nodes.summary:summary",
    ),
    # Fallback deterministic nodes
    "plan_outline_node_legacy": NodeSpec(
        name="plan_outline_node_legacy",
        type="node",
        description="Deterministic outline generation (fallback mode only).",
        inputs=["user_input", "goal_context"],
        outputs=["plan_outline"],
        entrypoint_path="app.cognitive.nodes.plan_outline_legacy:plan_outline_legacy",
    ),
    "sync_plans_node": NodeSpec(
        name="sync_plans_node",
        type="node",
        description="Synchronize all plans across all goals.",
        inputs=[],
        outputs=["sync_result"],
        entrypoint_path="app.cognitive.nodes.sync:sync_plans",
    ),
}

