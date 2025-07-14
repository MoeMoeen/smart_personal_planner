from sqlalchemy.orm import Session
from app.models import HabitGoal, ProjectGoal
from app.ai.schemas import GeneratedPlan


def save_generated_plan(plan: GeneratedPlan, db: Session):
    """
    Save the AI-generated plan into the database.
    Dynamically chooses the goal model (HabitGoal or ProjectGoal) based on goal_type.
    """
    goal_data = plan.goal

    # ✅ Defensive validation: ensure goal_type is supported
    goal_type = goal_data.goal_type.lower()
    if goal_type not in ["habit", "project"]:
        raise ValueError(f"Unsupported goal type: {goal_data.goal_type}")

    # ✅ Create the appropriate model based on goal_type
    if goal_type == "habit":
        db_goal = HabitGoal(
            title=goal_data.title,
            description=goal_data.description,
            start_date=goal_data.start_date,
            end_date=goal_data.end_date,
            goal_type=goal_type,
            recurrence_cycle=goal_data.recurrence_cycle,
            goal_frequency_per_cycle=goal_data.goal_frequency_per_cycle,
            goal_recurrence_count=goal_data.goal_recurrence_count,
            default_estimated_effort_per_occurrence=goal_data.default_estimated_effort_per_occurrence,
            progress=goal_data.progress
        )
    else:  # project
        db_goal = ProjectGoal(
            title=goal_data.title,
            description=goal_data.description,
            start_date=goal_data.start_date,
            end_date=goal_data.end_date,
            goal_type=goal_type,
            progress=goal_data.progress
        )

    # ✅ Add and flush to get goal.id before creating related records
    db.add(db_goal)
    db.flush()

    return db_goal
