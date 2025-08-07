# app/schemas.py

from pydantic import BaseModel, Field
from typing import Optional
from datetime import date
from enum import Enum

# === ENUMS ===
class GoalType(str, Enum):
    project = "project"
    habit = "habit"
    hybrid = "hybrid"

# === FEEDBACK SCHEMAS (Actually Used in Planning Router) ===
class FeedbackCreate(BaseModel):
    plan_id: int = Field(..., description="ID of the plan this feedback is associated with")
    goal_id: int = Field(..., description="ID of the goal this feedback is associated with")
    user_id: int = Field(..., description="ID of the user who provided this feedback")
    feedback_text: str = Field(..., description="Content of the feedback")
    suggested_changes: Optional[str] = Field(None, description="Suggested changes")
    created_at: Optional[date] = Field(None, description="Date when the feedback was created, defaults to today")

class FeedbackRead(BaseModel):
    id: int = Field(..., description="Unique identifier of the feedback")
    plan_id: int = Field(..., description="ID of the plan this feedback is associated with")
    goal_id: int = Field(..., description="ID of the goal this feedback is associated with")
    user_id: int = Field(..., description="ID of the user who provided this feedback")
    feedback_text: str = Field(..., description="Content of the feedback")
    suggested_changes: Optional[str] = Field(None, description="Suggested changes")
    created_at: date = Field(..., description="Date when the feedback was created")

    class Config:
        from_attributes = True  # Updated from orm_mode for Pydantic V2

# === PLAN SCHEMAS (Used in Agent Tools) ===
class PlanRead(BaseModel):
    """Minimal Plan schema for API responses - used by agent tools"""
    id: int = Field(..., description="Unique identifier of the plan")
    goal_id: int = Field(..., description="ID of the goal this plan belongs to")
    user_id: int = Field(..., description="ID of the user who owns this plan")
    is_approved: bool = Field(False, description="Whether plan is approved")
    refinement_round: int = Field(0, description="Refinement iteration number")
    
    class Config:
        from_attributes = True

# === DEPRECATED LEGACY SCHEMAS ===
# These are kept for backward compatibility but marked as deprecated
# Remove these once all clients migrate to AI-based planning

class GoalBase(BaseModel):
    """DEPRECATED - Use AI planning pipeline instead"""
    title: str = Field(..., description="Title of the goal")
    description: Optional[str] = Field(None, description="Description of the goal")

class GoalCreate(GoalBase):
    """DEPRECATED - Use AI planning pipeline instead"""
    user_id: int = Field(..., description="ID of the user who owns this goal")

class GoalUpdate(BaseModel):
    """DEPRECATED - Use AI planning pipeline instead"""
    title: Optional[str] = Field(None, description="Update the title of the goal")
    description: Optional[str] = Field(None, description="Update the description of the goal")

class GoalRead(GoalBase):
    """DEPRECATED - Use AI planning pipeline instead"""
    id: int = Field(..., description="Unique identifier of the goal")
    user_id: int = Field(..., description="ID of the user who owns this goal")

    class Config:
        from_attributes = True

class ProjectGoalCreate(GoalCreate):
    """DEPRECATED - Use AI planning pipeline instead"""
    goal_type: GoalType = GoalType.project
    end_date: date = Field(..., description="End date of the project")

class HabitGoalCreate(GoalCreate):
    """DEPRECATED - Use AI planning pipeline instead"""
    goal_type: GoalType = GoalType.habit
    goal_recurrence_count: Optional[int] = Field(None, ge=1, description="Number of cycles")
    goal_frequency_per_cycle: int = Field(..., ge=1, description="Frequency per cycle")
    recurrence_cycle: str = Field(..., description="Recurrence cycle type")
    default_estimated_time_per_cycle: Optional[int] = Field(1, ge=1, description="Default time per cycle")

class HabitGoalUpdate(GoalUpdate):
    """DEPRECATED - Use AI planning pipeline instead"""
    goal_recurrence_count: Optional[int] = Field(None, description="Update recurrence count")
    goal_frequency_per_cycle: Optional[int] = Field(None, gt=0, description="Update frequency per cycle")
    recurrence_cycle: Optional[str] = Field(None, description="Update cycle type")
    default_estimated_time_per_cycle: Optional[int] = Field(None, description="Update time per cycle")

class ProjectGoalUpdate(GoalUpdate):
    """DEPRECATED - Use AI planning pipeline instead"""
    end_date: Optional[date] = Field(None, description="Update end date")
    progress: Optional[int] = Field(None, ge=0, le=100, description="Update progress")

# === OCCURRENCE SCHEMAS (Used in Occurrences Router) ===
class GoalOccurrenceUpdate(BaseModel):
    occurrence_order: Optional[int] = Field(None, description="Order of this occurrence in the cycle")
    estimated_effort: Optional[int] = Field(None, description="Estimated total hours for this goal occurrence")
    completed: Optional[bool] = Field(None, description="Whether this goal occurrence has been completed")
    user_id: Optional[int] = Field(None, description="ID of the user who owns this occurrence")

class GoalOccurrenceRead(BaseModel):
    id: int = Field(..., description="Unique ID of the goal occurrence within a cycle")
    cycle_id: int = Field(..., description="ID of the parent habit cycle")
    occurrence_order: int = Field(..., description="Order of this occurrence in the cycle")
    estimated_effort: Optional[int] = Field(None, description="Estimated total hours for this goal occurrence")
    completed: bool = Field(False, description="Whether this goal occurrence has been completed")
    user_id: int = Field(..., description="ID of the user who owns this occurrence")

    class Config:
        from_attributes = True

class GoalOccurrenceCreate(BaseModel):
    cycle_id: int = Field(..., description="ID of the parent habit cycle")
    occurrence_order: int = Field(..., description="Order of this occurrence in the cycle")
    estimated_effort: Optional[int] = Field(None, description="Estimated total hours for this goal occurrence")
    user_id: int = Field(..., description="ID of the user who owns this occurrence")
