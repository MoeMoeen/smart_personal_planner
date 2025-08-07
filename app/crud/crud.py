# app/crud/crud.py - Minimal CRUD operations for actually used functions

from sqlalchemy.orm import Session
from typing import List, Optional
from app import models, schemas
from app.ai.schemas import PlanFeedbackRequest

# === PLAN CRUD OPERATIONS (Used by Agent Tools) ===

def get_plan_by_id(db: Session, plan_id: int) -> Optional[models.Plan]:
    """Get a plan by ID - used by agent tools and planning router"""
    return db.query(models.Plan).filter(models.Plan.id == plan_id).first()

def get_plans_by_user(db: Session, user_id: int) -> List[models.Plan]:
    """Get all plans for a user - used by agent tools"""
    return db.query(models.Plan).filter(models.Plan.user_id == user_id).order_by(models.Plan.created_at.desc()).all()

def get_approved_plans_by_user(db: Session, user_id: int) -> List[models.Plan]:
    """Get approved plans for a user - used by agent tools"""
    return db.query(models.Plan).filter(
        models.Plan.user_id == user_id,
        models.Plan.is_approved
    ).order_by(models.Plan.created_at.desc()).all()

# === FEEDBACK CRUD OPERATIONS (Used by Planning Router) ===

def get_feedback_by_plan_id(db: Session, plan_id: int) -> Optional[models.Feedback]:
    """Get feedback for a plan - used by planning router"""
    return db.query(models.Feedback).filter(models.Feedback.plan_id == plan_id).first()

def create_feedback(db: Session, feedback_data: PlanFeedbackRequest) -> models.Feedback:
    """Create feedback - used by planning router"""
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

def get_feedbacks_by_goal_id(db: Session, goal_id: int) -> List[models.Feedback]:
    """Get all feedbacks for a goal - used by planning router"""
    return db.query(models.Feedback).filter(models.Feedback.goal_id == goal_id).order_by(models.Feedback.created_at).all()

# === GOAL OCCURRENCE CRUD OPERATIONS (Used by Occurrences Router) ===

def create_goal_occurrence(db: Session, occurrence_data: schemas.GoalOccurrenceCreate) -> models.GoalOccurrence:
    """Create goal occurrence - used by cycles router"""
    db_occurrence = models.GoalOccurrence(**occurrence_data.model_dump())
    db.add(db_occurrence)
    db.commit()
    db.refresh(db_occurrence)
    return db_occurrence

def update_goal_occurrence(
    db: Session, occurrence_id: int, updates: schemas.GoalOccurrenceUpdate
) -> Optional[models.GoalOccurrence]:
    """Update goal occurrence - used by occurrences router"""
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

def delete_goal_occurrence(db: Session, occurrence_id: int) -> Optional[models.GoalOccurrence]:
    """Delete goal occurrence - used by occurrences router"""
    db_occurrence = db.query(models.GoalOccurrence).filter(
        models.GoalOccurrence.id == occurrence_id
    ).first()
    if not db_occurrence:
        return None
    db.delete(db_occurrence)
    db.commit()
    return db_occurrence

# === DEPRECATED GOAL CRUD OPERATIONS ===
# These are kept for backward compatibility with existing routers
# Remove once all clients migrate to AI-based planning

def create_goal(db: Session, goal_data: schemas.GoalCreate) -> models.Goal:
    """DEPRECATED - Create a lightweight Goal (metadata container)."""
    db_goal = models.Goal(
        title=goal_data.title,
        description=goal_data.description,
        user_id=goal_data.user_id
    )
    db.add(db_goal)
    db.commit()
    db.refresh(db_goal)
    return db_goal

def get_goal_by_id(db: Session, goal_id: int) -> Optional[models.Goal]:
    """DEPRECATED - Get goal by ID"""
    return db.query(models.Goal).filter(models.Goal.id == goal_id).first()

def get_goals_by_user(db: Session, user_id: int) -> List[models.Goal]:
    """DEPRECATED - Get goals by user"""
    return db.query(models.Goal).filter(models.Goal.user_id == user_id).all()

def update_goal(db: Session, goal_id: int, updates: schemas.GoalUpdate) -> Optional[models.Goal]:
    """DEPRECATED - Update Goal metadata"""
    db_goal = db.query(models.Goal).filter(models.Goal.id == goal_id).first()
    if not db_goal:
        return None
    for key, value in updates.model_dump(exclude_unset=True).items():
        setattr(db_goal, key, value)
    db.commit()
    db.refresh(db_goal)
    return db_goal

def delete_goal(db: Session, goal_id: int) -> Optional[models.Goal]:
    """DEPRECATED - Delete goal"""
    db_goal = db.query(models.Goal).filter(models.Goal.id == goal_id).first()
    if not db_goal:
        return None
    db.delete(db_goal)
    db.commit()
    return db_goal
