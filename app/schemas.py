from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import date, timedelta
from enum import Enum
import re

# === ENUMS ===
# Goal type enum (same as models)
class GoalType(str, Enum):
    project = "project"
    habit = "habit"

# === GOAL SHARED BASE ===
# Base schema for all goals - Shared base class for both projects and habits
# This will be used for creating and updating goals
class GoalBase(BaseModel):
    start_date: date = Field(..., description="Start date of the goal")
    end_date: Optional[date] = Field(None, description="End date of the goal, optional for habits")
    title: str = Field(..., description="Title of the goal", min_length=1, max_length=200)
    description: Optional[str] = Field(None, description="Description of the goal", max_length=1000)
    progress: int = Field(0, ge=0, le=100, description="Progress percentage (0-100)")
    goal_type: GoalType = Field(..., description="Type of the goal (project or habit)")
    
    @validator('title')
    def validate_title(cls, v):
        if not v or not v.strip():
            raise ValueError('Title cannot be empty')
        # Remove extra whitespace
        return v.strip()
    
    @validator('description')
    def validate_description(cls, v):
        if v:
            return v.strip()
        return v
    
    @validator('end_date')
    def validate_end_date(cls, v, values):
        if 'start_date' in values and v and v <= values['start_date']:
            raise ValueError('End date must be after start date')
        return v

# === CREATE GOAL VARIANTS ===
# Schema for creating a new project goal - Extended class for Project-specific fields
class ProjectGoalCreate(GoalBase):
    goal_type: GoalType = GoalType.project
    end_date: date = Field(..., description="End date of the project goal") # Projects require explicit end dates

# Schema for creating a new habit goal - Extended class for Habit-specific fields
class HabitGoalCreate(GoalBase):
    goal_type: GoalType = GoalType.habit
    end_date: Optional[date] = Field(None, description="End date of the habit goal, optional for open-ended habits")
    goal_recurrence_count: Optional[int] = Field(None, ge=1, description="Number of cycles to complete the habit goal (e.g., 6 months)")
    goal_frequency_per_cycle: int = Field(..., ge=1, description="How many times to complete the habit per cycle (e.g., 2 times per month)")
    recurrence_cycle: str = Field(..., description="Recurrence cycle type (e.g., daily, weekly, monthly)")
    default_estimated_time_per_cycle: Optional[int] = Field(1, ge=1, description="Default estimated time per cycle in hours (default is 1 hour)")
    
    @validator('recurrence_cycle')
    def validate_recurrence_cycle(cls, v):
        valid_cycles = ['daily', 'weekly', 'monthly', 'quarterly', 'yearly']
        if v.lower() not in valid_cycles:
            raise ValueError(f'Recurrence cycle must be one of: {", ".join(valid_cycles)}')
        return v.lower()
    
    @validator('goal_frequency_per_cycle')
    def validate_frequency(cls, v):
        if v <= 0:
            raise ValueError('Goal frequency per cycle must be positive')
        return v

# === UPDATE GOAL VARIANTS ===
# Schema for updating an existing habit goal - Used for PUT/PATCH requests
class HabitGoalUpdate(BaseModel):
    title: Optional[str] = Field(None, description="Update the title of the habit")
    description: Optional[str] = Field(None, description="Update the description of the habit")
    start_date: Optional[date] = Field(None, description="Update the start date")
    end_date: Optional[date] = Field(None, description="Update the end date (optional)")
    progress: Optional[int] = Field(None, ge=0, le=100, description="Update overall progress percentage")
    goal_recurrence_count: Optional[int] = Field(None, description="Update recurrence count")
    goal_frequency_per_cycle: Optional[int] = Field(None, gt=0, description="Update frequency per cycle")
    recurrence_cycle: Optional[str] = Field(None, description="Update cycle unit (daily, weekly, etc.)")
    default_estimated_time_per_cycle: Optional[int] = Field(None, description="Update default estimated time per cycle in hours")

# Schema for updating an existing project goal - Used for PUT/PATCH requests
class ProjectGoalUpdate(BaseModel):
    title: Optional[str] = Field(None, description="Update the title of the project")
    description: Optional[str] = Field(None, description="Update the description of the project")
    start_date: Optional[date] = Field(None, description="Update the start date")
    end_date: Optional[date] = Field(None, description="Update the end date")
    progress: Optional[int] = Field(None, ge=0, le=100, description="Update progress score (0–100)")

# === GOAL READ MODEL ===
# Response model
# Schema for reading a goal - Used for GET requests to retrieve goal details and for other goal-related operations
class GoalRead(GoalBase):
    id: int = Field(..., description="Unique identifier of the goal")
    # tasks: List[int] = Field([], description="List of task IDs associated with this goal")

    class Config:
        from_attributes = True  # Enable ORM mode to read from SQLAlchemy models

