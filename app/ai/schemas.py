# --- Pydantic is Python's data validation library used for schemas ---

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date, datetime, timezone

# ------------------------------------------
# ✅ 1. Task: The smallest unit of execution — one single task (under an occurrence)
# ------------------------------------------
class TaskPlan(BaseModel):
    title: str = Field(..., description="Title of the task")
    due_date: Optional[date] = Field(None, description="Due date of the task")
    estimated_time: Optional[int] = Field(None, ge=0, description="Estimated time in minutes")
    completed: bool = Field(False, description="Whether the task is marked completed")


# ---------------------------------------------------------
# ✅ 2. GoalOccurrence: One instance of the goal per cycle (e.g., 1 yoga session in May)
# ---------------------------------------------------------
class GoalOccurrencePlan(BaseModel):
    occurrence_order: int = Field(..., description="Order of the occurrence in the cycle (e.g., 1st, 2nd)")
    estimated_effort: Optional[int] = Field(None, description="Total effort for this occurrence in minutes")
    tasks: List[TaskPlan] = Field(..., description="List of tasks for this occurrence")


# ---------------------------------------------------------
# ✅ 3. HabitCycle: A single cycle (e.g. one week/month, May, June, etc.)
# ---------------------------------------------------------
class HabitCyclePlan(BaseModel):
    cycle_label: str = Field(..., description="Label like '2025-07' or 'Week 1'")
    start_date: date = Field(..., description="Start date of the cycle")
    end_date: date = Field(..., description="End date of the cycle")
    progress: int = Field(0, ge=0, le=100, description="Progress score (0-100%) for this cycle")
    occurrences: List[GoalOccurrencePlan] = Field(..., description="Occurrences within this cycle")


# ------------------------------------------
# ✅ 4. Goal: Top-level user-defined objective
# ------------------------------------------
class GoalPlan(BaseModel):
    title: str = Field(..., description="Title of the goal")
    description: Optional[str] = Field(None, description="Optional detailed description")
    start_date: date = Field(..., description="Start date of the goal")
    end_date: Optional[date] = Field(None, description="End date or deadline of the goal")
    progress: int = Field(0, ge=0, le=100, description="Overall progress score (0–100%)")
    goal_type: str = Field(..., description="Either 'habit' or 'project'")
    
    # Habit-specific logic
    recurrence_cycle: Optional[str] = Field(None, description="e.g., daily, weekly, monthly")
    goal_frequency_per_cycle: Optional[int] = Field(None, description="How many times per cycle the goal should be achieved")
    goal_recurrence_count: Optional[int] = Field(None, description="How many cycles should be planned (e.g. 6 months)")
    default_estimated_effort_per_occurrence: Optional[int] = Field(None, description="Optional default effort per goal instance")

    # Structure
    habit_cycles: Optional[List[HabitCyclePlan]] = Field(None, description="Defined only for habit goals")
    tasks: Optional[List[TaskPlan]] = Field(None, description="Defined only for project goals")


# ------------------------------------------------
# ✅ 5. Final generated plan wrapper (for parsing)
# ------------------------------------------------
class GeneratedPlan(BaseModel):
    goal: GoalPlan = Field(..., description="The main goal being planned")


# ------------------------------------------------
# We'll now update your prompt template to instruct the LLM to output two structured blocks:
# 1. A JSON plan
# 2. A code snippet (Python) for how to persist the plan to DB

# class GeneratedPlanWithCode(BaseModel):
#     goal: GoalPlan = Field(..., description="The main goal being planned")
#     code_snippet: str = Field(..., description="Python code snippet to save this plan to the database")
#     """
#     This schema includes both the structured goal plan and a code snippet for saving it.
#     The LLM should return a valid JSON object that matches this schema.
#     """


class PlanFeedbackRequest(BaseModel):
    plan_id: int = Field(..., description="ID of the generated plan to provide feedback on")
    feedback_text: str = Field(..., description="Feedback on the generated plan in natural language, e.g., 'too many tasks', 'missing details'")
    is_approved: Optional[bool] = Field(..., description="Whether the plan is approved by the user or needs changes")
    suggested_changes: Optional[str] = Field(None, description="Optional suggested changes to improve the plan")
    # Optional fields for tracking feedback source and timestamp
    user_id: Optional[int] = Field(None, description="Optional user ID for tracking feedback source")
    timestamp: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc), description="Optional timestamp of when the feedback was given")
    
class PlanRefinementRequest(BaseModel):
    plan_id: int = Field(..., description="ID of the generated plan to refine")
    custom_feedback: Optional[str] = Field(..., description="Custom feedback on how to improve the plan, e.g., 'Add more tasks', 'Change frequency'")
    user_id: Optional[int] = Field(None, description="Optional user ID for tracking refinement source")
    timestamp: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc), description="Optional timestamp of when the refinement was requested")

