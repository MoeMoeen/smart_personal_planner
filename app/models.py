from sqlalchemy import (
    Column,
    Integer,
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


# Step 1: Create the SQLAlchemy base for all models
Base = declarative_base()

# Step 2: Define goal types for polymorphic inheritance
class GoalType(str, enum.Enum):
    project = "project"
    habit = "habit"

# === BASE GOAL (SHARED TABLE) ===

# Step 3: Define the base Goal class (single-table inheritance)
class Goal(Base):
    __tablename__ = "goals"

    # Primary key ID
    id = Column(Integer, primary_key=True, index=True)

    start_date = Column(Date, nullable=False)  # shared by both projects and habits

    # Shared fields
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    goal_type = Column(SQLAlchemyEnum(GoalType), nullable=False)

    # Shared progress field (0–100), derived from tasks or cycle completion
    progress = Column(Integer, default=0)

    # Shared relationship: all goal types can have many tasks
    tasks = relationship("Task", back_populates="goal", cascade="all, delete-orphan")

    # Foreign key to link to the user who owns this goal
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Link to user

    # Relationship back to the user
    user = relationship("User", back_populates="goals")

    # Relationship to plans
    plans = relationship("Plan", back_populates="goal", uselist=True, cascade="all, delete-orphan")

    # Relationship to feedback
    feedback = relationship("Feedback", back_populates="goal", cascade="all, delete-orphan")


    # Polymorphism setup
    __mapper_args__ = {
        "polymorphic_on": goal_type,
        "polymorphic_identity": "goal",
    }

    def __repr__(self):
        try:
            title = self.title
        except (KeyError, AttributeError):
            title = 'N/A'
            
        try:
            start_date = self.start_date
        except (KeyError, AttributeError):
            start_date = 'N/A'
            
        try:
            goal_type = self.goal_type
        except (KeyError, AttributeError):
            goal_type = 'N/A'
            
        return f"<Goal(id={self.id}, title={title}, start_date={start_date}, goal_type={goal_type})>"

# === PROJECT GOAL (SUBCLASS) ===

# Step 4: Define subclass for one-time project goals
class ProjectGoal(Goal):
    __tablename__ = "project_goals"

    id = Column(Integer, ForeignKey("goals.id"), primary_key=True)  # Inherits from Goal

    # user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Link to user - already inherited from Goal

    # Projects require explicit end dates
    end_date = Column(Date, nullable=False)

    __mapper_args__ = {
        "polymorphic_identity": "project",
    }

    def __repr__(self):
        try:
            end_date = self.end_date
        except (KeyError, AttributeError):
            end_date = 'N/A'
        
        try:
            title = self.title
        except (KeyError, AttributeError):
            title = 'N/A'
            
        try:
            start_date = self.start_date
        except (KeyError, AttributeError):
            start_date = 'N/A'
            
        return f"<ProjectGoal(id={self.id}, title={title}, start_date={start_date}, end_date={end_date})>"

# === HABIT GOAL (SUBCLASS) ===
# Note: Habit goals are recurring and can have multiple cycles
# Step 5: Define subclass for recurring habit goals
class HabitGoal(Goal):
    __tablename__ = "habit_goals"

    id = Column(Integer, ForeignKey("goals.id"), primary_key=True)  # Inherits from Goal

    # user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Link to user
    
    end_date = Column(Date, nullable=True)  # Optional for open-ended habits

    # Defines how many cycles to complete the habit goal (e.g., 6 months)
    # This is optional and can be used to limit the habit goal duration
    # If None, the habit can continue indefinitely until manually stopped
    goal_recurrence_count = Column(Integer, nullable=True)     # E.g. 6 months

    # Defines how often to complete the goal per cycle (e.g., 2 times per month)
    goal_frequency_per_cycle = Column(Integer, nullable=False)

    # Cycle type: daily, weekly, monthly, quarterly, annual, etc.
    recurrence_cycle = Column(String, nullable=False)

    # Relationship to individual cycles (e.g. July 2025, Aug 2025, etc.). All habits have cycles.
    cycles = relationship("HabitCycle", back_populates="habit", cascade="all, delete-orphan")

    default_estimated_time_per_cycle = Column(Integer, nullable=True, default=1)  # Default hours per cycle


    # Polymorphic identity for habit goals
    __mapper_args__ = {
        "polymorphic_identity": "habit",
    }

    def __repr__(self):
        try:
            title = self.title
        except (KeyError, AttributeError):
            title = 'N/A'
            
        try:
            start_date = self.start_date
        except (KeyError, AttributeError):
            start_date = 'N/A'
            
        try:
            recurrence_cycle = self.recurrence_cycle
        except (KeyError, AttributeError):
            recurrence_cycle = 'N/A'
            
        return f"<HabitGoal(id={self.id}, title={title}, start_date={start_date}, recurrence_cycle={recurrence_cycle})>"

    
# === HABIT CYCLE ===
# Note: Each habit can have multiple cycles (e.g., every 1 month or every 1 week)
# Step 6: Define HabitCycle model (e.g., one row per week or month)
class HabitCycle(Base):
    __tablename__ = "habit_cycles"

    id = Column(Integer, primary_key=True, index=True)

    # Foreign key to link to parent HabitGoal
    habit_id = Column(Integer, ForeignKey("habit_goals.id"))

    # Foreign key to link to the user
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Foreign key to link to the plan
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=True)

    # Label to identify the cycle (e.g. '2025-07' for monthly)
    cycle_label = Column(String, nullable=False)

    # start and end dates per cycle
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)

    # Progress score per cycle (0–100), updated as tasks are completed
    progress = Column(Integer, default=0)

    # Reverse link to the habit
    habit = relationship("HabitGoal", back_populates="cycles")

    # Each cycle can have multiple occurrences (e.g., 1st, 2nd, etc.)
    occurrences = relationship("GoalOccurrence", back_populates="cycle", cascade="all, delete-orphan")

    # Relationship back to the plan
    plan = relationship("Plan", back_populates="cycles", uselist=False)

    # Relationship back to the user
    user = relationship("User", back_populates="habit_cycles")

    def __repr__(self):
        return f"<HabitCycle(id={self.id}, cycle_label={self.cycle_label}, start_date={self.start_date}, end_date={self.end_date})>"

