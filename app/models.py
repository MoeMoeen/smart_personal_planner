# app/models.py

from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    Boolean,
    Date,
    DateTime,
    ForeignKey
)
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy.orm import relationship, declarative_base
import enum
from sqlalchemy.sql import func
from typing import Optional


# Step 1: Create the SQLAlchemy base for all models
Base = declarative_base()

# Step 2: Define goal types for polymorphic inheritance
class GoalType(str, enum.Enum):
    project = "project"
    habit = "habit"
    hybrid = "hybrid"

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
    completed = Column(Boolean, default=False)

    # Link to the parent goal (via plan relationship - indirect)
    goal_id = Column(Integer, ForeignKey("goals.id"))

    # Optional link to a specific cycle (used for habit plans only)
    cycle_id = Column(Integer, ForeignKey("habit_cycles.id"), nullable=True)

    # Optional link to a specific occurrence (used for habit plans only)
    occurrence_id = Column(Integer, ForeignKey("goal_occurrences.id"), nullable=True)

    # ✅ PRIMARY RELATIONSHIP: Task belongs to Plan
    plan = relationship("Plan", back_populates="tasks", uselist=False)

    # Relationship back to goal (indirect via plan)
    goal = relationship("Goal", uselist=False)

    # Relationship back to cycle (if applicable)
    occurrence = relationship("GoalOccurrence", back_populates="tasks")

    # Relationship back to user
    user = relationship("User", back_populates="tasks")

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

    # Additional fields can be added as needed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # ✅ EXECUTION FIELDS (moved from Goal models)
    goal_type = Column(SQLAlchemyEnum(GoalType), nullable=False)  # 'project' or 'habit'
    start_date = Column(Date, nullable=False)  # Plan execution start
    end_date = Column(Date, nullable=False)    # Plan execution end (REQUIRED for all plans)
    progress = Column(Integer, default=0)      # 0-100% completion

    # ✅ HABIT-SPECIFIC FIELDS (moved from HabitGoal)
    recurrence_cycle = Column(String, nullable=True)           # 'daily', 'weekly', 'monthly'
    goal_frequency_per_cycle = Column(Integer, nullable=True)  # e.g., 3 times per week
    goal_recurrence_count = Column(Integer, nullable=True)     # e.g., 12 weeks total
    default_estimated_time_per_cycle = Column(Integer, nullable=True)  # minutes per cycle

    # ✅ AI METADATA FIELDS
    source = Column(String, default='AI', nullable=False)      # 'AI', 'manual', 'imported'
    ai_version = Column(String, nullable=True)                 # '1.0', '1.1', '2.0'
    refinement_round = Column(Integer, default=0, nullable=True)  # Track refinement rounds. 0 for initial AI-generated plan
    source_plan_id = Column(Integer, ForeignKey("plans.id"), nullable=True)  # Link to the original/source plan if this is a refined version

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

class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False, unique=True)  # Ensure one-to-one
    feedback_text = Column(String, nullable=False)
    suggested_changes = Column(String, nullable=True)
    plan_feedback_action = Column(SQLAlchemyEnum(PlanFeedbackAction, name="PlanFeedbackAction"), nullable=False)
    # created_at = Column(Date, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    goal_id = Column(Integer, ForeignKey("goals.id"), nullable=False) # Link to the goal being planned

    # Relationship back to the goal
    goal = relationship("Goal", back_populates="feedback", uselist=False)

    # Relationship back to the user
    user = relationship("User", back_populates="feedback")

    
    # Relationship back to the plan
    plan = relationship("Plan", back_populates="feedback")

    def __repr__(self):
        return f"<Feedback(id={self.id}, user_id={self.user_id}, plan_id={self.plan_id}, goal_id={self.goal_id}, feedback_text={self.feedback_text})>"

# Import memory models to ensure they're included in migrations
from app.memory.schemas import MemoryORM, MemoryAssociation