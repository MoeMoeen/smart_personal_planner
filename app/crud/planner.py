# app/crud/planner.py

from sqlalchemy.orm import Session, selectinload
from app.models import Goal, HabitCycle, GoalOccurrence, Task, Plan, Feedback
from app.DEPRECATED.DEPRECATED_ai.schemas import GeneratedPlan
from app.models import GoalType
from typing import Optional
from datetime import date
import logging

logger = logging.getLogger(__name__)

def validate_plan_semantics(plan: GeneratedPlan) -> None:
    """
    Validates that the structured plan has all necessary fields
    based on its goal_type. Raises a ValueError if something critical is missing.
    """
    
    goal_data = plan.goal  # Goal metadata (title, description)
    plan_data = plan.plan  # Plan execution details (goal_type, dates, etc.)
    
    if plan_data.goal_type == GoalType.habit:
        required_fields = [
            "goal_frequency_per_cycle",
            "goal_recurrence_count", 
            "recurrence_cycle",
            "default_estimated_time_per_cycle"
        ]
        for field in required_fields:
            value = getattr(plan_data, field, None)
            if value is None:
                raise ValueError(f"🚫 Missing required field for habit plan: '{field}'")

        if not plan_data.habit_cycles:
            raise ValueError("🚫 No habit_cycles defined for habit plan")

        for i, cycle in enumerate(plan_data.habit_cycles):
            if not cycle.occurrences:
                raise ValueError(f"🚫 Cycle {i + 1} has no occurrences")

            for j, occ in enumerate(cycle.occurrences):
                if not occ.tasks:
                    raise ValueError(f"🚫 Occurrence {j + 1} in cycle {i + 1} has no tasks")

    elif plan_data.goal_type == GoalType.project:
        if not plan_data.end_date:
            raise ValueError("🚫 Project plan is missing required end_date")
        if not plan_data.tasks or len(plan_data.tasks) == 0:
            raise ValueError("🚫 Project plan has no tasks")
    
    elif plan_data.goal_type == GoalType.hybrid:
        # Hybrid plans need both structures
        if not plan_data.habit_cycles:
            raise ValueError("🚫 Hybrid plan is missing habit_cycles")
        if not plan_data.tasks or len(plan_data.tasks) == 0:
            raise ValueError("🚫 Hybrid plan is missing tasks")
        
        # Validate habit cycles structure
        for i, cycle in enumerate(plan_data.habit_cycles):
            if not cycle.occurrences:
                raise ValueError(f"🚫 Cycle {i + 1} has no occurrences")
            for j, occ in enumerate(cycle.occurrences):
                if not occ.tasks:
                    raise ValueError(f"🚫 Occurrence {j + 1} in cycle {i + 1} has no tasks")

    else:
        raise ValueError(f"🚫 Unknown goal_type: {plan_data.goal_type}")

