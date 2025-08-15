# app/models.py

from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index
)
from sqlalchemy import Enum as SQLAlchemyEnum, JSON
from sqlalchemy.orm import relationship, declarative_base
import enum
from datetime import datetime
from sqlalchemy.sql import func
from typing import Optional


# Step 1: Create the SQLAlchemy base for all models
Base = declarative_base()

# Step 2: Define goal types for polymorphic inheritance
class GoalType(str, enum.Enum):
    project = "project"
    habit = "habit"
    hybrid = "hybrid"


# Task status enum for better type safety and bug prevention
class TaskExecutionStatus(str, enum.Enum):
    """Task execution status with clear lifecycle states."""
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


# Progress status enum for UI/reporting
class ProgressStatus(str, enum.Enum):
    """Progress status with clear completion states."""
    NOT_STARTED = "not_started"    # 0%
    IN_PROGRESS = "in_progress"    # 1-99%  
    COMPLETED = "completed"        # 100%
    BLOCKED = "blocked"            # Cannot progress
    ON_HOLD = "on_hold"           # Temporarily paused


# Recurrence cycle enum for habits type safety
class RecurrenceCycle(str, enum.Enum):
    """Standardized recurrence patterns for habit goals."""
    DAILY = "daily"
    WEEKLY = "weekly" 
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


# AI source enum for better metadata tracking
class PlanSource(str, enum.Enum):
    """Plan creation source for better tracking and analytics."""
    AI_GENERATED = "ai_generated"
    MANUAL_CREATED = "manual_created"
    IMPORTED = "imported"
    REFINED = "refined"
    TEMPLATE = "template"

# === BASE GOAL (SHARED TABLE) ===

# Step 3: Define the base Goal class (single-table inheritance)
class Goal(Base):
    __tablename__ = "goals"

    # Primary key ID
    id = Column(Integer, primary_key=True, index=True)

    # ✅ LIGHTWEIGHT METADATA ONLY (execution details moved to Plan)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    
    # Foreign key to link to the user who owns this goal
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # ✅ RELATIONSHIPS (execution entities now belong to Plan)
    # Relationship back to the user
    user = relationship("User", back_populates="goals")

    # Relationship to plans (this is where all execution logic lives)
    plans = relationship("Plan", back_populates="goal", uselist=True, cascade="all, delete-orphan")

    # Relationship to feedback (through plans)
    feedback = relationship("Feedback", back_populates="goal", cascade="all, delete-orphan")

    # Relationship to scheduled tasks (execution layer)
    scheduled_tasks = relationship("ScheduledTask", back_populates="goal", cascade="all, delete-orphan")

    # Note: tasks, cycles, etc. now belong to Plan, not Goal

    # ✅ DERIVED PROPERTIES for semantic access
    @property
    def primary_goal_type(self) -> Optional['GoalType']:
        """Get the goal_type from the most recent approved plan, or latest plan if none approved"""
        if not self.plans:
            return None
        
        # First try to get from approved plans
        approved_plans = [p for p in self.plans if p.is_approved]
        if approved_plans:
            # Return the most recent approved plan's type
            return max(approved_plans, key=lambda p: p.created_at).goal_type
        
        # Fallback to most recent plan if no approved plans
        return max(self.plans, key=lambda p: p.created_at).goal_type
    
    @property 
    def is_mixed_type(self) -> bool:
        """Check if this goal has plans of different goal_types"""
        if not self.plans:
            return False
        plan_types = {p.goal_type for p in self.plans}
        return len(plan_types) > 1
    
    @property
    def plan_count_by_type(self) -> dict:
        """Count plans by goal_type"""
        from collections import Counter
        return dict(Counter(p.goal_type for p in self.plans))

    def __repr__(self):
        return f"<Goal(id={self.id}, title='{self.title}', user_id={self.user_id})>"

# === HABIT CYCLE ===
# Note: Each habit can have multiple cycles (e.g., every 1 month or every 1 week)
# Step 6: Define HabitCycle model (e.g., one row per week or month)
class HabitCycle(Base):
    __tablename__ = "habit_cycles"

    id = Column(Integer, primary_key=True, index=True)

    # Foreign key to link to parent Goal (not HabitGoal anymore)
    goal_id = Column(Integer, ForeignKey("goals.id"))

    # Foreign key to link to the user
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Foreign key to link to the plan (where the habit execution logic lives)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False)

    # Label to identify the cycle (e.g. '2025-07' for monthly)
    cycle_label = Column(String, nullable=False)

    # start and end dates per cycle
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)

    # Progress score per cycle (0–100), updated as tasks are completed
    progress = Column(Integer, default=0)

    # Reverse link to the goal (now generic Goal, not HabitGoal)
    goal = relationship("Goal", uselist=False)

    # Each cycle can have multiple occurrences (e.g., 1st, 2nd, etc.)
    occurrences = relationship("GoalOccurrence", back_populates="cycle", cascade="all, delete-orphan")

    # Relationship back to the plan (where habit logic lives)
    plan = relationship("Plan", back_populates="cycles", uselist=False)

    # Relationship back to the user
    user = relationship("User", back_populates="habit_cycles")

    def __repr__(self):
        return f"<HabitCycle(id={self.id}, cycle_label={self.cycle_label}, start_date={self.start_date}, end_date={self.end_date})>"

