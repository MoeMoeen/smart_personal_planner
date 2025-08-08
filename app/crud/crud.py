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

# === USER CRUD OPERATIONS (Used by User Management Router) ===

def get_user_by_id(db: Session, user_id: int) -> Optional[models.User]:
    """Get user by ID"""
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    """Get user by email"""
    return db.query(models.User).filter(models.User.email == email).first()

def get_user_by_telegram_id(db: Session, telegram_user_id: int) -> Optional[models.User]:
    """Get user by Telegram user ID"""
    return db.query(models.User).filter(models.User.telegram_user_id == telegram_user_id).first()

def create_user(db: Session, user_data: schemas.UserCreate, hashed_password: str) -> models.User:
    """Create a new user with email/password authentication"""
    db_user = models.User(
        email=user_data.email,
        username=user_data.username,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        hashed_password=hashed_password,
        telegram_user_id=user_data.telegram_user_id
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def create_telegram_user(db: Session, user_data: schemas.UserCreate) -> models.User:
    """Create a new user from Telegram data (no password required)"""
    db_user = models.User(
        username=user_data.username,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        telegram_user_id=user_data.telegram_user_id
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user(db: Session, user_id: int, user_updates: schemas.UserUpdate) -> Optional[models.User]:
    """Update user information"""
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        return None
    
    update_data = user_updates.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_user, field, value)
    
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user_password(db: Session, user_id: int, hashed_password: str) -> Optional[models.User]:
    """Update user password"""
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        return None
    
    setattr(db_user, "hashed_password", hashed_password)
    db.commit()
    db.refresh(db_user)
    return db_user

def delete_user(db: Session, user_id: int) -> Optional[models.User]:
    """Delete user (soft delete or hard delete based on your requirements)"""
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        return None
    
    # Hard delete - you might want to implement soft delete instead
    db.delete(db_user)
    db.commit()
    return db_user