# === TASK ===

# Step 7: Define Task model (attached to either habit or project goals)
class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)

    # Foreign key to user
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Foreign key to link to the plan
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=True)
    
    # Task details
    title = Column(String, nullable=False)
    due_date = Column(Date, nullable=True)
    estimated_time = Column(Integer, nullable=True)  # Hours estimate
    completed = Column(Boolean, default=False)

    # Link to the parent goal (can be either project or habit)
    goal_id = Column(Integer, ForeignKey("goals.id"))

    # Optional link to a specific cycle (used for habits only)
    cycle_id = Column(Integer, ForeignKey("habit_cycles.id"), nullable=True)

    # Option link to a specific occurrence (used for habits only)
    occurrence_id = Column(Integer, ForeignKey("goal_occurrences.id"), nullable=True)

    # Relationship back to goal (project or habit)
    goal = relationship("Goal", back_populates="tasks")

    # Relationship back to cycle (if applicable)
    occurrence = relationship("GoalOccurrence", back_populates="tasks")

    # Relationship back to user
    user = relationship("User", back_populates="tasks")

    # Relaitonship back to plan
    plan = relationship("Plan", back_populates="tasks", uselist=False)

    def __repr__(self):
        return f"<Task(id={self.id}, title={self.title}, due_date={self.due_date}, completed={self.completed})>"

# === GOAL OCCURRENCE PER CYCLE ===

class GoalOccurrence(Base):
    __tablename__ = "goal_occurrences"

    id = Column(Integer, primary_key=True, index=True)

    # Foreign key to link to the user
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Foreign key to link to a specific habit cycle
    cycle_id = Column(Integer, ForeignKey("habit_cycles.id"), nullable=False)

    # Foreign key to link to the plan
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=True)

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
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    # created_at = Column(Date, nullable=False)


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

    # New Metadata fields 
    refinement_round = Column(Integer, default=0, nullable=True)  # Track refinement rounds. 0 for initial AI-generated plan
    source_plan_id = Column(Integer, ForeignKey("plans.id"), nullable=True)  # Link to the original/source plan if this is a refined version

    # Relationship to the source plan if this is a refined version
    source_plan = relationship("Plan", remote_side=[id], back_populates="refined_plans", uselist=False)

    # Relationship to refined plans (if this is a refined version)
    refined_plans = relationship("Plan", back_populates="source_plan", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Plan(id={self.id}, goal_id={self.goal_id}, is_approved={self.is_approved}, user_id={self.user_id})>"

    
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