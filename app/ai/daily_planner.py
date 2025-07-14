"""Daily planner module for generating personalized daily plans."""

from datetime import date, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from app import models, schemas
from app.crud import get_goals, get_tasks_by_goal


class DailyPlannerService:
    """Service for generating daily plans based on user goals and tasks."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def generate_daily_plan(
        self, 
        plan_date: date, 
        available_hours: int = 8,
        user_id: Optional[int] = None
    ) -> List[dict]:
        """
        Generate a daily plan for a specific date.
        
        Args:
            plan_date: The date to generate the plan for
            available_hours: Number of hours available for work
            user_id: Optional user ID for filtering goals
            
        Returns:
            List of tasks scheduled for the day
        """
        # Get all active goals (this is a simplified implementation)
        goals = get_goals(self.db)
        
        # Filter goals that are active on the plan date
        active_goals = []
        for goal in goals:
            if goal.start_date <= plan_date:
                if not goal.end_date or goal.end_date >= plan_date:
                    active_goals.append(goal)
        
        # Get tasks for active goals
        scheduled_tasks = []
        total_time = 0
        
        for goal in active_goals:
            tasks = get_tasks_by_goal(self.db, goal.id)
            
            for task in tasks:
                # Skip completed tasks
                if task.completed:
                    continue
                
                # Check if task is due soon or overdue
                if task.due_date and task.due_date <= plan_date + timedelta(days=7):
                    estimated_time = task.estimated_time or 1
                    
                    # Check if we have enough time left
                    if total_time + estimated_time <= available_hours * 60:  # Convert to minutes
                        scheduled_tasks.append({
                            "task_id": task.id,
                            "title": task.title,
                            "estimated_time": estimated_time,
                            "due_date": task.due_date,
                            "goal_title": goal.title,
                            "priority": self._calculate_priority(task, plan_date)
                        })
                        total_time += estimated_time
        
        # Sort by priority (highest first)
        scheduled_tasks.sort(key=lambda x: x["priority"], reverse=True)
        
        return scheduled_tasks
    
    def _calculate_priority(self, task: models.Task, plan_date: date) -> int:
        """Calculate task priority based on due date and other factors."""
        priority = 0
        
        if task.due_date:
            days_until_due = (task.due_date - plan_date).days
            if days_until_due <= 0:
                priority += 100  # Overdue tasks get highest priority
            elif days_until_due <= 3:
                priority += 50   # Due soon
            elif days_until_due <= 7:
                priority += 25   # Due this week
        
        # Add priority based on estimated time (shorter tasks get slight boost)
        if task.estimated_time:
            if task.estimated_time <= 30:
                priority += 10
            elif task.estimated_time <= 60:
                priority += 5
        
        return priority