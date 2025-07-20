from sqlalchemy.orm import Session
from app.models import HabitGoal, ProjectGoal, HabitCycle, GoalOccurrence
from app.models import Task, Plan
from app.ai.schemas import GeneratedPlan, AIPlanResponse

from app.ai.schemas import GeneratedPlan
from app.models import Plan, Feedback
from sqlalchemy.orm import Session
from app.ai.goal_parser_chain import refine_plan_chain
from fastapi import HTTPException
from app.models import GoalType
from typing import Optional


def save_generated_plan(plan: GeneratedPlan, db: Session, user_id: int, refined_from_plan_id : Optional[int] = None) -> Plan:
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
            default_estimated_time_per_cycle=goal_data.default_estimated_time_per_cycle,
            progress=goal_data.progress,
            user_id=user_id  # Set the user ID for tracking ownership
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
            db_cycle.habit_id = db_goal.id  # Explicit FK
            db_cycle.user_id = db_goal.user_id  # Also if available in the input

            # Add occurrences for this cycle
            for occurrence in cycle.occurrences or []:
                db_occurrence = GoalOccurrence(
                    occurrence_order=occurrence.occurrence_order,
                    estimated_effort=occurrence.estimated_effort,
                    # cycle=db_cycle
                )
                db_occurrence.cycle_id = db_cycle.id  # Explicit FK
                db_occurrence.user_id = db_goal.user_id  # Also if available in the input

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
                    db_task.goal_id = db_goal.id  # Explicit FK
                    db_task.cycle_id = db_cycle.id  # Explicit FK
                    db_task.occurrence_id = db_occurrence.id  # Explicit FK
                    db_task.user_id = db_goal.user_id

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
            progress=goal_data.progress,
            user_id=user_id  # Set the user ID for tracking ownership
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
            db_task.goal_id = db_goal.id  # Explicit FK
            db_task.user_id = db_goal.user_id
            db_goal.tasks.append(db_task)

    # ✅ Commit the entire transaction
    
    db.commit() # Commit everything
    db.refresh(db_goal)  # Refresh to get the latest state with IDs with relationships

    # Determine refinement round
    refinement_round = 0
    if refined_from_plan_id:
        # If this is a refined plan, increment the round
        source_plan = db.query(Plan).filter(Plan.id == refined_from_plan_id).first()
        if source_plan:
            refinement_round = (source_plan.refinement_round or 0) + 1

    # ✅ Create the plan record
    db_plan = Plan(
        goal_id=db_goal.id,
        user_id=user_id,  # Set the user ID for tracking ownership
        is_approved=False,  # Initial state
        refinement_round=refinement_round,  # Set refinement round
        refined_from_plan_id=refined_from_plan_id  # Link to the source plan if this is a refined version
    )
    db.add(db_plan)
    db.commit()  # Commit the plan as well
    db.refresh(db_plan)  # Refresh to get the latest state
    
    # ✅ Return the created plan
    return db_plan

# ------------------------------------------------

def generate_refined_plan_from_feedback(plan_id: int, db: Session) -> AIPlanResponse:
    """
    Re-run the LangChain plan parser with accumulated feedback for a given plan.
    Returns a new GeneratedPlan object.
    """
    # Get the plan
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise ValueError("Plan not found")

    # Get the goal
    goal_id = plan.goal_id
    goal = plan.goal
    if not goal:
        raise ValueError("Goal not found for the given plan")
    
    # Get all feedbacks linked to this goal (across all related plans)
    all_feedback = (
        db.query(Feedback)
        .filter(Feedback.plan.has(goal_id=goal_id))
        .order_by(Feedback.created_at)
        .all()
    )

    # Accumulate all feedbacks
    accumulated_feedback_instructions = ""
    for f in all_feedback:
        accumulated_feedback_instructions += "\n- " + f.feedback_text
        if getattr(f, "suggested_changes", None):
            accumulated_feedback_instructions += f" (Suggested: {f.suggested_changes})"


    # === Format previous plan content === 
    # # Format tasks

    formatted_tasks = "\n".join(
        f"- {task.title} (Due: {task.due_date}, Completed: {task.completed})" for task in plan.tasks) or "No tasks yet."
    
    # Add reccurrence cycles if applicable, i.e., if the goal is a habit
    formatted_cycles = ""
    reccurrence_info = ""
    if goal.goal_type == GoalType.habit:
        habit : HabitGoal = goal
        reccurrence_info = f"""
            Reccurrence Cycle: {habit.goal_frequency_per_cycle} times per {habit.recurrence_cycle},
            Total Cycles: {habit.goal_recurrence_count or 'Open-ended'}
            Default Estimated Time per Cycle: {habit.default_estimated_time_per_cycle or 'Not specified'}""".strip()

        # Format cycles if they exist
        if hasattr(goal, 'cycles') and goal.cycles:
            formatted_cycles = "\n".join(
                f"Cycle {cycle.cycle_label}: {cycle.start_date} to {cycle.end_date} (Progress: {cycle.progress})"
                for cycle in plan.goal.cycles) or "No cycles yet."  

    else:
        reccurrence_info = "This is a project goal, no recurrence cycles."
        
    # Assemble and Format the previous plan section
    previous_plan_content = f"""
    --- Previous Plan (Structured) ---
    Goal Title: {goal.title} ({goal.goal_type.capitalize()})
    Goal Description: {goal.description or 'No description provided.'}
    Start Date: {goal.start_date or 'Not specified'}
    End Date: {goal.end_date or 'Not specified'}  

    Reccurrence Information: {reccurrence_info if reccurrence_info else 'No recurrence information.'}

    Tasks:
    {formatted_tasks}

    Cycles:
    {formatted_cycles if formatted_cycles else 'No cycles available.'}

    --- End of Previous Plan ---
    """.strip()

    # Prepare the refinement prompt input
    
    refinement_prompt_input = {
        "goal_description": plan.goal.description or plan.goal.title,
        "prior_feedback": accumulated_feedback_instructions.strip(),
        "previous_plan": previous_plan_content,
    }

    # Call the refinement AI chain: Invoke the goal parser chain with the accumulated feedback
    try:
        refined_plan = refine_plan_chain.invoke(refinement_prompt_input)["plan"]

        # Validate the refined plan
        if not refined_plan or not refined_plan.goal:
            raise HTTPException(status_code=500, detail="Refined plan generation failed")
        
        if not isinstance(refined_plan, GeneratedPlan):
            raise HTTPException(status_code=500, detail="Refined plan is not valid")

        return AIPlanResponse(
            plan=refined_plan,
            source="AI-Refined",
            ai_version="1.2"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error refining plan: {str(e)}")

# ------------------------------------------------
