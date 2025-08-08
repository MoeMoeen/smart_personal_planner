from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Sequence
import warnings

from app import schemas
from app.crud import crud
from app.db import get_db
from app.routers.users import get_current_user
from app.models import User

# Step 1: Create the API router for goals
router = APIRouter(
    prefix="/goals",
    tags=["goals"]
)

# === CREATE GOAL (Plan-Centric Architecture) ===
@router.post("/", response_model=schemas.GoalRead)
def create_goal(
    goal_data: schemas.GoalCreate,
    db: Session = Depends(get_db)
) -> schemas.GoalRead:
    """
    Create a new lightweight Goal (metadata container).
    Use the /plans/ endpoint to create execution plans for this goal.
    """
    db_goal = crud.create_goal(db, goal_data)
    return db_goal

# === LIST ALL GOALS FOR AUTHENTICATED USER ===
@router.get("/", response_model=List[schemas.GoalRead])
def list_goals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Sequence[schemas.GoalRead]:
    """
    List all goals for the authenticated user.
    """
    db_goals = crud.get_goals_by_user(db, user_id=current_user.id)  # type: ignore
    return db_goals

# === LEGACY ENDPOINTS (Backward Compatibility) ===
@router.post("/habit/", response_model=schemas.GoalRead, deprecated=True)
def create_habit_goal(
    goal_data: schemas.HabitGoalCreate,
    db: Session = Depends(get_db)
) -> schemas.GoalRead:
    """
    [DEPRECATED] Create a habit goal - use POST /goals/ + POST /plans/ instead.
    This endpoint creates both Goal and Plan for backward compatibility.
    """
    warnings.warn(
        "create_habit_goal is deprecated. Use create_goal + create_plan instead.",
        DeprecationWarning,
        stacklevel=2
    )
    
    # Create Goal (metadata)
    goal_create = schemas.GoalCreate(
        title=goal_data.title,
        description=goal_data.description,
        user_id=goal_data.user_id
    )
    db_goal = crud.create_goal(db, goal_create)
    
    # For backward compatibility, we would need to create a Plan here too
    # But since this is deprecated, we'll just create the Goal
    return db_goal

@router.post("/project/", response_model=schemas.GoalRead, deprecated=True)
def create_project_goal(
    goal_data: schemas.ProjectGoalCreate,
    db: Session = Depends(get_db)
) -> schemas.GoalRead:
    """
    [DEPRECATED] Create a project goal - use POST /goals/ + POST /plans/ instead.
    This endpoint creates both Goal and Plan for backward compatibility.
    """
    warnings.warn(
        "create_project_goal is deprecated. Use create_goal + create_plan instead.",
        DeprecationWarning,
        stacklevel=2
    )
    
    # Create Goal (metadata)
    goal_create = schemas.GoalCreate(
        title=goal_data.title,
        description=goal_data.description,
        user_id=goal_data.user_id
    )
    db_goal = crud.create_goal(db, goal_create)
    
    # For backward compatibility, we would need to create a Plan here too
    # But since this is deprecated, we'll just create the Goal
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

# === LIST USER GOALS ===
@router.get("/user/{user_id}", response_model=List[schemas.GoalRead])
def list_goals_for_user(
    user_id: int,
    db: Session = Depends(get_db)
) -> Sequence[schemas.GoalRead]:
    """
    List all goals for a specific user.
    """
    db_goals = crud.get_goals_by_user(db, user_id=user_id)
    return db_goals

# === UPDATE GOAL (Plan-Centric) ===
@router.put("/{goal_id}", response_model=schemas.GoalRead)
def update_goal(
    goal_id: int,
    updates: schemas.GoalUpdate,
    db: Session = Depends(get_db)
) -> schemas.GoalRead:
    """
    Update Goal metadata (title, description). 
    Use PUT /plans/{plan_id} to update execution details.
    """
    db_goal = crud.update_goal(db, goal_id, updates)
    if not db_goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return db_goal

# === LEGACY UPDATE ENDPOINTS (Deprecated) ===
@router.put("/habit/{goal_id}", response_model=schemas.GoalRead, deprecated=True)
def update_habit_goal(
    goal_id: int,
    updates: schemas.HabitGoalUpdate,
    db: Session = Depends(get_db)
) -> schemas.GoalRead:
    """
    [DEPRECATED] Update habit goal - use PUT /goals/{goal_id} + PUT /plans/{plan_id} instead.
    """
    warnings.warn(
        "update_habit_goal is deprecated. Use update_goal + update_plan instead.",
        DeprecationWarning,
        stacklevel=2
    )
    
    # Convert to new GoalUpdate format
    goal_updates = schemas.GoalUpdate(
        title=updates.title,
        description=updates.description
    )
    db_goal = crud.update_goal(db, goal_id, goal_updates)
    if not db_goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return db_goal

@router.put("/project/{goal_id}", response_model=schemas.GoalRead, deprecated=True)
def update_project_goal(
    goal_id: int,
    updates: schemas.ProjectGoalUpdate,
    db: Session = Depends(get_db)
) -> schemas.GoalRead:
    """
    [DEPRECATED] Update project goal - use PUT /goals/{goal_id} + PUT /plans/{plan_id} instead.
    """
    warnings.warn(
        "update_project_goal is deprecated. Use update_goal + update_plan instead.",
        DeprecationWarning,
        stacklevel=2
    )
    
    # Convert to new GoalUpdate format
    goal_updates = schemas.GoalUpdate(
        title=updates.title,
        description=updates.description
    )
    db_goal = crud.update_goal(db, goal_id, goal_updates)
    if not db_goal:
        raise HTTPException(status_code=404, detail="Goal not found")
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