# === TASK ===

# Step 7: Define Task model (now belongs to Plan, not directly to Goal)
class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)

    # Foreign key to user
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Foreign key to link to the plan (REQUIRED - tasks belong to plans now)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False)
    
    # Task details
    title = Column(String, nullable=False)
    due_date = Column(Date, nullable=True)
    estimated_time = Column(Integer, nullable=True)  # Minutes estimate
    
    # Enhanced status tracking
    status = Column(SQLAlchemyEnum(TaskExecutionStatus), nullable=False, default=TaskExecutionStatus.TODO)
    completed = Column(Boolean, default=False)  # Keep for backward compatibility
    completed_at = Column(DateTime, nullable=True)  # Timestamp when completed
    blocked_reason = Column(String, nullable=True)  # Why blocked if status is BLOCKED

    # Link to the parent goal (via plan relationship - indirect)
    goal_id = Column(Integer, ForeignKey("goals.id"))

    # Optional link to a specific cycle (used for habit plans only)
    cycle_id = Column(Integer, ForeignKey("habit_cycles.id"), nullable=True)

    # Optional link to a specific occurrence (used for habit plans only)
    occurrence_id = Column(Integer, ForeignKey("goal_occurrences.id"), nullable=True)

    # Performance indexes for common query patterns
    __table_args__ = (
        Index('ix_tasks_user_status', 'user_id', 'status'),
        Index('ix_tasks_plan_due_date', 'plan_id', 'due_date'),
        Index('ix_tasks_status_due_date', 'status', 'due_date'),
    )

    # ✅ PRIMARY RELATIONSHIP: Task belongs to Plan
    plan = relationship("Plan", back_populates="tasks", uselist=False)

    # Relationship back to goal (indirect via plan)
    goal = relationship("Goal", uselist=False)

    # Relationship back to cycle (if applicable)
    occurrence = relationship("GoalOccurrence", back_populates="tasks")

    # Relationship back to user
    user = relationship("User", back_populates="tasks")

    # Relationship to scheduled tasks (execution layer)
    scheduled_tasks = relationship("ScheduledTask", back_populates="task", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Task(id={self.id}, title={self.title}, plan_id={self.plan_id}, due_date={self.due_date}, completed={self.completed})>"

# === GOAL OCCURRENCE PER CYCLE ===

class GoalOccurrence(Base):
    __tablename__ = "goal_occurrences"

    id = Column(Integer, primary_key=True, index=True)

    # Foreign key to link to the user
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Foreign key to link to a specific habit cycle
    cycle_id = Column(Integer, ForeignKey("habit_cycles.id"), nullable=False)

    # Foreign key to link to the plan (REQUIRED - occurrences belong to plans)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False)

    # Order of occurrence within the cycle, e.g., 1st, 2nd, etc.
    occurrence_order = Column(Integer, nullable=False)

    # Optional total estimated effort in hours for this occurrence
    estimated_effort = Column(Integer, nullable=True)

    # Status tracking: has this instance been completed?
    completed = Column(Boolean, default=False)

    # Relationship back to HabitCycle
    cycle = relationship("HabitCycle", back_populates="occurrences")

    # Each occurrence may have multiple tasks
    tasks = relationship("Task", back_populates="occurrence", cascade="all, delete-orphan")

    # Relationship back to Plan
    plan = relationship("Plan", back_populates="occurrences", uselist=False, single_parent=True)

    # Relationship back to User
    user = relationship("User", back_populates="goal_occurrences")

    def __repr__(self):
        return f"<GoalOccurrence(id={self.id}, occurrence_order={self.occurrence_order}, cycle_id={self.cycle_id})>"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=True)  # Made nullable for Telegram users
    hashed_password = Column(String, nullable=True)  # Made nullable for Telegram users
    
    # Telegram integration fields
    telegram_user_id = Column(BigInteger, unique=True, nullable=True, index=True)  # Telegram user ID
    username = Column(String, nullable=True)  # Telegram username
    first_name = Column(String, nullable=True)  # Telegram first name
    last_name = Column(String, nullable=True)  # Telegram last name

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationship to goals
    goals = relationship("Goal", back_populates="user", cascade="all, delete-orphan")

    # Relationship to tasks
    tasks = relationship("Task", back_populates="user", cascade="all, delete-orphan")

    # Relationship to plans
    plans = relationship("Plan", back_populates="user", cascade="all, delete-orphan")

    # Relationship to habit cycles
    habit_cycles = relationship("HabitCycle", back_populates="user", cascade="all, delete-orphan")

    # Relationship to goal occurrences
    goal_occurrences = relationship("GoalOccurrence", back_populates="user", cascade="all, delete-orphan")

    # Relationship to feedback
    feedback = relationship("Feedback", back_populates="user", cascade="all, delete-orphan")

    # Relationship to scheduled tasks (execution layer)
    scheduled_tasks = relationship("ScheduledTask", back_populates="user", cascade="all, delete-orphan")

    # Relationship to capacity snapshots (analytics)
    capacity_snapshots = relationship("CapacitySnapshot", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"

class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, index=True)
    goal_id = Column(Integer, ForeignKey("goals.id"), nullable=False)
    is_approved = Column(Boolean, default=False, nullable=False)

    # Relationship to the main goal
    goal = relationship("Goal", back_populates="plans")

    # Foreign key to link to the user who owns this plan
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Relationship back to the user
    user = relationship("User", back_populates="plans")

    # Relationship to cycles (if applicable)
    cycles = relationship("HabitCycle", back_populates="plan", cascade="all, delete-orphan", single_parent=True)

    # Relationship to occurrences (if applicable)
    occurrences = relationship("GoalOccurrence", back_populates="plan", cascade="all, delete-orphan")

    # Relationship to tasks (if applicable)
    tasks = relationship("Task", back_populates="plan", cascade="all, delete-orphan")

    # Relationship to feedback
    feedback = relationship("Feedback", back_populates="plan", cascade="all, delete-orphan", uselist=False)

    # Relationship to scheduled tasks (execution layer)
    scheduled_tasks = relationship("ScheduledTask", back_populates="plan", cascade="all, delete-orphan")

    # Additional fields can be added as needed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # ✅ EXECUTION FIELDS (moved from Goal models)
    goal_type = Column(SQLAlchemyEnum(GoalType), nullable=False)  # 'project' or 'habit'
    start_date = Column(Date, nullable=False)  # Plan execution start
    end_date = Column(Date, nullable=False)    # Plan execution end (REQUIRED for all plans)
    progress = Column(Integer, default=0)      # 0-100% completion
    progress_status = Column(SQLAlchemyEnum(ProgressStatus), nullable=False, default=ProgressStatus.NOT_STARTED)

    # ✅ HABIT-SPECIFIC FIELDS (moved from HabitGoal)
    recurrence_cycle = Column(SQLAlchemyEnum(RecurrenceCycle), nullable=True)  # Enum for type safety
    goal_frequency_per_cycle = Column(Integer, nullable=True)  # e.g., 3 times per week
    goal_recurrence_count = Column(Integer, nullable=True)     # e.g., 12 weeks total
    default_estimated_time_per_cycle = Column(Integer, nullable=True)  # minutes per cycle

    # ✅ AI METADATA FIELDS
    source = Column(SQLAlchemyEnum(PlanSource), nullable=False, default=PlanSource.AI_GENERATED)
    ai_version = Column(String, nullable=True)                 # '1.0', '1.1', '2.0'
    refinement_round = Column(Integer, default=0, nullable=True)  # Track refinement rounds. 0 for initial AI-generated plan
    source_plan_id = Column(Integer, ForeignKey("plans.id"), nullable=True)  # Link to the original/source plan if this is a refined version

    # Performance indexes for common query patterns
    __table_args__ = (
        Index('ix_plans_user_goal_type', 'user_id', 'goal_type'),
        Index('ix_plans_date_range', 'start_date', 'end_date'),
        Index('ix_plans_approval_status', 'is_approved', 'goal_type'),
        Index('ix_plans_progress_status', 'progress_status', 'goal_type'),
    )

    # ✅ PLAN RELATIONSHIPS
    # Relationship to the source plan if this is a refined version
    source_plan = relationship("Plan", remote_side=[id], back_populates="refined_plans", uselist=False)

    # Relationship to refined plans (if this is a refined version)
    refined_plans = relationship("Plan", back_populates="source_plan", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Plan(id={self.id}, goal_id={self.goal_id}, goal_type={self.goal_type}, is_approved={self.is_approved}, refinement_round={self.refinement_round}, user_id={self.user_id})>"

    
class PlanFeedbackAction(str, enum.Enum):
    APPROVE = "approve"
    REQUEST_REFINEMENT = "request_refinement"


# Database enum aligned with cognitive layer TaskStatus for type safety
class ScheduledTaskStatus(str, enum.Enum):
    """Database enum aligned with cognitive layer TaskStatus for type safety."""
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress" 
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    OVERDUE = "overdue"


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False, unique=True)  # Ensure one-to-one
    feedback_text = Column(String, nullable=False)
    suggested_changes = Column(JSON, nullable=True)  # Structured suggestions as JSON
    plan_feedback_action = Column(SQLAlchemyEnum(PlanFeedbackAction, name="PlanFeedbackAction"), nullable=False)
    feedback_metadata = Column(JSON, nullable=True)  # Sentiment, categories, priority, etc.
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    goal_id = Column(Integer, ForeignKey("goals.id"), nullable=False) # Link to the goal being planned
    
    # Performance indexes for common query patterns
    __table_args__ = (
        Index('ix_feedback_user_created', 'user_id', 'created_at'),
        Index('ix_feedback_plan_action', 'plan_id', 'plan_feedback_action'),
    )

    # Relationship back to the goal
    goal = relationship("Goal", back_populates="feedback", uselist=False)

    # Relationship back to the user
    user = relationship("User", back_populates="feedback")

    
    # Relationship back to the plan
    plan = relationship("Plan", back_populates="feedback")

    def __repr__(self):
        return f"<Feedback(id={self.id}, user_id={self.user_id}, plan_id={self.plan_id}, goal_id={self.goal_id}, feedback_text={self.feedback_text})>"


