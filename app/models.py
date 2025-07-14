from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    Date,
    Enum,
    ForeignKey
)
from sqlalchemy.orm import relationship, declarative_base
import enum

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
    goal_type = Column(Enum(GoalType), nullable=False)

    # Shared progress field (0–100), derived from tasks or cycle completion
    progress = Column(Integer, default=0)

    # Shared relationship: all goal types can have many tasks
    tasks = relationship("Task", back_populates="goal", cascade="all, delete-orphan")

    # Polymorphism setup
    __mapper_args__ = {
        "polymorphic_on": goal_type,
        "polymorphic_identity": "goal",
    }

# === PROJECT GOAL (SUBCLASS) ===

# Step 4: Define subclass for one-time project goals
class ProjectGoal(Goal):
    __tablename__ = "project_goals"

    id = Column(Integer, ForeignKey("goals.id"), primary_key=True)  # Inherits from Goal

    # Projects require explicit end dates
    end_date = Column(Date, nullable=False)

    __mapper_args__ = {
        "polymorphic_identity": "project",
    }

# === HABIT GOAL (SUBCLASS) ===
# Note: Habit goals are recurring and can have multiple cycles
# Step 5: Define subclass for recurring habit goals
class HabitGoal(Goal):
    __tablename__ = "habit_goals"

    id = Column(Integer, ForeignKey("goals.id"), primary_key=True)  # Inherits from Goal
    
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

    
# === HABIT CYCLE ===
# Note: Each habit can have multiple cycles (e.g., every 1 month or every 1 week)
# Step 6: Define HabitCycle model (e.g., one row per week or month)
class HabitCycle(Base):
    __tablename__ = "habit_cycles"

    id = Column(Integer, primary_key=True, index=True)

    # Foreign key to link to parent HabitGoal
    habit_id = Column(Integer, ForeignKey("goals.id"))

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

# === TASK ===

# Step 7: Define Task model (attached to either habit or project goals)
class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)

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

# === GOAL OCCURRENCE Per Cycle ===

class GoalOccurrence(Base):
    __tablename__ = "goal_occurrences"

    id = Column(Integer, primary_key=True, index=True)

    # Foreign key to link to a specific habit cycle
    cycle_id = Column(Integer, ForeignKey("habit_cycles.id"), nullable=False)

    # Order of occurrence within the cycle, e.g., 1st, 2nd, etc.
    sequence_number = Column(Integer, nullable=False)

    # Optional total estimated effort in hours for this occurrence
    estimated_effort = Column(Integer, nullable=True)

    # Status tracking: has this instance been completed?
    completed = Column(Boolean, default=False)

    # Relationship back to HabitCycle
    cycle = relationship("HabitCycle", back_populates="occurrences")

    # Each occurrence may have multiple tasks
    tasks = relationship("Task", back_populates="occurrence", cascade="all, delete-orphan")
