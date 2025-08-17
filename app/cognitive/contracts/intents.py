# app/cognitive/contracts/intents.py
# Centralized intent registry for the cognitive AI system

SUPPORTED_INTENTS = [
    {"name": "create_new_plan", "description": "User wants to create a new plan for a goal or project."},
    {"name": "edit_existing_plan", "description": "User wants to make minor or specific changes to an existing plan (e.g., update a task, change a deadline, add/remove a step)."},
    {"name": "revise_plan", "description": "User wants to holistically rethink or restructure a plan, often in response to feedback, new circumstances, or falling behind. This is a major revision, not just a minor edit."},
    {"name": "adaptive_replan", "description": "User is behind schedule for a goal and wants the system to intelligently replan so the goal can still be achieved. This may require compressing, rescheduling, or reprioritizing tasks, and may trigger syncing of other plans to avoid conflicts."},
    {"name": "update_task", "description": "User wants to update details of a specific task."},
    {"name": "give_feedback", "description": "User provides feedback on a plan, task, or system behavior."},
    {"name": "ask_question", "description": "User asks a question about plans, tasks, or the system."},
    {"name": "pause_goal", "description": "User wants to pause progress on a goal."},
    {"name": "reschedule_task", "description": "User wants to change the scheduled time of a task."},
    {"name": "show_summary", "description": "User requests a summary of plans, goals, or progress."},
    {"name": "undo_last_action", "description": "User wants to undo the most recent change or action."},
    {"name": "add_constraint", "description": "User wants to add a constraint (e.g., time, resource) to a plan or task."},
    {"name": "remove_task", "description": "User wants to remove a task from a plan."},
    {"name": "update_goal", "description": "User wants to update the details or parameters of a goal."},
    {"name": "see_goal_performance", "description": "User wants to see his/her performance metrics for a specific goal."},
    {"name": "see_overall_performance", "description": "User wants to see his/her overall performance metrics across all goals."},
    {"name": "sync_all_plans_across_all_goals", "description": "User wants to synchronize all plans across all goals."},
    {"name": "reset_existing_plan", "description": "User wants to reset a plan to its initial state."},
    {"name": "ask_about_preferences", "description": "User asks about their own preferences or system's understanding of them."}
]
