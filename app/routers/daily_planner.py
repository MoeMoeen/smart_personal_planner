from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, datetime, timedelta
from pydantic import BaseModel, Field

from app.ai.daily_planner import DailyPlannerService
from app.db import get_db

router = APIRouter(
    prefix="/daily-planner",
    tags=["Daily Planning"]
)

# === DAILY PLAN SCHEMAS ===
class DailyPlanRequest(BaseModel):
    plan_date: date = Field(..., description="Date to generate the plan for")
    available_hours: int = Field(8, ge=1, le=24, description="Number of hours available for work")
    user_id: Optional[int] = Field(None, description="Optional user ID for filtering")

class DailyPlanResponse(BaseModel):
    plan_date: date
    available_hours: int
    scheduled_tasks: List[dict]
    total_scheduled_time: int
    remaining_time: int

# === GENERATE DAILY PLAN ===
@router.post("/generate", response_model=DailyPlanResponse)
def generate_daily_plan(
    request: DailyPlanRequest,
    db: Session = Depends(get_db)
):
    """
    Generate a daily plan for a specific date based on goals and tasks.
    """
    try:
        planner_service = DailyPlannerService(db)
        scheduled_tasks = planner_service.generate_daily_plan(
            plan_date=request.plan_date,
            available_hours=request.available_hours,
            user_id=request.user_id
        )
        
        total_scheduled_time = sum(task.get("estimated_time", 0) for task in scheduled_tasks)
        remaining_time = (request.available_hours * 60) - total_scheduled_time
        
        return DailyPlanResponse(
            plan_date=request.plan_date,
            available_hours=request.available_hours,
            scheduled_tasks=scheduled_tasks,
            total_scheduled_time=total_scheduled_time,
            remaining_time=max(0, remaining_time)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to generate daily plan: {str(e)}"
        )

# === QUICK DAILY PLAN ===
@router.get("/today", response_model=DailyPlanResponse)
def get_today_plan(
    available_hours: int = Query(8, ge=1, le=24, description="Hours available today"),
    user_id: Optional[int] = Query(None, description="Optional user ID"),
    db: Session = Depends(get_db)
):
    """
    Generate a daily plan for today.
    """
    today = date.today()
    request = DailyPlanRequest(
        plan_date=today,
        available_hours=available_hours,
        user_id=user_id
    )
    
    return generate_daily_plan(request, db)

# === WEEKLY OVERVIEW ===
@router.get("/week", response_model=List[DailyPlanResponse])
def get_weekly_overview(
    start_date: Optional[date] = Query(None, description="Start date of the week"),
    available_hours: int = Query(8, ge=1, le=24, description="Hours available per day"),
    user_id: Optional[int] = Query(None, description="Optional user ID"),
    db: Session = Depends(get_db)
):
    """
    Generate daily plans for a week.
    """
    if start_date is None:
        start_date = date.today()
    
    weekly_plans = []
    planner_service = DailyPlannerService(db)
    
    for i in range(7):
        current_date = start_date + timedelta(days=i)
        scheduled_tasks = planner_service.generate_daily_plan(
            plan_date=current_date,
            available_hours=available_hours,
            user_id=user_id
        )
        
        total_scheduled_time = sum(task.get("estimated_time", 0) for task in scheduled_tasks)
        remaining_time = (available_hours * 60) - total_scheduled_time
        
        weekly_plans.append(DailyPlanResponse(
            plan_date=current_date,
            available_hours=available_hours,
            scheduled_tasks=scheduled_tasks,
            total_scheduled_time=total_scheduled_time,
            remaining_time=max(0, remaining_time)
        ))
    
    return weekly_plans