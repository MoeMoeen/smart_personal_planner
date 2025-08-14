# app/cognitive/contracts/types.py

from typing import List, Literal, Optional, Union
from datetime import datetime, date
from pydantic import BaseModel, Field

# === CORE PLANNING CONTRACTS ===

# Goal Specification
class GoalSpec(BaseModel):
    goal_id: Optional[str] = None
    user_id: str
    title: str
    description: Optional[str] = None
    goal_type: Literal["project", "habit"]
    start_date: date
    end_date: Optional[date] = None
    recurrence_count: Optional[int] = None
    constraints: Optional[List[str]] = []

# Plan Outline
class PlanOutline(BaseModel):
    goal_id: str
    num_cycles: int
    cycle_duration_days: int
    occurrences_per_cycle: int
    notes: Optional[str] = None

# Occurrence Task
class OccurrenceTask(BaseModel):
    title: str
    type: Literal["core", "preparation", "recovery"]
    estimated_minutes: int
    notes: Optional[str] = None

# Occurrence Tasks
class OccurrenceTasks(BaseModel):
    goal_id: str
    cycle_number: int
    occurrence_number: int
    tasks: List[OccurrenceTask]

# Calendarized Task - used for scheduling tasks in a calendar view
class CalendarizedTask(BaseModel):
    title: str
    start_datetime: datetime
    end_datetime: datetime
    occurrence_id: Optional[str]
    notes: Optional[str] = None

# Calendarized Plan - 
class CalendarizedPlan(BaseModel):
    goal_id: str
    tasks: List[CalendarizedTask]

# Plan Verification Report 
class PlanVerificationReport(BaseModel):
    goal_id: str
    passed: bool
    violations: List[str] = []

# === MEMORY MODELS ===

# Memory Object - This represents a single memory entry
class MemoryObject(BaseModel):
    memory_id: Optional[str] = None
    user_id: str
    goal_id: Optional[str] = None
    type: Literal["episodic", "semantic", "procedural"]
    content: Union[str, dict]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[dict] = {}

# Memory Context - This represents the context in which memories are stored and retrieved
class MemoryContext(BaseModel):
    episodic: List[MemoryObject] = []
    semantic: List[MemoryObject] = []
    procedural: List[MemoryObject] = []
