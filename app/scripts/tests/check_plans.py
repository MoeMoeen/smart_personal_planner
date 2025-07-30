#!/usr/bin/env python3
"""
Check which plans don't have feedback yet
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import SessionLocal
from app.models import Plan, Feedback

def check_plans_without_feedback():
    """Check which plans don't have feedback yet"""
    db = SessionLocal()
    try:
        # Get all plans
        plans = db.query(Plan).all()
        print(f"Total plans in database: {len(plans)}")
        
        # Check which ones have feedback
        for plan in plans:
            feedback = db.query(Feedback).filter(Feedback.plan_id == plan.id).first()
            feedback_status = "HAS FEEDBACK" if feedback else "NO FEEDBACK"
            print(f"  - Plan {plan.id}: Goal {plan.goal_id}, User {plan.user_id}, Approved: {plan.is_approved} - {feedback_status}")
            
        # Find plans without feedback
        plans_without_feedback = []
        for plan in plans:
            feedback = db.query(Feedback).filter(Feedback.plan_id == plan.id).first()
            if not feedback:
                plans_without_feedback.append(plan)
        
        print(f"\nPlans without feedback: {len(plans_without_feedback)}")
        for plan in plans_without_feedback:
            print(f"  - Plan {plan.id}: Goal {plan.goal_id}, User {plan.user_id}")
            
    finally:
        db.close()

if __name__ == "__main__":
    check_plans_without_feedback()
