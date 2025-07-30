#!/usr/bin/env python3

from app.db import SessionLocal
from app.models import Goal, Plan, Task, HabitCycle
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta

def create_test_plan():
    """Create a new plan for testing refinement"""
    print("Starting create_test_plan...")
    db = SessionLocal()
    try:
        print("Connected to database")
        # Find a goal that exists
        goal = db.query(Goal).filter(Goal.id == 8).first()
        print(f"Found goal: {goal}")
        if not goal:
            print("Goal 8 not found, creating a new goal...")
            goal = Goal(
                id=100,  # Use a high ID to avoid conflicts
                title="Test Goal for Refinement",
                description="A test goal to check refinement logic",
                user_id=1,
                goal_type="simple",
                priority="medium",
                status="active",
                start_date=datetime.now().date(),
                end_date=(datetime.now() + timedelta(days=30)).date()
            )
            db.add(goal)
            db.flush()  # Get the ID
            print(f"Created goal with ID: {goal.id}")
        
        # Create a new plan
        new_plan = Plan(
            goal_id=goal.id,
            user_id=goal.user_id,
            is_approved=False
        )
        
        db.add(new_plan)
        db.flush()  # Get the plan ID
        
        # Add some tasks
        task1 = Task(
            plan_id=new_plan.id,
            user_id=goal.user_id,
            goal_id=goal.id,
            title="Task 1 - Set up environment",
            due_date=(datetime.now() + timedelta(days=7)).date(),
            estimated_time=4,
            completed=False
        )
        
        task2 = Task(
            plan_id=new_plan.id,
            user_id=goal.user_id,
            goal_id=goal.id,
            title="Task 2 - Complete implementation", 
            due_date=(datetime.now() + timedelta(days=14)).date(),
            estimated_time=8,
            completed=False
        )
        
        db.add(task1)
        db.add(task2)
        
        db.commit()
        
        print(f"✅ Created test plan with ID: {new_plan.id}")
        print(f"   Goal ID: {goal.id}")
        print(f"   User ID: {goal.user_id}")
        print(f"   Tasks: {task1.title}, {task2.title}")
        
        return new_plan.id, goal.id, goal.user_id
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error creating test plan: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None
    finally:
        db.close()

if __name__ == "__main__":
    plan_id, goal_id, user_id = create_test_plan()
    if plan_id:
        print(f"\nUse this for testing:")
        print(f"Plan ID: {plan_id}")
        print(f"Goal ID: {goal_id}")
        print(f"User ID: {user_id}")
