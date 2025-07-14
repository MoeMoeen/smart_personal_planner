from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Sequence

from app import models, schemas
from app.crud import crud
from app.db import get_db

# Step 1: Create the API router for goals
router = APIRouter(
    prefix="/goals",
    tags=["goals"]
)

# === CREATE HABIT GOAL ===
@router.post("/habit/", response_model=schemas.GoalRead)
def create_habit_goal(
    goal_data: schemas.HabitGoalCreate,
    db: Session = Depends(get_db)
) -> schemas.GoalRead:
    """
    Create a new habit goal.
    """
    db_goal = crud.create_habit_goal(db, goal_data)
    return db_goal

# === CREATE PROJECT GOAL ===
@router.post("/project/", response_model=schemas.GoalRead)
def create_project_goal(
    goal_data: schemas.ProjectGoalCreate,
    db: Session = Depends(get_db)
) -> schemas.GoalRead:
    """
    Create a new project goal.
    """
    db_goal = crud.create_project_goal(db, goal_data)
    return db_goal

# === GET GOAL BY ID ===
@router.get("/{goal_id}", response_model=schemas.GoalRead)
def get_goal_by_id(
    goal_id: int,
    db: Session = Depends(get_db)
) -> schemas.GoalRead:
    """
    Get a goal by its ID.
    """
    db_goal = crud.get_goal_by_id(db, goal_id)
    if not db_goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return db_goal

# === LIST ALL GOALS ===
@router.get("/", response_model=List[schemas.GoalRead])
def list_goals(
    goal_type: Optional[str] = None,
    db: Session = Depends(get_db)
) -> Sequence[schemas.GoalRead]:
    """
    List all goals, optionally filtered by type.
    """
    db_goals = crud.get_goals(db, goal_type=goal_type)
    return db_goals

# === UPDATE HABIT GOAL ===
@router.put("/habit/{goal_id}", response_model=schemas.GoalRead)
def update_habit_goal(
    goal_id: int,
    updates: schemas.HabitGoalUpdate,
    db: Session = Depends(get_db)
) -> schemas.GoalRead:
    """
    Update an existing habit goal.
    """
    db_goal = crud.update_habit_goal(db, goal_id, updates)
    if not db_goal:
        raise HTTPException(status_code=404, detail="Habit goal not found")
    return db_goal

# === UPDATE PROJECT GOAL ===
@router.put("/project/{goal_id}", response_model=schemas.GoalRead)
def update_project_goal(
    goal_id: int,
    updates: schemas.ProjectGoalUpdate,
    db: Session = Depends(get_db)
) -> schemas.GoalRead:
    """
    Update an existing project goal.
    """
    db_goal = crud.update_project_goal(db, goal_id, updates)
    if not db_goal:
        raise HTTPException(status_code=404, detail="Project goal not found")
    return db_goal

# === DELETE GOAL ===
@router.delete("/{goal_id}", response_model=schemas.GoalRead)
def delete_goal(
    goal_id: int,
    db: Session = Depends(get_db)
) -> schemas.GoalRead:
    """
    Delete a goal by its ID.
    """
    db_goal = crud.delete_goal(db, goal_id)
    if not db_goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return db_goal