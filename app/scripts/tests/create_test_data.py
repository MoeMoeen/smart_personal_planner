from datetime import date, datetime, timezone
from sqlalchemy.orm import Session
from app.db import SessionLocal
from app.models import User, Goal, Plan, Feedback, GoalType, PlanFeedbackAction

# Start a new DB session
db: Session = SessionLocal()

# 1. Create a test user
user = User(email="testuser4@example4.com", hashed_password="hashed4", created_at=datetime.now(timezone.utc))
db.add(user)
db.commit()
db.refresh(user)

# user = db.query(User).filter(User.email == "test@example.com").first()


# 2. Create a goal for that user
goal = Goal(
    title="Test Goal 3",
    description="This is a test goal 3",
    start_date=date.today(),
    goal_type=GoalType.project,
    user_id=user.id
)
db.add(goal)
db.commit()
db.refresh(goal)

# goal = db.query(Goal).filter(Goal.title == "Test Goal").first()


# 3. Create a plan for the goal
plan = Plan(
    goal_id=goal.id,
    user_id=user.id,
    is_approved=True,
)
db.add(plan)
db.commit()
db.refresh(plan)

# plan = db.query(Plan).filter(Plan.id == 11).first()


# 4. Create a feedback entry for the plan
feedback = Feedback(
    user_id=user.id,
    plan_id=plan.id,
    goal_id=goal.id,
    feedback_text="This is a test feedback for plan id 10",
    suggested_changes="No changes needed for this plan id 10",
    plan_feedback_action=PlanFeedbackAction.APPROVE,
    created_at=datetime.now(timezone.utc)
)
db.add(feedback)
db.commit()
db.refresh(feedback)

# goal = db.query(Goal).filter(Goal.title == "Test Goal 3").first()

# 5. Output result
print("✅ Created test records:")
print(f"User ID: {user.id}, Email: {user.email}")
print(f"Goal ID: {goal.id}, Title: {goal.title}, user ID: {goal.user_id}")
print(f"Plan ID: {plan.id}, Goal ID in Plan: {plan.goal_id}, User ID in Plan: {plan.user_id}")
print(f"Feedback ID: {feedback.id}, Feedback Text: {feedback.feedback_text}")