# === TASK MODELS ===
# Schema for task creation - Used for creating tasks associated with goals
class TaskCreate(BaseModel):
    title: str = Field(..., description="Title of the task", min_length=1, max_length=200)
    due_date: Optional[date] = Field(None, description="Due date of the task")
    estimated_time: Optional[int] = Field(None, ge=1, description="Estimated time in hours to complete this task")
    completed: Optional[bool] = Field(False, description="Whether the task is completed")
    goal_id: int = Field(..., description="ID of the goal this task belongs to", gt=0)
    cycle_id: Optional[int] = Field(None, description="ID of the cycle this task belongs to, if applicable")
    occurrence_id: Optional[int] = Field(None, description="ID of goal occurrence this task is part of (if habit)")
    
    @validator('title')
    def validate_title(cls, v):
        if not v or not v.strip():
            raise ValueError('Title cannot be empty')
        return v.strip()
    
    @validator('due_date')
    def validate_due_date(cls, v):
        # Allow any date - removed strict past date validation
        return v

# Schema for updating an existing task - Used for PUT/PATCH requests
class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, description="Title of the task", min_length=1, max_length=200)
    due_date: Optional[date] = Field(None, description="Due date of the task")
    completed: Optional[bool] = Field(None, description="Whether the task is completed")
    estimated_time: Optional[int] = Field(None, ge=1, description="Estimated time to complete the task in hours")
    goal_id: Optional[int] = Field(None, description="Update the parent goal ID", gt=0)
    cycle_id: Optional[int] = Field(None, description="Update the associated cycle ID (for habits)")
    occurrence_id: Optional[int] = Field(None, description="Reassign task to a different goal occurrence (optional)")
    
    @validator('title')
    def validate_title(cls, v):
        if v is not None and (not v or not v.strip()):
            raise ValueError('Title cannot be empty')
        return v.strip() if v else v


# Schema for reading a task - Used for GET requests to retrieve task details
class TaskRead(TaskCreate):
    id: int = Field(..., description="Unique identifier of the task")

    class Config:
        from_attributes = True  # Enable ORM mode to read from SQLAlchemy models

# === GOAL OCCURRENCE READ-ONLY ===

class GoalOccurrenceRead(BaseModel):
    id: int = Field(..., description="Unique ID of the goal occurrence within a cycle")
    cycle_id: int = Field(..., description="ID of the parent habit cycle")
    sequence_number: int = Field(..., description="Order of this occurrence in the cycle")
    estimated_effort: Optional[int] = Field(None, description="Estimated total hours for this goal occurrence")
    completed: bool = Field(False, description="Whether this goal occurrence has been completed")

    class Config:
        from_attributes = True

# === GOAL OCCURRENCE CREATE/UPDATE === 
class GoalOccurrenceCreate(BaseModel):
    cycle_id: int = Field(..., description="ID of the parent habit cycle")
    sequence_number: int = Field(..., description="Order of this occurrence in the cycle")
    estimated_effort: Optional[int] = Field(None, description="Estimated total hours for this goal occurrence")
    completed: bool = Field(False, description="Whether this goal occurrence has been completed")

class GoalOccurrenceUpdate(BaseModel):
    sequence_number: Optional[int] = Field(None, description="Order of this occurrence in the cycle")
    estimated_effort: Optional[int] = Field(None, description="Estimated total hours for this goal occurrence")
    completed: Optional[bool] = Field(None, description="Whether this goal occurrence has been completed")


# === HABIT CYCLE READ-ONLY ===
# Schema for habit cycle read-only model - Used for creating and reading habit cycles
class HabitCycleRead(BaseModel):
    id: int = Field(..., description="Unique identifier of the habit cycle")
    start_date: date = Field(..., description="Start date of the habit cycle")
    end_date: Optional[date] = Field(None, description="End date of the habit cycle, optional for open-ended cycles")
    habit_id: int = Field(..., description="ID of the habit this cycle belongs to")
    cycle_label: str = Field(..., description="Label for the cycle (e.g., 'July 2025')")
    progress: int = Field(0, ge=0, le=100, description="Progress score for the cycle (0-100)")
    occurrences: List[GoalOccurrenceRead] = Field([], description="List of scheduled goal occurrences in this cycle")

    class Config:
        from_attributes = True  # Enable ORM mode to read from SQLAlchemy models

# === HABIT CYCLE CREATE/UPDATE ===
class HabitCycleCreate(BaseModel):
    start_date: date = Field(..., description="Start date of the habit cycle")
    end_date: Optional[date] = Field(None, description="End date of the habit cycle, optional for open-ended cycles")
    habit_id: int = Field(..., description="ID of the habit this cycle belongs to")
    cycle_label: str = Field(..., description="Label for the cycle (e.g., 'July 2025')")
    progress: int = Field(0, ge=0, le=100, description="Progress score for the cycle (0-100)")