def save_generated_plan(plan: GeneratedPlan, db: Session, user_id: int, source_plan_id: Optional[int] = None) -> Plan:
    """
    Save the AI-generated plan into the database using the new Plan-centric architecture.
    Creates a lightweight Goal for metadata and a Plan for all execution details.
    """
    goal_data = plan.goal  # Lightweight metadata (title, description)
    plan_data = plan.plan  # All execution details (goal_type, dates, tasks, cycles)

    # ✅ Enhanced validation with detailed completeness checking
    validate_plan_semantics(plan)
    
    # ✅ Additional completeness validation
    from app.DEPRECATED.DEPRECATED_ai.goal_parser_chain import validate_plan_completeness
    is_valid, issues = validate_plan_completeness(plan)
    
    if not is_valid:
        logger.warning("🚨 Plan validation issues detected:")
        for issue in issues:
            logger.warning(f"  - {issue}")
        # Continue with save but log the issues for debugging
        # In production, you might want to reject incomplete plans
    else:
        logger.info("✅ Plan passed all validation checks")

    # ✅ Defensive validation: ensure goal_type is supported
    goal_type = plan_data.goal_type
    if goal_type not in [GoalType.habit, GoalType.project, GoalType.hybrid]:
        raise ValueError(f"Unsupported goal type: {plan_data.goal_type}")

    # ✅ Create or reuse Goal (lightweight metadata container)
    if source_plan_id is not None:
        # Refined plan: reuse existing goal
        source_plan = db.query(Plan).filter(Plan.id == source_plan_id).first()
        if not source_plan:
            raise ValueError(f"Source plan with ID {source_plan_id} not found")
        db_goal = source_plan.goal
    else:
        # New plan (not a refined plan, so it's about a new goal essentially): create new goal
        db_goal = Goal(
            title=goal_data.title,
            description=goal_data.description,
            user_id=user_id
        )
        db.add(db_goal)
        db.flush()  # Get goal.id

    # ✅ Create Plan (central orchestrator with all execution details)
    db_plan = Plan(
        goal_id=db_goal.id,
        goal_type=goal_type,
        start_date=plan_data.start_date,
        end_date=plan_data.end_date,
        progress=plan_data.progress,
        
        # Habit-specific fields (for habit and hybrid plans)
        recurrence_cycle=plan_data.recurrence_cycle,
        goal_frequency_per_cycle=plan_data.goal_frequency_per_cycle,
        goal_recurrence_count=plan_data.goal_recurrence_count,
        default_estimated_time_per_cycle=plan_data.default_estimated_time_per_cycle,
        
        # Refinement tracking (from GeneratedPlan level)
        refinement_round=plan.refinement_round,
        source_plan_id=plan.source_plan_id if source_plan_id is None else source_plan_id,
        
        user_id=user_id
    )
    db.add(db_plan)
    db.flush()  # Get plan.id

    # ✅ Add habit cycles (for habit and hybrid plans)
    if plan_data.habit_cycles:
        for cycle in plan_data.habit_cycles:
            db_cycle = HabitCycle(
                plan_id=db_plan.id,  # Link to Plan, not Goal
                cycle_label=cycle.cycle_label,
                start_date=cycle.start_date,
                end_date=cycle.end_date,
                progress=cycle.progress,
                user_id=user_id
            )
            db.add(db_cycle)
            db.flush()  # Get cycle.id

            # Add occurrences for this cycle
            for occurrence in cycle.occurrences:
                db_occurrence = GoalOccurrence(
                    cycle_id=db_cycle.id,
                    plan_id=db_plan.id,  # Link to the plan
                    occurrence_order=occurrence.occurrence_order,
                    estimated_effort=occurrence.estimated_effort,
                    user_id=user_id
                )
                db.add(db_occurrence)
                db.flush()  # Get occurrence.id

                # Add tasks to the occurrence
                for task in occurrence.tasks:
                    db_task = Task(
                        title=task.title,
                        due_date=task.due_date,
                        estimated_time=task.estimated_time,
                        completed=task.completed,
                        plan_id=db_plan.id,  # Link to Plan
                        goal_id=db_goal.id,  # Also link to Goal for queries
                        cycle_id=db_cycle.id,  # Link to Cycle
                        occurrence_id=db_occurrence.id,  # Link to Occurrence
                        user_id=user_id
                    )
                    db.add(db_task)

    # ✅ Add project tasks (for project and hybrid plans)
    if plan_data.tasks:
        for task in plan_data.tasks:
            db_task = Task(
                title=task.title,
                due_date=task.due_date,
                estimated_time=task.estimated_time,
                completed=task.completed,
                plan_id=db_plan.id,  # Link to Plan
                goal_id=db_goal.id,  # Also link to Goal for queries
                user_id=user_id
            )
            db.add(db_task)

    # ✅ Commit all changes
    db.commit()
    
    return db_plan

# ------------------------------------------------

