from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import schemas
from app.crud import crud
from app.db import get_db
from typing import List

router = APIRouter(
    prefix="/cycles",
    tags=["Habit Cycles"]
)

@router.post("/{cycle_id}/occurrences", response_model=schemas.GoalOccurrenceRead)
def create_occurrence_for_cycle(
    cycle_id: int,
    data: schemas.GoalOccurrenceCreate,
    db: Session = Depends(get_db)
):
    if cycle_id != data.cycle_id:
        raise HTTPException(
            status_code=400,
            detail="cycle_id mismatch between URL and request body"
        )
    return crud.create_goal_occurrence(db, data)


@router.get("/{cycle_id}/occurrences", response_model=List[schemas.GoalOccurrenceRead])
def list_occurrences_for_cycle(
    cycle_id: int,
    db: Session = Depends(get_db)
):
    return crud.get_occurrences_for_cycle(db, cycle_id)