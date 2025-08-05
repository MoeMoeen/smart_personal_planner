# app/ai/schemas.py
# --- Pydantic is Python's data validation library used for schemas ---

from pydantic import BaseModel, Field, model_validator
from typing import List, Optional
from datetime import date, datetime, timezone
from app.models import PlanFeedbackAction  # Import the enum from models.py

from enum import Enum

class GoalTypeEnum(str, Enum):
    habit = "habit"
    project = "project"
    hybrid = "hybrid"


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
# ✅ 4. Goal: Lightweight metadata container (title & description only)
# ------------------------------------------
class GoalPlan(BaseModel):
    title: str = Field(..., description="Title of the goal")
    description: str = Field(..., description="Detailed description")
    user_id: Optional[int] = Field(None, description="Optional user ID for tracking ownership")


# ------------------------------------------
# ✅ 5. Plan: Central orchestrator containing all execution logic
# ------------------------------------------
class PlanStructure(BaseModel):
    goal_type: GoalTypeEnum = Field(..., description="Type of goal: habit, project, or hybrid")
    start_date: date = Field(..., description="Start date of the plan")
    end_date: Optional[date] = Field(None, description="End date or deadline of the plan")
    progress: int = Field(0, ge=0, le=100, description="Overall progress score (0–100%)")
    
    # Habit-specific fields
    recurrence_cycle: Optional[str] = Field(None, description="e.g., daily, weekly, monthly (for habit-based components)")
    goal_frequency_per_cycle: Optional[int] = Field(None, description="How many times per cycle the goal should be achieved (for habit-based components)")
    goal_recurrence_count: Optional[int] = Field(None, description="How many cycles should be planned, e.g. 6 months (for habit-based components)")
    default_estimated_time_per_cycle: Optional[int] = Field(None, description="Optional default effort per goal instance (for habit-based components)")
    
    # Plan structure - can have both for hybrid plans
    habit_cycles: Optional[List[HabitCyclePlan]] = Field(None, description="Habit-based cycles (for habit or hybrid plans)")
    tasks: Optional[List[TaskPlan]] = Field(None, description="Project-based tasks (for project or hybrid plans)")
    
    @property
    def is_hybrid(self) -> bool:
        """Check if this plan has both habit cycles and tasks"""
        return bool(self.habit_cycles) and bool(self.tasks)
    
    @property
    def plan_type_actual(self) -> str:
        """Get the actual plan type based on content"""
        has_habits = bool(self.habit_cycles)
        has_tasks = bool(self.tasks)
        
        if has_habits and has_tasks:
            return "hybrid"
        elif has_habits:
            return "habit"
        elif has_tasks:
            return "project"
        else:
            return "empty"
    
    @model_validator(mode='after')
    def validate_structure(self):
        """Validate that at least one structure type is provided"""
        has_habits = bool(self.habit_cycles)
        has_tasks = bool(self.tasks)
        
        if not has_habits and not has_tasks:
            raise ValueError("Plan must have either habit_cycles, tasks, or both")
        
        return self
    
    # AI metadata
    ai_model_used: Optional[str] = Field(None, description="AI model used to generate this plan")
    ai_prompt_version: Optional[str] = Field(None, description="Version of the prompt used")
    generated_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc), description="When the plan was generated")
    
    # Refinement tracking
    refinement_round: Optional[int] = Field(0, description="Round of refinement (0 for original)")
    source_plan_id: Optional[int] = Field(None, description="ID of the plan this is refined from")


# ------------------------------------------------
# ✅ 6. Final generated plan wrapper (for parsing)
# ------------------------------------------------
class GeneratedPlan(BaseModel):
    goal: GoalPlan = Field(..., description="The goal being planned (title & description only)")
    plan: PlanStructure = Field(..., description="The execution plan with all implementation details")
    plan_id: Optional[int] = Field(None, description="Optional ID of the generated plan")
    user_id: Optional[int] = Field(None, description="ID of the user who owns this plan")
    
# ------------------------------------------------
# ✅ 7. Plan feedback request schema. This is used to submit feedback on a generated plan.
# ------------------------------------------------

class PlanFeedbackRequest(BaseModel):
    plan_id: int = Field(..., description="ID of the generated plan to provide feedback on")
    goal_id: int = Field(..., description="ID of the goal associated with this plan")
    feedback_text: str = Field(..., description="Feedback on the generated plan in natural language, e.g., 'too many tasks', 'missing details'")
    plan_feedback_action: PlanFeedbackAction = Field(..., description="Action to take on the plan feedback, e.g., approve or request refinement")
    suggested_changes: Optional[str] = Field(None, description="Optional suggested changes to improve the plan")
    # Optional fields for tracking feedback source and timestamp
    user_id: int = Field(..., description="User ID for tracking feedback source")
    timestamp: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc), description="Optional timestamp of when the feedback was given")

class PlanFeedbackResponse(BaseModel):
    message: str
    feedback: str
    plan_id: int
    plan_feedback_action: PlanFeedbackAction
    refined_plan_id: Optional[int] = None
    refined_plan: Optional[GeneratedPlan] = None
    goal_id: Optional[int] = None

# ------------------------------------------------

# ✅ Input schema for the user’s natural language goal
class GoalDescriptionRequest(BaseModel):
    goal_description: str = Field(..., description="User's natural language description of the goal")
    user_id: int = Field(..., description="ID of the user who owns this goal")  

# ✅ Output schema: the full structured plan
class AIPlanResponse(BaseModel):
    plan: GeneratedPlan = Field(..., description="AI-generated structured plan")
    source: str = Field(default="AI", description="Source of the generated plan")   
    ai_version: str = Field(default="1.0", description="Version of the AI model used")
    user_id: int = Field(..., description="ID of the user who owns this plan")

# ✅ Output schema for plan with code snippet
# 👇 This is what we expose as FastAPI response

class GeneratedPlanWithCode(BaseModel):
    plan: GeneratedPlan = Field(..., description="AI-generated structured plan")
    code_block: str = Field(..., description="Python code snippet to save this plan to the database")

class AIPlanWithCodeResponse(GeneratedPlanWithCode):
    source: str = Field(default="AI", description="Source of the generated plan")   
    ai_version: str = Field(default="1.0", description="Version of the AI model used")

# ------------------------------------------------
# class PlanRefinementRequest(BaseModel):
#     plan_id: int = Field(..., description="ID of the generated plan to refine")
#     custom_feedback: Optional[str] = Field(..., description="Custom feedback on how to improve the plan, e.g., 'Add more tasks', 'Change frequency'")
#     user_id: Optional[int] = Field(None, description="Optional user ID for tracking refinement source")
#     timestamp: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc), description="Optional timestamp of when the refinement was requested")