def generate_refined_plan_from_feedback(
        db: Session,
        plan_id: int,
        feedback_text: str,
        suggested_changes: str) -> dict:
    """Generate a refined plan based on user feedback using LangChain."""
    try:
        logger.info(f"Starting refinement for plan {plan_id}")

        # ✅ Load the plan with proper relationships (Plan-centric approach)
        plan = db.query(Plan).options(
            selectinload(Plan.goal),
            selectinload(Plan.tasks),
            selectinload(Plan.cycles).selectinload(HabitCycle.occurrences).selectinload(GoalOccurrence.tasks)
        ).filter(Plan.id == plan_id).first()
        
        if not plan:
            raise ValueError(f"Plan with ID {plan_id} not found")
        
        logger.info(f"Plan loaded: {plan.id}, Goal ID: {plan.goal_id}, User ID: {plan.user_id}")

        # ✅ Get goal metadata (lightweight)
        goal = plan.goal
        if not goal:
            raise ValueError(f"Goal not found for plan {plan_id}")

        logger.info(f"Goal loaded: {goal.id}, Plan Type: {plan.goal_type}, User ID: {goal.user_id}")
        
        # ✅ Format existing tasks (from Plan, not Goal)
        formatted_tasks = []
        for task in plan.tasks:
            formatted_tasks.append(f"- {task.title} (Due: {task.due_date or 'No due date'})")
        formatted_tasks = "\n".join(formatted_tasks) if formatted_tasks else "No tasks available."
        
        # ✅ Add recurrence cycles if applicable (habit or hybrid plans)
        formatted_cycles = ""
        recurrence_info = ""
        if plan.goal_type in [GoalType.habit, GoalType.hybrid]:
            # Get habit-specific info from Plan (not from old polymorphic classes)
            recurrence_info = f"Frequency: {plan.goal_frequency_per_cycle or 'Not specified'}"
            recurrence_info += f", Recurrence Count: {plan.goal_recurrence_count or 'Not specified'}"
            recurrence_info += f", Cycle: {plan.recurrence_cycle or 'Not specified'}"

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
            recurrence_info = "Not applicable (Project Goal)"
            
        # ✅ Assemble previous plan content (Plan-centric data)
        previous_plan_content = f"""
        --- Previous Plan (Plan-Centric Structure) ---
        Goal Title: {goal.title}
        Goal Description: {goal.description or 'No description provided.'}
        Plan Type: {plan.goal_type.value.capitalize()}
        Plan ID: {plan.id}
        Goal ID: {goal.id}
        User ID: {plan.user_id}
        Start Date: {plan.start_date or 'Not specified'}
        End Date: {plan.end_date or 'Not specified'}
        Progress: {plan.progress}%

        Recurrence Information: {recurrence_info}

        Tasks:
        {formatted_tasks}

        Cycles:
        {formatted_cycles if formatted_cycles else 'No cycles available.'}

        --- End of Previous Plan ---
        """.strip()

        logger.info(f"Refining plan {plan_id} with feedback: {feedback_text} and suggested changes: {suggested_changes}")
        
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

        logger.info("------ [DEBUG] Prior Feedback Combined ------")
        logger.info(prior_feedback_combined)
        logger.info("------ [DEBUG] End of Prior Feedback Combined ------")

        # ✅ 5. Prepare source plan data for field completion (Plan-centric)
        from app.DEPRECATED.DEPRECATED_ai.goal_parser_chain import robust_refine_plan
        
        source_plan_data = {
            "goal_id": goal.id,
            "plan_id": plan.id,
            "title": goal.title,
            "description": goal.description,
            "goal_type": plan.goal_type.value,
            "start_date": plan.start_date,
            "end_date": plan.end_date,
            "progress": plan.progress,
        }

        # Add goal-type specific fields
        if plan.goal_type in [GoalType.habit, GoalType.hybrid]:
            source_plan_data.update({
                "goal_recurrence_count": plan.goal_recurrence_count,
                "goal_frequency_per_cycle": plan.goal_frequency_per_cycle,
                "recurrence_cycle": plan.recurrence_cycle,
                "default_estimated_time_per_cycle": plan.default_estimated_time_per_cycle,
                "habit_cycles": [
                    {
                        "cycle_label": cycle.cycle_label,
                        "start_date": cycle.start_date,
                        "end_date": cycle.end_date,
                        "progress": cycle.progress,
                        "occurrences": [
                            {
                                "occurrence_order": occ.occurrence_order,
                                "estimated_effort": occ.estimated_effort,
                                "tasks": [
                                    {
                                        "title": task.title,
                                        "due_date": task.due_date,
                                        "estimated_time": task.estimated_time,
                                        "completed": task.completed
                                    } for task in occ.tasks
                                ]
                            } for occ in cycle.occurrences
                        ]
                    } for cycle in plan.cycles
                ]
            })

        if plan.goal_type in [GoalType.project, GoalType.hybrid]:
            source_plan_data.update({
                "tasks": [
                    {
                        "title": task.title,
                        "due_date": task.due_date,
                        "estimated_time": task.estimated_time,
                        "completed": task.completed
                    } for task in plan.tasks if not task.cycle_id  # Only project tasks (not cycle tasks)
                ]
            })
        
        try:
            # Try robust refinement first
            refined_plan_data = robust_refine_plan(
                goal_description=goal.description or goal.title,
                previous_plan_content=previous_plan_content,
                prior_feedback=prior_feedback_combined,
                source_plan_data=source_plan_data
            )
            result = {"plan": refined_plan_data}
            logger.info("🔄 Robust refinement successful: %s", refined_plan_data)

        except Exception as e:
            print(f"Robust refinement failed, falling back to original chain: {e}")
            # Fallback to original chain
            from app.DEPRECATED.DEPRECATED_ai.goal_parser_chain import refine_plan_chain
            result = refine_plan_chain.invoke({
                "goal_description": goal.description or goal.title,
                "previous_plan": previous_plan_content,
                "prior_feedback": prior_feedback_combined
            })
        
        print(f"Plan user_id: {plan.user_id}, type: {type(plan.user_id)}")
        print(f"Plan id: {plan.id}, type: {type(plan.id)}")
        
        # ✅ Parse the refined plan and save it
        if result and isinstance(result, dict) and 'plan' in result:
            refined_plan_data = result['plan']
            print(f"Refined plan data: {refined_plan_data}")
            print(f"Refined plan data type: {type(refined_plan_data)}")
            
            # Save the refined plan with source plan reference
            from typing import cast
            user_id_val = cast(int, plan.user_id)  
            plan_id_val = cast(int, plan.id)
            
            refined_plan_saved = save_generated_plan(
                plan=refined_plan_data,
                db=db,
                user_id=user_id_val,
                source_plan_id=plan_id_val
            )
            
            print(f"Refined plan saved with ID: {refined_plan_saved.id}")
            # Return both the saved plan and the original GeneratedPlan
            return {"saved_plan": refined_plan_saved, "generated_plan": refined_plan_data}
        else:
            print(f"Unexpected result structure. Result: {result}")
            print(f"Result keys: {result.keys() if isinstance(result, dict) else 'Not a dict'}")
            raise ValueError("Failed to generate refined plan from LangChain")
            
    except Exception as e:
        print(f"Error in generate_refined_plan_from_feedback: {e}")
        raise e
