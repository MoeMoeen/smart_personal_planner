# app/crud/crud.py

from sqlalchemy.orm import Session
from typing import List, Optional
from app import models, schemas
from app.ai.schemas import PlanFeedbackRequest, PlanFeedbackAction

# === GOAL CRUD OPERATIONS ===

# Create Habit Goal
def create_habit_goal(db: Session, goal_data: schemas.HabitGoalCreate) -> models.HabitGoal:
    db_goal = models.HabitGoal(**goal_data.model_dump())
    db.add(db_goal)
    db.commit()
    db.refresh(db_goal)
    return db_goal

# Create Project Goal
def create_project_goal(db: Session, goal_data: schemas.ProjectGoalCreate) -> models.ProjectGoal:
    db_goal = models.ProjectGoal(**goal_data.model_dump())
    db.add(db_goal)
    db.commit()
    db.refresh(db_goal)
    return db_goal

# Get Goal by ID
def get_goal_by_id(db: Session, goal_id: int) -> Optional[models.Goal]:
    return db.query(models.Goal).filter(models.Goal.id == goal_id).first()

# List All Goals (optionally filtered by type)
def get_goals(db: Session, goal_type: Optional[str] = None) -> List[models.Goal]:
    query = db.query(models.Goal)
    if goal_type:
        query = query.filter(models.Goal.goal_type == goal_type)
    return query.all()

# Update Habit Goal
def update_habit_goal(db: Session, goal_id: int, updates: schemas.HabitGoalUpdate) -> Optional[models.HabitGoal]:
    db_goal = db.query(models.HabitGoal).filter(models.HabitGoal.id == goal_id).first()
    if not db_goal:
        return None
    for key, value in updates.model_dump(exclude_unset=True).items():
        setattr(db_goal, key, value)
    db.commit()
    db.refresh(db_goal)
    return db_goal

# Update Project Goal
def update_project_goal(db: Session, goal_id: int, updates: schemas.ProjectGoalUpdate) -> Optional[models.ProjectGoal]:
    db_goal = db.query(models.ProjectGoal).filter(models.ProjectGoal.id == goal_id).first()
    if not db_goal:
        return None
    for key, value in updates.model_dump(exclude_unset=True).items():
        setattr(db_goal, key, value)
    db.commit()
    db.refresh(db_goal)
    return db_goal

# Delete Goal
def delete_goal(db: Session, goal_id: int) -> Optional[models.Goal]:
    db_goal = db.query(models.Goal).filter(models.Goal.id == goal_id).first()
    if not db_goal:
        return None
    db.delete(db_goal)
    db.commit()
    return db_goal

# === TASK CRUD OPERATIONS ===

# Create Task
def create_task(db: Session, task_data: schemas.TaskCreate) -> models.Task:
    db_task = models.Task(**task_data.model_dump())
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

# Get Task by ID
def get_task_by_id(db: Session, task_id: int) -> Optional[models.Task]:
    return db.query(models.Task).filter(models.Task.id == task_id).first()

# List Tasks by Goal ID
def get_tasks_by_goal(db: Session, goal_id: int) -> List[models.Task]:
    return db.query(models.Task).filter(models.Task.goal_id == goal_id).all()

# Update Task
def update_task(db: Session, task_id: int, updates: schemas.TaskUpdate) -> Optional[models.Task]:
    db_task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not db_task:
        return None
    for key, value in updates.model_dump(exclude_unset=True).items():
        setattr(db_task, key, value)
    db.commit()
    db.refresh(db_task)
    return db_task

# Delete Task
def delete_task(db: Session, task_id: int) -> Optional[models.Task]:
    db_task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not db_task:
        return None
    db.delete(db_task)
    db.commit()
    return db_task

# === HABIT CYCLE CRUD OPERATIONS ===

# Read Habit Cycle by Habit ID
def get_habit_cycles_by_habit(db: Session, habit_id: int) -> List[models.HabitCycle]:
    return db.query(models.HabitCycle).filter(models.HabitCycle.habit_id == habit_id).all()


