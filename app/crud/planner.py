# app/crud/planner.py

from sqlalchemy.orm import Session, selectinload
from app.models import HabitGoal, ProjectGoal, HabitCycle, GoalOccurrence, Goal
from app.models import Task, Plan
from app.ai.schemas import GeneratedPlan, AIPlanResponse

from app.ai.schemas import GeneratedPlan
from app.models import Plan, Feedback
from sqlalchemy.orm import Session
from app.ai.goal_parser_chain import refine_plan_chain
from fastapi import HTTPException
from app.models import GoalType
from typing import Optional
from datetime import date
from app.models import GoalType

def validate_plan_semantics(plan: GeneratedPlan) -> None:
    """
    Validates that the structured plan has all necessary fields
    based on its goal_type. Raises a ValueError if something critical is missing.
    """
    
    goal = plan.goal
    if goal.goal_type == GoalType.habit:
        required_fields = [
            "goal_frequency_per_cycle",
            "goal_recurrence_count",
            "recurrence_cycle",
            "default_estimated_time_per_cycle"
        ]
        for field in required_fields:
            value = getattr(goal, field, None)
            if value is None:
                raise ValueError(f"🚫 Missing required field for habit goal: '{field}'")

        if not goal.habit_cycles:
            raise ValueError("🚫 No habit_cycles defined for habit goal")

        for i, cycle in enumerate(goal.habit_cycles):
            if not cycle.occurrences:
                raise ValueError(f"🚫 Cycle {i + 1} has no occurrences")

            for j, occ in enumerate(cycle.occurrences):
                if not occ.tasks:
                    raise ValueError(f"🚫 Occurrence {j + 1} in cycle {i + 1} has no tasks")

    elif goal.goal_type == GoalType.project:
        if not goal.end_date:
            raise ValueError("🚫 Project goal is missing required end_date")
        if not goal.tasks or len(goal.tasks) == 0:
            raise ValueError("🚫 Project goal has no tasks")

    else:
        raise ValueError(f"🚫 Unknown goal_type: {goal.goal_type}")

def save_generated_plan(plan: GeneratedPlan, db: Session, user_id: int, source_plan_id : Optional[int] = None) -> Plan:
    """
    Save the AI-generated plan into the database.
    Dynamically chooses the goal model (HabitGoal or ProjectGoal) based on goal_type.
    """
    goal_data = plan.goal

    # ✅ Enforce semantic correctness before DB write
    validate_plan_semantics(plan)

    # ✅ Defensive validation: ensure goal_type is supported
    goal_type = goal_data.goal_type
    if goal_type not in [GoalType.habit, GoalType.project]:
        raise ValueError(f"Unsupported goal type: {goal_data.goal_type}")

    if goal_data.goal_type == GoalType.habit:
        required_fields = [
            "goal_frequency_per_cycle",
            "goal_recurrence_count",
            "recurrence_cycle",
            "default_estimated_time_per_cycle"
        ]
        for field in required_fields:
            if getattr(goal_data, field, None) is None:
                raise ValueError(f"Missing required field for habit goal: '{field}'")

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
        if not goal_data.end_date:
            raise ValueError("End date is required for project goals, but none was provided.")
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
    if source_plan_id:
        # If this is a refined plan, increment the round
        source_plan = db.query(Plan).filter(Plan.id == source_plan_id).first()
        if source_plan:
            refinement_round = (source_plan.refinement_round or 0) + 1

    # ✅ Create the plan record
    db_plan = Plan(
        goal_id=db_goal.id,
        user_id=user_id,  # Set the user ID for tracking ownership
        is_approved=False,  # Initial state
        refinement_round=refinement_round,  # Set refinement round
        source_plan_id=source_plan_id  # Link to the source plan if this is a refined version
    )
    db.add(db_plan)
    db.commit()  # Commit the plan as well
    db.refresh(db_plan)  # Refresh to get the latest state
    
    # ✅ Return the created plan
    return db_plan

# ------------------------------------------------

