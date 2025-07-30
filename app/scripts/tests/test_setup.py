#!/usr/bin/env python3
"""
Simple script to check the database and create test data for plan_feedback endpoint testing
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import SessionLocal
from app.models import User, Goal, Plan
from datetime import date

def check_database():
    """Check what data exists in the database"""
    db = SessionLocal()
    try:
        # Check users
        users = db.query(User).all()
        print(f"Users in database: {len(users)}")
        for user in users:
            print(f"  - User {user.id}: {user.email}")
        
        # Check goals
        goals = db.query(Goal).all()
        print(f"\nGoals in database: {len(goals)}")
        for goal in goals:
            print(f"  - Goal {goal.id}: {goal.title} (Type: {goal.goal_type}, User: {goal.user_id})")
        
        # Check plans
        plans = db.query(Plan).all()
        print(f"\nPlans in database: {len(plans)}")
        for plan in plans:
            print(f"  - Plan {plan.id}: Goal {plan.goal_id}, Approved: {plan.is_approved}, User: {plan.user_id}")
            
        return users, goals, plans
        
    finally:
        db.close()

def create_test_data():
    """Create test data if needed"""
    db = SessionLocal()
    try:
        # Check if we have test data
        users = db.query(User).all()
        if not users:
            print("Creating test user...")
            test_user = User(
                email="test@example.com",
                hashed_password="hashed_password_here"
            )
            db.add(test_user)
            db.commit()
            db.refresh(test_user)
            print(f"Created test user with ID: {test_user.id}")
        else:
            test_user = users[0]
            print(f"Using existing user: {test_user.id}")
        
        # Check if we have test goals
        goals = db.query(Goal).filter(Goal.user_id == test_user.id).all()
        if not goals:
            print("Creating test goal...")
            test_goal = Goal(
                title="Learn Python Programming",
                description="Master Python programming fundamentals",
                start_date=date.today(),
                goal_type="project",
                user_id=test_user.id
            )
            db.add(test_goal)
            db.commit()
            db.refresh(test_goal)
            print(f"Created test goal with ID: {test_goal.id}")
        else:
            test_goal = goals[0]
            print(f"Using existing goal: {test_goal.id}")
        
        # Check if we have test plans
        plans = db.query(Plan).filter(Plan.goal_id == test_goal.id).all()
        if not plans:
            print("Creating test plan...")
            test_plan = Plan(
                goal_id=test_goal.id,
                user_id=test_user.id,
                is_approved=False
            )
            db.add(test_plan)
            db.commit()
            db.refresh(test_plan)
            print(f"Created test plan with ID: {test_plan.id}")
        else:
            test_plan = plans[0]
            print(f"Using existing plan: {test_plan.id}")
            
        return test_user, test_goal, test_plan
        
    finally:
        db.close()

if __name__ == "__main__":
    print("=== Checking database ===")
    users, goals, plans = check_database()
    
    print("\n=== Creating test data if needed ===")
    test_user, test_goal, test_plan = create_test_data()
    
    print("\n=== Test data ready ===")
    print(f"User ID: {test_user.id}")
    print(f"Goal ID: {test_goal.id}")
    print(f"Plan ID: {test_plan.id}")
