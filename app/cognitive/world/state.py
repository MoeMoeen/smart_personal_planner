# app/cognitive/world/state.py

"""World state representation for task management and user availability."""

from typing import List, Dict, Optional
from datetime import datetime, date, time, timezone
from pydantic import BaseModel, Field
from enum import Enum

# === WORLD MODEL SCHEMAS ===
# Global task coordination and user availability management

class TaskStatus(str, Enum):
    """Status of a calendarized task"""
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress" 
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    OVERDUE = "overdue"

class CalendarizedTask(BaseModel):
    """
    Global view of a single task with its scheduled time slot.
    This represents tasks across ALL goals for global coordination.
    """
    task_id: str
    goal_id: str
    plan_id: str
    title: str
    start_datetime: datetime
    end_datetime: datetime
    estimated_minutes: int
    status: TaskStatus = TaskStatus.SCHEDULED
    
    # Optional relationships
    cycle_id: Optional[str] = None
    occurrence_id: Optional[str] = None
    
    # Metadata
    priority: Optional[int] = None  # 1-5 scale
    tags: Optional[List[str]] = Field(default_factory=list)
    notes: Optional[str] = None

class TimeRange(BaseModel):
    """Represents a time range within a day"""
    start_time: time  # e.g., 08:00
    end_time: time    # e.g., 18:00

class DayAvailability(BaseModel):
    """User's availability for a specific day"""
    date: date
    available_ranges: List[TimeRange] = []
    total_available_minutes: int = 0
    is_blackout: bool = False  # True for vacation days, etc.
    notes: Optional[str] = None

class AvailabilityMap(BaseModel):
    """
    User's availability across time periods.
    Defines when user is available for tasks (e.g., 8am-6pm weekdays).
    """
    user_id: str
    
    # Default weekly pattern
    default_weekly_pattern: Dict[str, List[TimeRange]] = {}  # "monday": [TimeRange(8:00, 18:00)]
    
    # Specific date overrides
    date_specific: List[DayAvailability] = []
    
    # Timezone
    timezone: str = "UTC"

class CapacityConstraints(BaseModel):
    """User's capacity constraints per time period"""
    max_hours_per_day: float = 8.0
    max_hours_per_week: float = 40.0
    max_tasks_per_day: int = 10
    
    # Break requirements
    min_break_between_tasks_minutes: int = 15
    max_consecutive_work_hours: float = 4.0  # Must have break after this

class CapacityMap(BaseModel):
    """
    User's capacity and load constraints.
    Tracks how much work they can handle and current load.
    """
    user_id: str
    constraints: CapacityConstraints
    
    # Current load tracking (calculated from scheduled tasks)
    current_daily_load: Dict[str, float] = {}    # "2025-08-14": 6.5 hours
    current_weekly_load: Dict[str, float] = {}   # "2025-W33": 25.0 hours

class BlackoutWindow(BaseModel):
    """
    Time periods when user is completely unavailable.
    Future enhancement for vacations, meetings, etc.
    """
    start_datetime: datetime
    end_datetime: datetime
    reason: str  # "vacation", "meeting", "personal"
    recurring: bool = False
    recurrence_pattern: Optional[str] = None  # "weekly", "monthly", etc.

class WorldState(BaseModel):
    """
    Complete world model state for a user.
    Provides global view of all tasks, availability, and constraints.
    """
    user_id: str
    
    # All scheduled tasks across all goals/plans
    all_tasks: List[CalendarizedTask] = []
    
    # User's availability and capacity
    availability: AvailabilityMap
    capacity: CapacityMap
    
    # Future: blackout windows
    blackouts: List[BlackoutWindow] = []
    
    # Metadata
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    version: str = "1.0"

class TaskConflict(BaseModel):
    """Represents a scheduling conflict between tasks"""
    task1_id: str
    task2_id: str
    conflict_type: str  # "overlap", "capacity_exceeded", "availability_violation"
    severity: str  # "minor", "major", "critical"
    description: str
    suggested_resolution: Optional[str] = None

class WorldStateValidation(BaseModel):
    """Results of validating world state for conflicts and violations"""
    user_id: str
    is_valid: bool
    conflicts: List[TaskConflict] = []
    capacity_violations: List[str] = []
    availability_violations: List[str] = []
    total_issues: int = 0

# === HELPER FUNCTIONS ===

def create_default_availability(user_id: str) -> AvailabilityMap:
    """Create default availability: 9am-6pm weekdays"""
    return AvailabilityMap(
        user_id=user_id,
        default_weekly_pattern={
            "monday": [TimeRange(start_time=time(9, 0), end_time=time(18, 0))],
            "tuesday": [TimeRange(start_time=time(9, 0), end_time=time(18, 0))],
            "wednesday": [TimeRange(start_time=time(9, 0), end_time=time(18, 0))],
            "thursday": [TimeRange(start_time=time(9, 0), end_time=time(18, 0))],
            "friday": [TimeRange(start_time=time(9, 0), end_time=time(18, 0))],
            "saturday": [],  # Weekend off by default
            "sunday": []     # Weekend off by default
        },
        timezone="UTC"
    )

def create_default_capacity(user_id: str) -> CapacityMap:
    """Create default capacity constraints"""
    return CapacityMap(
        user_id=user_id,
        constraints=CapacityConstraints(
            max_hours_per_day=6.0,      # 6 hours per day
            max_hours_per_week=30.0,    # 30 hours per week  
            max_tasks_per_day=8,
            min_break_between_tasks_minutes=15,
            max_consecutive_work_hours=3.0
        )
    )

def tasks_overlap(task1: CalendarizedTask, task2: CalendarizedTask) -> bool:
    return task1.start_datetime < task2.end_datetime and task2.start_datetime < task1.end_datetime
