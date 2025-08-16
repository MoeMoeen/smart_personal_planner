"""
Intent Recognition Node
- Analyzes each user input to determine intent (e.g., create plan, update task, feedback, etc.)
- Routes to the appropriate workflow/chain of nodes
- Enables non-linear, conversational, context-aware interaction
"""
from app.cognitive.contracts.types import MemoryContext
from typing import Dict, Any


# Intent schema and supported intents with explanations
INTENT_SCHEMA = {
    "intent": "str, one of the supported intents below",
    "parameters": "dict, extracted entities or context relevant to the intent"
}

# Supported intents and explanations:
SUPPORTED_INTENTS = [
    # "create_new_plan": User wants to create a new plan for a goal or project
    "create_new_plan",
    # "edit_existing_plan": User wants to modify an existing plan
    "edit_existing_plan",
    # "update_task": User wants to update details of a specific task
    "update_task",
    # "give_feedback": User provides feedback on a plan, task, or system behavior
    "give_feedback",
    # "ask_question": User asks a question about plans, tasks, or the system
    "ask_question",
    # "pause_goal": User wants to pause progress on a goal
    "pause_goal",
    # "reschedule_task": User wants to change the scheduled time of a task
    "reschedule_task",
    # "show_summary": User requests a summary of plans, goals, or progress
    "show_summary",
    # "undo_last_action": User wants to undo the most recent change or action
    "undo_last_action",
    # "revise_plan": User wants to revise or refine an existing plan
    "revise_plan",
    # "add_constraint": User wants to add a constraint (e.g., time, resource) to a plan or task
    "add_constraint",
    # "remove_task": User wants to remove a task from a plan
    "remove_task",
    # "update_goal": User wants to update the details or parameters of a goal
    "update_goal",
    # "see_goal_performance": User wants to see performance metrics for a specific goal
    "see_goal_performance",
    # "see_overall_performance": User wants to see overall system or user performance metrics
    "see_overall_performance",
    # "sync_all_plans_across_all_goals": User wants to synchronize all plans across all goals
    "sync_all_plans_across_all_goals",
    # "reset_existing_plan": User wants to reset a plan to its initial state
    "reset_existing_plan",
    # "ask_about_preferences": User asks about their own preferences or system's understanding of them
    "ask_about_preferences"
]

def intent_recognition_node(user_input: str, memory_context: MemoryContext) -> Dict[str, Any]:
    """
    LLM-based intent recognition node.
    Args:
        user_input: Raw user message
        memory_context: Injected memory context
    Returns:
        dict: {"intent": str, "parameters": dict, ...}
    """
    # TODO: Implement LLM-based intent recognition using OpenAI as default, with local LLM stub as backup
    # 1. Construct prompt with SUPPORTED_INTENTS and explanations
    # 2. Call LLM and parse response
    # 3. If LLM fails, log and optionally use minimal rule-based fallback
    raise NotImplementedError("LLM-based intent recognition node not implemented yet.")
