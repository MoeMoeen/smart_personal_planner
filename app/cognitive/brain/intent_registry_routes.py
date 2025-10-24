# app/cognitive/brain/intent_registry_routes.py
# canonical intents, synonyms, examples, default routes (knowledge)

# Centralized intent registry and default routes per each intent for the cognitive AI system

from __future__ import annotations

# app/cognitive/brain/intent_registry_routes.py

from __future__ import annotations
from typing import Dict, List


# --------------------------------------------------------------------
# Canonical User-Facing Intents
# --------------------------------------------------------------------
SUPPORTED_INTENTS: List[Dict[str, str]] = [
    {"name": "create_new_plan", "description": "User wants to create a new plan for a goal or project."},
    {"name": "edit_existing_plan", "description": "User wants to make minor or specific changes to an existing plan (e.g., update a task, change a deadline, add/remove a step)."},
    {"name": "revise_plan", "description": "User wants to holistically rethink or restructure a plan."},
    {"name": "adaptive_replan", "description": "User is behind schedule and wants to intelligently replan."},
    {"name": "update_task", "description": "User wants to update details of a specific task."},
    {"name": "give_feedback", "description": "User provides feedback on a plan, task, or system behavior."},
    {"name": "pause_goal", "description": "User wants to pause progress on a goal."},
    {"name": "reschedule_task", "description": "User wants to change the scheduled time of a task."},
    {"name": "show_summary", "description": "User requests a summary of plans, goals, or progress."},
    {"name": "undo_last_action", "description": "User wants to undo the most recent change or action."},
    {"name": "add_constraint", "description": "User wants to add a constraint (e.g., time, resource) to a plan or task."},
    {"name": "remove_task", "description": "User wants to remove a task from a plan."},
    {"name": "update_goal", "description": "User wants to update the details or parameters of a goal."},
    {"name": "see_goal_performance", "description": "User wants to see performance metrics for a specific goal."},
    {"name": "see_overall_performance", "description": "User wants to see overall performance metrics across all goals."},
    {"name": "sync_all_plans_across_all_goals", "description": "User wants to synchronize all plans across all goals."},
    {"name": "reset_existing_plan", "description": "User wants to reset a plan to its initial state."},
    {"name": "ask_about_preferences", "description": "User asks about their own preferences or system's understanding of them."},
]


# --------------------------------------------------------------------
# System / Control Intents (meta-intents not directly asked by user)
# --------------------------------------------------------------------
SYSTEM_INTENTS: List[Dict[str, str]] = [
    {"name": "clarify", "description": "System needs to ask the user for missing required information before continuing."},
    {"name": "ask_question", "description": "System interprets ambiguous or unrelated input as a general question."},
]


# --------------------------------------------------------------------
# All Intents (for convenience if needed)
# --------------------------------------------------------------------
ALL_INTENTS: List[Dict[str, str]] = SUPPORTED_INTENTS + SYSTEM_INTENTS


# --------------------------------------------------------------------
# Fallback deterministic flows (sequences of nodes) for when LLM planning is unavailable or fails.
# --------------------------------------------------------------------

DEFAULT_FLOW_REGISTRY = {
    # --- Plan lifecycle ---
    "create_new_plan": [
        "planning_node",
        "user_confirm_a_node",
        "task_generation_node",
        "world_model_integration_node",
        "calendarization_node",
        "validation_node",
        "user_confirm_b_node",
        "persistence_node",
    ],
    "edit_existing_plan": [
        "update_task_node",       # direct edit to existing task/plan
        "validation_node",
        "user_confirm_b_node",
        "persistence_node",
    ],
    "revise_plan": [
        "planning_node",           # re-generate outline
        "user_confirm_a_node",
        "task_generation_node",        # rebuild tasks
        "world_model_integration_node",
        "calendarization_node",
        "validation_node",
        "user_confirm_b_node",
        "persistence_node",
    ],
    "adaptive_replan": [
        "planning_node",           # re-outline under new constraints
        "task_generation_node",
        "world_model_integration_node",
        "calendarization_node",
        "validation_node",
        "user_confirm_b_node",
        "persistence_node",
    ],
    "reset_existing_plan": [
        "plan_reset_node",        # wipe/rebuild baseline
        "planning_node",
        "user_confirm_a_node",
        "task_generation_node",
        "calendarization_node",
        "validation_node",
        "user_confirm_b_node",
        "persistence_node",
    ],

    # --- Task-level operations ---
    "update_task": [
        "update_task_node",
        "validation_node",
        "user_confirm_b_node",
        "persistence_node",
    ],
    "reschedule_task": [
        "reschedule_task_node",
        "validation_node",
        "user_confirm_b_node",
        "persistence_node",
    ],
    "remove_task": [
        "remove_task_node",
        "validation_node",
        "user_confirm_b_node",
        "persistence_node",
    ],

    # --- Goal-level operations ---
    "update_goal": [
        "goal_update_node",
        "planning_node",
        "user_confirm_a_node",
        "task_generation_node",
        "calendarization_node",
        "validation_node",
        "user_confirm_b_node",
        "persistence_node",
    ],
    "pause_goal": [
        "pause_goal_node",
        "persistence_node",
    ],

    # --- Meta/system operations ---
    "give_feedback": [
        "feedback_logger_node",
        "acknowledge_node",
    ],
    "undo_last_action": [
        "undo_node",
        "validation_node",
        "user_confirm_b_node",
        "persistence_node",
    ],
    "add_constraint": [
        "constraint_node",
        "planning_node",          # constraint may require re-outline
        "task_generation_node",
        "validation_node",
        "user_confirm_b_node",
        "persistence_node",
    ],
    "sync_all_plans_across_all_goals": [
        "sync_node",
        "validation_node",
        "user_confirm_b_node",
        "persistence_node",
    ],

    # --- Information requests ---
    "show_summary": ["summary_node"],
    "see_goal_performance": ["performance_node"],
    "see_overall_performance": ["performance_node"],
    "ask_question": ["conversation_node"],
    "ask_about_preferences": ["preference_node"],
    "clarify": ["clarification_node"],
}


def map_intent_to_node(intent: str) -> str:
    """
    Map high-level intent names to graph node names.
    In real system, you could load from config or registry.
    Mapping format is <intent_name>: <node_name>
    """
    mapping = {
        "confirm_outline": "task_generation_node",
        "revise_outline": "planning_node",
        "ask_question": "conversation_node",  # if you have a small-talk node
        "adaptive_replan": "planning_node",
        "create_new_plan": "planning_node",
    }
    return mapping.get(intent, "planning_node")
