from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, schemas
from app.crud import crud
from app.db import get_db

router = APIRouter(
    prefix="/occurrences",
    tags=["Goal Occurrences"]
)

@router.get("/{occurrence_id}", response_model=schemas.GoalOccurrenceRead)
def get_occurrence_by_id(
    occurrence_id: int,
    db: Session = Depends(get_db)
) -> schemas.GoalOccurrenceRead:
    """
    Get a goal occurrence by its ID.
    """
    occurrence = db.get(models.GoalOccurrence, occurrence_id)
    if not occurrence:
        raise HTTPException(status_code=404, detail="Occurrence not found")
    return occurrence

@router.put("/{occurrence_id}", response_model=schemas.GoalOccurrenceRead)
def update_occurrence(
    occurrence_id: int,
    updates: schemas.GoalOccurrenceUpdate,
    db: Session = Depends(get_db)
) -> schemas.GoalOccurrenceRead:
    """ Update a goal occurrence by its ID.
    """
    # Ensure the occurrence exists
    occurrence = db.get(models.GoalOccurrence, occurrence_id)
    if not occurrence:
        raise HTTPException(status_code=404, detail="Occurrence not found")
    updated = crud.update_goal_occurrence(db, occurrence_id, updates)
    if not updated:
        raise HTTPException(status_code=404, detail="Occurrence not found")
    return updated

@router.delete("/{occurrence_id}", response_model=schemas.GoalOccurrenceRead)
def delete_occurrence(
    occurrence_id: int,
    db: Session = Depends(get_db)
) -> schemas.GoalOccurrenceRead:
    """ Delete a goal occurrence by its ID.
    """
    # Ensure the occurrence exists
    occurrence = db.get(models.GoalOccurrence, occurrence_id)
    if not occurrence:
        raise HTTPException(status_code=404, detail="Occurrence not found")
    deleted = crud.delete_goal_occurrence(db, occurrence_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Occurrence not found")
    return deleted