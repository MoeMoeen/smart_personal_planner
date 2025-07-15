from sqlalchemy.orm import Session
from app.models import HabitGoal, ProjectGoal, HabitCycle, GoalOccurrence
from app.models import Task
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
        db.add(db_goal)
        db.flush()  # Ensure ID is generated before adding occurrences
        # Add habit cycles and occurrences
        for cycle in goal_data.habit_cycles or []:
            db_cycle = HabitCycle(
                cycle_label=cycle.cycle_label,
                start_date=cycle.start_date,
                end_date=cycle.end_date,
                progress=cycle.progress,
            )

            # Add occurrences for this cycle
            for occurrence in cycle.occurrences or []:
                db_occurrence = GoalOccurrence(
                    occurrence_order=occurrence.occurrence_order,
                    estimated_effort=occurrence.estimated_effort,
                    # cycle=db_cycle
                )
                # Add tasks to the occurrence
                for task in occurrence.tasks or []:
                    db_task = Task(
                        title=task.title,
                        due_date=task.due_date,
                        estimated_time=task.estimated_time,
                        completed=task.completed,
                        # goal_id=db_goal.id,  # Link to the main goal
                        # occurrence=db_occurrence  # Link to the occurrence
                    )
                    db_occurrence.tasks.append(db_task)

                db_cycle.occurrences.append(db_occurrence)
            
            # Link cycle to the goal
            db_goal.cycles.append(db_cycle)

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
        # Add tasks directly to the project goal
        for task in goal_data.tasks or []:
            db_task = Task(
                title=task.title,
                due_date=task.due_date,
                estimated_time=task.estimated_time,
                completed=task.completed,
                # goal_id=db_goal.id  # Link to the main project goal
            )
            db_goal.tasks.append(db_task)

    # ✅ Commit the entire transaction

    db.commit() # Commit everything
    db.refresh(db_goal)  # Refresh to get the latest state with IDs with relationships

    return db_goal