# === SCHEDULED TASK (EXECUTION LAYER) ===

class ScheduledTask(Base):
    """
    Scheduled/Calendarized tasks - the execution layer.
    
    This represents tasks that have been scheduled with specific times 
    and are ready for execution. Maps to CalendarizedTask from the 
    cognitive memory layer.
    
    Key relationships:
    - Links to Task (the planning unit)
    - Links to User, Goal, Plan (context)
    - Contains scheduling metadata (start/end times, etc.)
    """
    __tablename__ = "scheduled_tasks"
    
    # Primary key
    id = Column(String, primary_key=True, default=lambda: str(__import__('uuid').uuid4()))
    
    # Context relationships (foreign keys)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    goal_id = Column(Integer, ForeignKey("goals.id"), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False, index=True)
    
    # Optional cycle/occurrence links for habit tasks
    cycle_id = Column(Integer, ForeignKey("habit_cycles.id"), nullable=True)
    occurrence_id = Column(Integer, ForeignKey("goal_occurrences.id"), nullable=True)
    
    # Core scheduling data
    start_datetime = Column(DateTime, nullable=False, index=True)
    end_datetime = Column(DateTime, nullable=False, index=True)
    estimated_minutes = Column(Integer, nullable=False)
    
    # Task metadata (with JSON optimization)
    title = Column(String, nullable=False)  # Cached from task for performance
    priority = Column(Integer, nullable=True)  # 1-5 scale
    tags = Column(JSON, nullable=True)  # JSON array for better querying and filtering
    notes = Column(String, nullable=True)
    
    # Execution status with type safety
    status = Column(SQLAlchemyEnum(ScheduledTaskStatus), nullable=False, default=ScheduledTaskStatus.SCHEDULED)
    
    # Scheduling metadata
    scheduling_reason = Column(String, nullable=True)  # Why scheduled at this time
    scheduling_algorithm = Column(String, nullable=True)  # Which algo scheduled it
    scheduling_confidence = Column(String, nullable=True)  # 0-1 confidence score
    
    # Audit and versioning
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    source_plan_version = Column(String, nullable=True)  # Track plan version
    
    # Performance indexes for common query patterns
    __table_args__ = (
        # Composite index for user's calendar view (most common query)
        Index('ix_scheduled_tasks_user_datetime', 'user_id', 'start_datetime'),
        # Composite index for plan-based queries
        Index('ix_scheduled_tasks_plan_datetime', 'plan_id', 'start_datetime'),
        # Index for status-based filtering and monitoring
        Index('ix_scheduled_tasks_status', 'status'),
        # Index for goal-based timeline queries
        Index('ix_scheduled_tasks_goal_datetime', 'goal_id', 'start_datetime'),
    )
    
    # Relationships
    user = relationship("User", back_populates="scheduled_tasks")
    goal = relationship("Goal", back_populates="scheduled_tasks")
    plan = relationship("Plan", back_populates="scheduled_tasks")
    task = relationship("Task", back_populates="scheduled_tasks")
    cycle = relationship("HabitCycle", uselist=False)
    occurrence = relationship("GoalOccurrence", uselist=False)
    
    def to_calendarized_task(self):
        """
        Convert SQLAlchemy ORM model to Pydantic CalendarizedTask
        This bridges the database layer to the cognitive memory layer
        """
        # Handle tags (now JSON field)
        tags_list = []
        tags_value = getattr(self, 'tags', None)
        if tags_value is not None and not isinstance(tags_value, Column):
            if isinstance(tags_value, list):
                tags_list = tags_value
            elif isinstance(tags_value, str):
                try:
                    import json
                    tags_list = json.loads(tags_value)
                except json.JSONDecodeError:
                    tags_list = []
        
        from app.cognitive.world.state import CalendarizedTask, TaskStatus
        
        # Convert database enum to cognitive enum
        cognitive_status = TaskStatus(self.status.value if hasattr(self.status, 'value') else self.status)
        
        return CalendarizedTask(
            task_id=str(self.task_id),
            goal_id=str(self.goal_id),
            plan_id=str(self.plan_id),
            title=self.title if not isinstance(self.title, Column) and self.title is not None else "",
            start_datetime=self.start_datetime if not isinstance(self.start_datetime, Column) and self.start_datetime is not None else datetime.utcnow(),
            end_datetime=self.end_datetime if not isinstance(self.end_datetime, Column) and self.end_datetime is not None else datetime.utcnow(),
            estimated_minutes=self.estimated_minutes if not isinstance(self.estimated_minutes, Column) and self.estimated_minutes is not None else 0,
            status=cognitive_status,
            cycle_id=str(self.cycle_id) if not isinstance(self.cycle_id, Column) and self.cycle_id is not None else None,
            occurrence_id=str(self.occurrence_id) if not isinstance(self.occurrence_id, Column) and self.occurrence_id is not None else None,
            priority=self.priority if not isinstance(self.priority, Column) and self.priority is not None else None,
            tags=tags_list,
            notes=self.notes if not isinstance(self.notes, Column) and self.notes is not None else None
        )
    
    @classmethod
    def from_calendarized_task(cls, cal_task, user_id: int, plan_id: int, task_id: int):
        """
        Create SQLAlchemy ORM model from Pydantic CalendarizedTask
        This bridges the cognitive memory layer to the database layer
        """
        # Handle tags as JSON array (no longer need to serialize to string)
        tags_value = cal_task.tags if cal_task.tags else None
        
        # Convert cognitive enum to database enum
        db_status = ScheduledTaskStatus(cal_task.status.value) if hasattr(cal_task.status, 'value') else ScheduledTaskStatus(cal_task.status)
        
        return cls(
            id=cal_task.task_id,  # Use task_id as the scheduled task ID
            user_id=user_id,
            goal_id=int(cal_task.goal_id),
            plan_id=plan_id,
            task_id=task_id,
            cycle_id=int(cal_task.cycle_id) if cal_task.cycle_id else None,
            occurrence_id=int(cal_task.occurrence_id) if cal_task.occurrence_id else None,
            start_datetime=cal_task.start_datetime,
            end_datetime=cal_task.end_datetime,
            estimated_minutes=cal_task.estimated_minutes,
            title=cal_task.title,
            priority=cal_task.priority,
            tags=tags_value,
            notes=cal_task.notes,
            status=db_status
        )
    
    def __repr__(self):
        return (f"<ScheduledTask(id={self.id}, title='{self.title}', "
                f"start={self.start_datetime}, status={self.status})>")


class CapacitySnapshot(Base):
    """
    Historical capacity snapshots for analytics and learning.
    Tracks how capacity was used over time.
    """
    __tablename__ = "capacity_snapshots"
    
    id = Column(String, primary_key=True, default=lambda: str(__import__('uuid').uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Time period
    period_type = Column(String, nullable=False)  # daily, weekly
    period_key = Column(String, nullable=False)   # 2025-08-15, 2025-W33
    
    # Capacity data
    limit_hours = Column(String, nullable=False)
    scheduled_hours = Column(String, nullable=False)
    actual_hours = Column(String, nullable=True)  # Filled after execution
    utilization_rate = Column(String, nullable=True)  # scheduled/limit
    
    # Metadata
    snapshot_datetime = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="capacity_snapshots")
    
    def __repr__(self):
        return (f"<CapacitySnapshot(user_id={self.user_id}, period={self.period_key}, "
                f"scheduled={self.scheduled_hours}h/{self.limit_hours}h)>")