def generate_refined_plan_from_feedback(db: Session, plan_id: int, feedback_text: str, suggested_changes: str):
    """Generate a refined plan based on user feedback using LangChain."""
    try:
        print(f"Starting refinement for plan {plan_id}")
        
        # Load the plan with proper relationships and handle polymorphic loading
        plan = db.query(Plan).options(
            selectinload(Plan.goal),
            selectinload(Plan.tasks),
            selectinload(Plan.cycles).selectinload(HabitCycle.occurrences).selectinload(GoalOccurrence.tasks)
        ).filter(Plan.id == plan_id).first()
        
        if not plan:
            raise ValueError(f"Plan with ID {plan_id} not found")
        
        print(f"Plan loaded: {plan}")
        
        # Load the goal with explicit type handling for polymorphic inheritance
        goal = plan.goal
        if not goal:
            raise ValueError(f"Goal not found for plan {plan_id}")
            
        print(f"Goal loaded: {goal}")
        print(f"Goal type: {type(goal)}")
        
        # Format existing tasks
        formatted_tasks = []
        for task in plan.tasks:
            formatted_tasks.append(f"- {task.title} (Due: {task.due_date or 'No due date'})")
        formatted_tasks = "\n".join(formatted_tasks) if formatted_tasks else "No tasks available."
    
        # Safely get end_date depending on goal type
        end_date = "Not specified"
        goal_end_date = getattr(goal, 'end_date', None)
        if goal_end_date:
            end_date = str(goal_end_date)
        
        # Add recurrence cycles if applicable, i.e., if the goal is a habit
        formatted_cycles = ""
        recurrence_info = ""
        if str(goal.goal_type) == "habit":
            # Cast to HabitGoal to access habit-specific attributes
            habit_goal = db.query(HabitGoal).filter(HabitGoal.id == goal.id).first()
            if habit_goal:
                recurrence_info = f"Frequency: {habit_goal.goal_frequency_per_cycle or 'Not specified'}"

                # Get cycles for this plan
                cycles = plan.cycles or []
                if cycles:
                    formatted_cycles = "\n".join([
                        f"Cycle {cycle.cycle_label}: {cycle.start_date} to {cycle.end_date} (Progress: {cycle.progress})"
                        for cycle in cycles
                    ])
                else:
                    formatted_cycles = "No cycles defined."
            else:
                recurrence_info = "Habit goal details not found."
        else:
            recurrence_info = "Not applicable (Project Goal)"
            
        # Assemble and Format the previous plan section
        previous_plan_content = f"""
        --- Previous Plan (Structured) ---
        Goal Title: {goal.title} ({goal.goal_type.capitalize()})
        Goal Description: {goal.description or 'No description provided.'}
        Start Date: {goal.start_date or 'Not specified'}
        End Date: {getattr(goal, 'end_date', None) or 'Not specified'}  

        Recurrence Information: {recurrence_info if recurrence_info else 'No recurrence information.'}

        Tasks:
        {formatted_tasks}

        Cycles:
        {formatted_cycles if formatted_cycles else 'No cycles available.'}

        --- End of Previous Plan ---
        """.strip()

        # Prepare the refinement prompt input
        
        print(f"About to call refine_plan_chain with feedback: {feedback_text}")
        print(f"Suggested changes: {suggested_changes}")
        
        # # Call the LangChain refinement chain
        # result = refine_plan_chain.invoke({
        #     "goal_description": goal.description or goal.title,
        #     "previous_plan": previous_plan_content,
        #     "prior_feedback": f"Feedback: {feedback_text}\nSuggested Changes: {suggested_changes or 'No specific changes suggested.'}"
        # })

        
        # ✅ 1. Fetch all previous feedback for this goal
        all_feedbacks = (
            db.query(Feedback)
            .filter(Feedback.goal_id == goal.id)
            .order_by(Feedback.created_at.asc())
            .all()
        )

        # ✅ 2. Format each previous feedback entry
        prior_feedback_texts = [
            f"[{fb.created_at.strftime('%Y-%m-%d %H:%M')}] {fb.feedback_text}"
            + (f" — Suggested: {fb.suggested_changes}" if fb.suggested_changes is not None else "")
            for fb in all_feedbacks
        ]

        # ✅ 3. Add the latest feedback from the current request
        prior_feedback_texts.append(
            f"[{date.today().strftime('%Y-%m-%d')} NEW] {feedback_text}"
            + (f" — Suggested: {suggested_changes}" if suggested_changes else "")
        )

        # ✅ 4. Join all into a single block
        prior_feedback_combined = "\n".join(prior_feedback_texts)

        print("------ [DEBUG] Prior Feedback Combined ------")
        print(prior_feedback_combined)
        print("------ [DEBUG] End of Prior Feedback Combined ------")

        # ✅ 5. Use robust refinement function that handles incomplete outputs gracefully
        from app.ai.goal_parser_chain import robust_refine_plan
        
        # Prepare original plan data for field completion
        original_plan_data = None
        if goal.goal_type == "habit":
            habit_goal = db.query(HabitGoal).filter(HabitGoal.id == goal.id).first()
            if habit_goal:
                original_plan_data = {
                    "goal_recurrence_count": habit_goal.goal_recurrence_count,
                    "goal_frequency_per_cycle": habit_goal.goal_frequency_per_cycle,
                    "recurrence_cycle": habit_goal.recurrence_cycle,
                    "default_estimated_time_per_cycle": habit_goal.default_estimated_time_per_cycle
                }
        
        try:
            # Try robust refinement first
            refined_plan_data = robust_refine_plan(
                goal_description=goal.description or goal.title,
                previous_plan=previous_plan_content,
                prior_feedback=prior_feedback_combined,
                original_plan_data=original_plan_data
            )
            result = {"plan": refined_plan_data}
            
        except Exception as e:
            print(f"Robust refinement failed, falling back to original chain: {e}")
            # Fallback to original chain
            result = refine_plan_chain.invoke({
                "goal_description": goal.description or goal.title,
                "previous_plan": previous_plan_content,
                "prior_feedback": prior_feedback_combined
            })
        
        print(f"Plan user_id: {plan.user_id}, type: {type(plan.user_id)}")
        print(f"Plan id: {plan.id}, type: {type(plan.id)}")
        
        # Parse the refined plan and save it
        # The result is a dict with a 'plan' key containing the GeneratedPlan
        if result and isinstance(result, dict) and 'plan' in result:
            refined_plan_data = result['plan']
            print(f"Refined plan data: {refined_plan_data}")
            print(f"Refined plan data type: {type(refined_plan_data)}")
            
            # Save the refined plan with source plan reference
            # Temporarily use original call to test functionality
            from typing import cast
            user_id_val = cast(int, plan.user_id)  
            plan_id_val = cast(int, plan.id)
            
            refined_plan = save_generated_plan(
                plan=refined_plan_data,
                db=db,
                user_id=user_id_val,
                source_plan_id=plan_id_val
            )
            
            print(f"Refined plan saved with ID: {refined_plan.id}")
            # Return both the saved plan and the original GeneratedPlan
            return {"saved_plan": refined_plan, "generated_plan": refined_plan_data}
        else:
            print(f"Unexpected result structure. Result: {result}")
            print(f"Result keys: {result.keys() if isinstance(result, dict) else 'Not a dict'}")
            raise ValueError("Failed to generate refined plan from LangChain")
            
    except Exception as e:
        print(f"Error in generate_refined_plan_from_feedback: {e}")
        raise e