# === GOAL OCCURRENCE CRUD OPERATIONS ===

# Create Goal Occurrence
def create_goal_occurrence(db: Session, occurrence_data: schemas.GoalOccurrenceCreate) -> models.GoalOccurrence:
    db_occurrence = models.GoalOccurrence(**occurrence_data.model_dump())
    db.add(db_occurrence)
    db.commit()
    db.refresh(db_occurrence)
    return db_occurrence

# Get all occurrences for a given cycle
def get_occurrences_for_cycle(
    db: Session, cycle_id: int
) -> List[models.GoalOccurrence]:
    return db.query(models.GoalOccurrence).filter(
        models.GoalOccurrence.cycle_id == cycle_id
    ).order_by(models.GoalOccurrence.sequence_number).all()

# Update Goal Occurrence 
def update_goal_occurrence(
    db: Session, occurrence_id: int, updates: schemas.GoalOccurrenceUpdate
) -> Optional[models.GoalOccurrence]:
    db_occurrence = db.query(models.GoalOccurrence).filter(
        models.GoalOccurrence.id == occurrence_id
    ).first()
    if not db_occurrence:
        return None
    for key, value in updates.model_dump(exclude_unset=True).items():
        setattr(db_occurrence, key, value)
    db.commit()
    db.refresh(db_occurrence)
    return db_occurrence

# Delete Goal Occurrence
def delete_goal_occurrence(db: Session, occurrence_id: int) -> Optional[models.GoalOccurrence]:
    db_occurrence = db.query(models.GoalOccurrence).filter(
        models.GoalOccurrence.id == occurrence_id
    ).first()
    if not db_occurrence:
        return None
    db.delete(db_occurrence)
    db.commit()
    return db_occurrence

# === PLAN CRUD OPERATIONS ===
# Create Plan
def create_plan(db: Session, plan_data: schemas.PlanCreate) -> models.Plan:
    db_plan = models.Plan(**plan_data.model_dump())
    db.add(db_plan)
    db.commit()
    db.refresh(db_plan)
    return db_plan

# Get Plan by ID
def get_plan_by_id(db: Session, plan_id: int) -> Optional[models.Plan]:
    return db.query(models.Plan).filter(models.Plan.id == plan_id).first()

# List Plans by User ID
def get_plans_by_user(db: Session, user_id: int) -> List[models.Plan]:
    return db.query(models.Plan).filter(models.Plan.user_id == user_id).order_by(models.Plan.created_at.desc()).all()

# Get approved plans by User ID
def get_approved_plans_by_user(db: Session, user_id: int) -> List[models.Plan]:
    return db.query(models.Plan).filter(
        models.Plan.user_id == user_id,
        models.Plan.is_approved
    ).order_by(models.Plan.created_at.desc()).all()

# === FEEDBACK CRUD OPERATIONS ===
# Get Feedback by Plan ID
def get_feedback_by_plan_id(db: Session, plan_id: int) -> Optional[models.Feedback]:
    return db.query(models.Feedback).filter(models.Feedback.plan_id == plan_id).first()

# create_feedback
def create_feedback(db: Session, feedback_data: PlanFeedbackRequest) -> models.Feedback:
    feedback = models.Feedback(
        plan_id=feedback_data.plan_id,
        goal_id=feedback_data.goal_id,
        feedback_text=feedback_data.feedback_text,
        plan_feedback_action=feedback_data.plan_feedback_action,
        suggested_changes=feedback_data.suggested_changes,
        user_id=feedback_data.user_id,
        created_at=feedback_data.timestamp
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback

# get feedbacks by goal ID
def get_feedbacks_by_goal_id(db: Session, goal_id: int) -> List[models.Feedback]:
    return db.query(models.Feedback).filter(models.Feedback.goal_id == goal_id).order_by(models.Feedback.created_at).all()