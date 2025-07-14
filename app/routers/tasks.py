from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app import models, schemas, crud
from app.db import get_db

router = APIRouter(
    prefix="/tasks",
    tags=["tasks"]
)

# === CREATE TASK ===
@router.post("/", response_model=schemas.TaskRead)
def create_task(
    task_data: schemas.TaskCreate,
    db: Session = Depends(get_db)
) -> schemas.TaskRead:
    """
    Create a new task.
    """
    try:
        # Validate that the goal exists
        goal = crud.get_goal_by_id(db, task_data.goal_id)
        if not goal:
            raise HTTPException(status_code=404, detail="Goal not found")
        
        db_task = crud.create_task(db, task_data)
        return db_task
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# === GET TASK BY ID ===
@router.get("/{task_id}", response_model=schemas.TaskRead)
def get_task_by_id(
    task_id: int,
    db: Session = Depends(get_db)
) -> schemas.TaskRead:
    """
    Get a task by its ID.
    """
    db_task = crud.get_task_by_id(db, task_id)
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    return db_task

# === LIST TASKS BY GOAL ===
@router.get("/goal/{goal_id}", response_model=List[schemas.TaskRead])
def get_tasks_by_goal(
    goal_id: int,
    db: Session = Depends(get_db)
) -> List[schemas.TaskRead]:
    """
    Get all tasks for a specific goal.
    """
    # Validate that the goal exists
    goal = crud.get_goal_by_id(db, goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    tasks = crud.get_tasks_by_goal(db, goal_id)
    return tasks

# === UPDATE TASK ===
@router.put("/{task_id}", response_model=schemas.TaskRead)
def update_task(
    task_id: int,
    updates: schemas.TaskUpdate,
    db: Session = Depends(get_db)
) -> schemas.TaskRead:
    """
    Update an existing task.
    """
    try:
        db_task = crud.update_task(db, task_id, updates)
        if not db_task:
            raise HTTPException(status_code=404, detail="Task not found")
        return db_task
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# === DELETE TASK ===
@router.delete("/{task_id}", response_model=schemas.TaskRead)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db)
) -> schemas.TaskRead:
    """
    Delete a task by its ID.
    """
    db_task = crud.delete_task(db, task_id)
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    return db_task

# === MARK TASK AS COMPLETE ===
@router.patch("/{task_id}/complete", response_model=schemas.TaskRead)
def mark_task_complete(
    task_id: int,
    db: Session = Depends(get_db)
) -> schemas.TaskRead:
    """
    Mark a task as completed.
    """
    updates = schemas.TaskUpdate(completed=True)
    db_task = crud.update_task(db, task_id, updates)
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    return db_task

# === MARK TASK AS INCOMPLETE ===
@router.patch("/{task_id}/incomplete", response_model=schemas.TaskRead)
def mark_task_incomplete(
    task_id: int,
    db: Session = Depends(get_db)
) -> schemas.TaskRead:
    """
    Mark a task as incomplete.
    """
    updates = schemas.TaskUpdate(completed=False)
    db_task = crud.update_task(db, task_id, updates)
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    return db_task