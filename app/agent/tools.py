# app/agent/tools.py

from langchain_core.tools import tool
from app.crud.planner import save_generated_plan
from app.ai.schemas import GeneratedPlan, GoalDescriptionRequest, AIPlanResponse, PlanFeedbackRequest, PlanFeedbackResponse
from sqlalchemy.orm import Session
from app.db import SessionLocal, get_db
from typing import Optional
import logging
from datetime import date, datetime
from app.ai.goal_parser_chain import goal_parser_chain, parser
from app.crud import planner
from app.routers.planning import generate_plan_from_ai, plan_feedback  # ✅ Import existing functions
from app.models import GoalType, HabitGoal, HabitCycle, GoalOccurrence, Task, PlanFeedbackAction

logger = logging.getLogger(__name__)

@tool("generate_plan_with_ai")
def generate_plan_with_ai_tool(goal_prompt: str, user_id: int) -> str:
    """
    Tool: Generate a structured goal + task plan from a natural language description and save it to database.
    
    This tool generates AND saves the plan in one step - no separate saving needed.

    Parameters:
    - goal_prompt: Natural language goal description (e.g. "I want to learn Python").
    - user_id: The user ID to associate with the plan.

    Returns:
    A dictionary containing the plan details and confirmation of saving.
    """
    logger.info("🔧 TOOL EXECUTION: generate_plan_with_ai_tool started")
    logger.info(f"📝 TOOL INPUT: goal_prompt='{goal_prompt}', user_id={user_id}")
    
    try:
        # Create a database session
        db = SessionLocal()
        
        # Create the request object that the existing function expects
        request = GoalDescriptionRequest(
            goal_description=goal_prompt,
            user_id=user_id
        )
        
        logger.info("🔄 TOOL: Calling existing generate_plan_from_ai function")
        
        # Call the existing, tested function
        response: AIPlanResponse = generate_plan_from_ai(request=request, db=db)
        
        logger.info(f"✅ TOOL SUCCESS: Plan generated and saved for user {user_id}")
        
        # Convert the response to a dict format that the LLM can understand
        goal = response.plan.goal
        
        # Extract tasks information
        tasks_info = ""
        if goal.goal_type == "project" and goal.tasks:
            tasks_list = []
            for i, task in enumerate(goal.tasks[:5], 1):  # Show first 5 tasks
                due_date = task.due_date.strftime("%Y-%m-%d") if task.due_date else "No due date"
                time_str = f" ({task.estimated_time} min)" if task.estimated_time else ""
                tasks_list.append(f"{i}. {task.title}{time_str} - Due: {due_date}")
            tasks_info = "\n".join(tasks_list)
            if len(goal.tasks) > 5:
                tasks_info += f"\n... and {len(goal.tasks) - 5} more tasks"
                
        elif goal.goal_type == "habit" and goal.habit_cycles:
            # For habits, show cycle and frequency info
            cycle_info = []
            cycle_info.append(f"📅 Schedule: {goal.recurrence_cycle}")
            cycle_info.append(f"🔄 Frequency: {goal.goal_frequency_per_cycle} times per {goal.recurrence_cycle}")
            if goal.default_estimated_time_per_cycle:
                cycle_info.append(f"⏱️ Time per session: {goal.default_estimated_time_per_cycle} minutes")
            tasks_info = "\n".join(cycle_info)
        
        # Format timeline
        timeline = f"{goal.start_date}"
        if goal.end_date:
            timeline += f" to {goal.end_date}"
        
        result = {
            "plan_title": goal.title,
            "goal_type": goal.goal_type,
            "goal_description": goal.description,
            "timeline": timeline,
            "tasks_info": tasks_info,
            "user_id": response.user_id,
            "source": response.source,
            "status": "generated_and_saved",
            "message": f"✅ Created {goal.goal_type} goal: '{goal.title}' with detailed plan structure"
        }
        
        # Return a clear success message that the agent can understand
        return f"✅ PLAN SUCCESSFULLY CREATED AND SAVED!\n\nTitle: {goal.title}\nType: {goal.goal_type}\nDescription: {goal.description}\nTimeline: {timeline}\n\n{tasks_info}\n\nPlan ID: {response.plan.plan_id}"
        
    except Exception as e:
        logger.error(f"❌ TOOL ERROR: generate_plan_with_ai_tool failed: {str(e)}")
        error_msg = str(e)
        # Return a clear error message that the agent can understand
        return f"❌ TOOL FAILED: {error_msg}\n\nThe plan could not be created. Please ask the user for more specific details about their goal."
    finally:
        if 'db' in locals():
            db.close()
            logger.info("💾 TOOL: Database session closed")

@tool("get_user_plans")
def get_user_plans(user_id: int) -> str:
    """
    Retrieve all plans (approved or not) created by the user.

    Use this when the user wants to see all the plans they've worked on, including drafts and refinements.
    This gives context for previous attempts and decisions made in goal planning.

    Args:
        user_id (int): ID of the user

    Returns:
        str: List of all plans with their goal titles and statuses
    """
    try:
        from app.db import SessionLocal
        from app.crud import crud

        db = SessionLocal()

        logger.info(f"Retrieving plans for user {user_id}")

        plans = crud.get_plans_by_user(db, user_id=user_id)

        if not plans:
            logger.warning(f"No plans found for user {user_id}")
            return "No plans found for this user."

        lines = []
        for plan in plans:
            goal = plan.goal
            if goal:
                lines.append(f"- Plan ID {plan.id}: '{goal.title}' ({goal.goal_type}, Progress: {goal.progress}%)")

        logger.info(f"Retrieved {len(plans)} plans for user {user_id}")
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Error retrieving plans: {str(e)}")
        return f"❌ Error retrieving plans: {str(e)}"
    finally:
        db.close()

@tool("get_user_approved_plans")
def get_user_approved_plans(user_id: int) -> str:
    """
    Retrieve the user's currently approved and active plans.

    Use this when the user asks "what am I currently working on?" or "what's my active plan?"
    This only returns plans that are marked as approved and are considered current.

    Args:
        user_id (int): ID of the user

    Returns:
        str: List of approved plans with associated goal titles
    """
    try:
        from app.db import SessionLocal
        from app.crud import crud

        db = SessionLocal()

        logger.info(f"Retrieving approved plans for user {user_id}")
        plans = crud.get_approved_plans_by_user(db, user_id=user_id)

        if not plans:
            logger.warning(f"No approved plans found for user {user_id}")
            return "No approved plans found for this user."

        lines = []
        for plan in plans:
            goal = plan.goal
            if goal:
                lines.append(f"- Approved Plan ID {plan.id}: '{goal.title}' ({goal.goal_type}, Progress: {goal.progress}%)")

        logger.info(f"Retrieved {len(plans)} approved plans for user {user_id}")
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Error retrieving approved plans: {str(e)}")
        return f"❌ Error retrieving approved plans: {str(e)}"
    finally:
        db.close()

def _plan_feedback_helper(plan_id: int, feedback_text: str, action: str, user_id: int, suggested_changes: Optional[str] = None) -> dict:
    """
    Helper function to handle plan feedback without LangChain tool decorators.
    This allows us to call it from other tools without issues.
    """
    logger.info("🔧 HELPER: _plan_feedback_helper started")
    
    try:
        # Create a database session
        db = SessionLocal()
        
        # Convert action string to PlanFeedbackAction enum
        if action.lower() == "approve":
            feedback_action = PlanFeedbackAction.APPROVE
        elif action.lower() == "refine":
            feedback_action = PlanFeedbackAction.REQUEST_REFINEMENT
        else:
            return {
                "error": f"Invalid action '{action}'. Must be 'approve' or 'refine'",
                "status": "failed",
                "message": "Invalid feedback action provided"
            }
        
        # Get the plan first to extract goal_id
        from app.crud import crud
        plan = crud.get_plan_by_id(db, plan_id)
        if not plan:
            return {
                "error": f"Plan {plan_id} not found",
                "status": "failed",
                "message": f"Plan {plan_id} not found"
            }
        
        # Create the request object that the existing function expects  
        request = PlanFeedbackRequest(
            plan_id=plan_id,
            goal_id=plan.goal_id,  # type: ignore  # SQLAlchemy runtime value vs Column type
            feedback_text=feedback_text,
            plan_feedback_action=feedback_action,
            user_id=user_id,
            suggested_changes=suggested_changes,
            timestamp=datetime.now()
        )
        
        logger.info("🔄 HELPER: Calling existing plan_feedback function")
        
        # Call the existing, tested function
        response: PlanFeedbackResponse = plan_feedback(request=request, db=db)
        
        logger.info(f"✅ HELPER SUCCESS: Feedback processed for plan {plan_id}")
        
        # Convert the response to a dict format
        result = {
            "message": response.message,
            "feedback": response.feedback,
            "plan_id": response.plan_id,
            "action": response.plan_feedback_action.value,
            "goal_id": response.goal_id,
            "status": "success"
        }
        
        # If a refined plan was created, include those details
        if response.refined_plan_id:
            result["refined_plan_id"] = response.refined_plan_id
            result["refinement_created"] = True
            
            # Extract key details from the refined plan
            if response.refined_plan:
                refined_goal = response.refined_plan.goal
                result["refined_plan_title"] = refined_goal.title
                result["refined_plan_type"] = refined_goal.goal_type
                result["refined_plan_description"] = refined_goal.description
        else:
            result["refinement_created"] = False
        
        return result
        
    except Exception as e:
        logger.error(f"❌ HELPER ERROR: _plan_feedback_helper failed: {str(e)}")
        return {
            "error": str(e),
            "status": "failed",
            "message": f"Failed to process feedback: {str(e)}"
        }
    finally:
        if 'db' in locals():
            db.close()
            logger.info("💾 HELPER: Database session closed")

@tool("plan_feedback")
def plan_feedback_tool(plan_id: int, feedback_text: str, action: str, user_id: int, suggested_changes: Optional[str] = None) -> dict:
    """
    Tool: Submit feedback on a generated plan - either approve it or request refinement.
    
    This tool wraps the existing backend plan_feedback logic and handles:
    - Plan approval (sets is_approved=True and sets other plans' is_approved=False, manages business rules)
    - Plan refinement (aggregates feedback history, generates refined plan)
    
    Parameters:
    - plan_id: ID of the plan to provide feedback on
    - feedback_text: The user's feedback about the plan
    - action: Either "approve" or "refine" 
    - user_id: The user ID submitting feedback
    - suggested_changes: Optional specific changes requested (used for refinement)
    
    Returns:
    A dictionary containing the feedback result and any refined plan details.
    """
    return _plan_feedback_helper(plan_id, feedback_text, action, user_id, suggested_changes)

@tool("refine_existing_plan")
def refine_existing_plan(plan_id: int, user_feedback: str, user_id: int) -> str:
    """
    DEPRECATED: Use plan_feedback_tool with action='refine' instead.
    
    This tool is kept for backward compatibility but plan_feedback_tool is preferred
    as it follows the complete backend logic including feedback history aggregation.
    """
    logger.warning("⚠️ DEPRECATED: refine_existing_plan called. Use plan_feedback_tool instead.")
    
    # Call the helper function directly
    result = _plan_feedback_helper(
        plan_id=plan_id,
        feedback_text=user_feedback,
        action="refine",
        user_id=user_id
    )
    
    if result.get("status") == "success":
        if result.get("refinement_created"):
            return f"✅ {result['message']} New plan ID: {result.get('refined_plan_id')}"
        else:
            return f"✅ {result['message']}"
    else:
        return f"❌ {result.get('message', 'Unknown error')}"


@tool("get_plan_details_smart")
def get_plan_details_smart(user_id: int, plan_id: Optional[int] = None) -> str:
    """
    SMART plan details tool that handles multiple scenarios using existing CRUD functions.
    
    Use this when user wants to see plan details, including:
    - "Show me plan X details" (specific plan_id)
    - "Show me the plan you just created" (latest plan)
    - "Tell me about my latest plan" (latest plan)
    - "What's in the plan we just made?" (latest plan)
    
    Args:
        user_id (int): ID of the user
        plan_id (Optional[int]): Specific plan ID, or None for latest plan
        
    Returns:
        str: Detailed plan information using existing CRUD functions
    """
    try:
        from app.db import SessionLocal
        from app.crud.crud import get_plan_by_id, get_plans_by_user  # ✅ USE EXISTING CRUD!
        
        db = SessionLocal()
        logger.info(f"SMART TOOL: Getting plan details for user {user_id}, plan_id={plan_id}")
        
        # ✅ SMART LOGIC: If no plan_id provided, get the latest plan
        if plan_id is None:
            logger.info("🧠 SMART: No plan_id provided, getting user's latest plan...")
            plans = get_plans_by_user(db, user_id)  # ✅ USE EXISTING CRUD!
            if not plans:
                return "❌ No plans found for this user."
            plan = plans[0]  # Latest plan (ordered by created_at desc)
            logger.info(f"🧠 SMART: Found latest plan ID {plan.id}")
        else:
            # ✅ USE EXISTING CRUD FUNCTION!
            plan = get_plan_by_id(db, plan_id)
            if plan is None or getattr(plan, "user_id", None) != user_id:
                return f"❌ Plan {plan_id} not found or doesn't belong to this user."
        
        # Get the associated goal
        goal = plan.goal
        if not goal:
            return f"❌ No goal found for plan {plan.id}"
        
        # Build response using the data we have (with proper null-safe checks)
        is_approved = getattr(plan, 'is_approved', False) or False
        status_emoji = "✅" if is_approved else "📋"
        goal_type_emoji = "🎯" if goal.goal_type == "project" else "🔄"
        
        response_parts = [
            f"{status_emoji} **Detailed Plan Information**",
            "",
            f"**📝 Plan ID:** {plan.id}",
            f"**📝 Title:** {goal.title}",
            f"**📋 Type:** {goal.goal_type.title()} Goal", 
            f"**📖 Description:** {goal.description or 'No description provided'}",
            f"**📅 Timeline:** {goal.start_date} to {goal.end_date or 'Ongoing'}",
            f"**📊 Progress:** {goal.progress}%",
            f"**🔄 Refinement Round:** {plan.refinement_round or 0}",
            f"**✅ Status:** {'Approved' if is_approved else 'Pending Review'}",
            ""
        ]
        
        # Add task details for project goals using existing database models
        if goal.goal_type == GoalType.project:
            tasks = db.query(Task).filter(Task.goal_id == goal.id).order_by(Task.due_date).all()
            if tasks:
                response_parts.append("**📋 Tasks:**")
                for i, task in enumerate(tasks, 1):
                    due_date = task.due_date.strftime("%Y-%m-%d") if task.due_date is not None else "No due date"
                    time_str = f" ({task.estimated_time} min)" if task.estimated_time is not None else ""
                    task_completed = getattr(task, 'completed', False) or False
                    status = "✅" if task_completed else "⭕"
                    response_parts.append(f"{i}. {status} {task.title}{time_str} - Due: {due_date}")
                response_parts.append("")
            else:
                response_parts.append("**📋 Tasks:** No tasks created yet")
                
        # ✅ FIX: Add complete hierarchical details for habit goals
        elif goal.goal_type == GoalType.habit:
            # Get the habit goal details
            habit_goal = db.query(HabitGoal).filter(HabitGoal.id == goal.id).first()
            if habit_goal:
                response_parts.append(f"**🔄 Habit Details:**")
                response_parts.append(f"• **Recurrence:** {habit_goal.recurrence_cycle}")
                response_parts.append(f"• **Frequency:** {habit_goal.goal_frequency_per_cycle} times per {habit_goal.recurrence_cycle}")
                response_parts.append("")
                
                # Get all cycles for this habit goal
                cycles = db.query(HabitCycle).filter(HabitCycle.habit_id == goal.id).order_by(HabitCycle.start_date).all()
                if cycles:
                    response_parts.append(f"**📅 Habit Cycles ({len(cycles)} cycles):**")
                    for cycle in cycles:
                        response_parts.append(f"")
                        response_parts.append(f"📅 **Cycle: {cycle.cycle_label}**")
                        response_parts.append(f"   📆 Period: {cycle.start_date} to {cycle.end_date}")
                        
                        # Get occurrences for this cycle
                        occurrences = db.query(GoalOccurrence).filter(GoalOccurrence.cycle_id == cycle.id).order_by(GoalOccurrence.occurrence_order).all()
                        if occurrences:
                            response_parts.append(f"   🎯 **Occurrences ({len(occurrences)}):**")
                            for occ in occurrences:
                                response_parts.append(f"")
                                response_parts.append(f"      🎯 **Occurrence #{occ.occurrence_order}**")
                                response_parts.append(f"         ⏱️ Estimated effort: {occ.estimated_effort} minutes")
                                
                                # Get tasks for this occurrence
                                tasks = db.query(Task).filter(Task.occurrence_id == occ.id).order_by(Task.due_date).all()
                                if tasks:
                                    response_parts.append(f"         📋 **Tasks:**")
                                    for task in tasks:
                                        response_parts.append(f"            • **{task.title}**")
                                        response_parts.append(f"              📅 Due: {task.due_date}")
                                        response_parts.append(f"              ⏱️ Time: {task.estimated_time} min")
                                else:
                                    response_parts.append(f"         📋 **Tasks:** None created")
                        else:
                            response_parts.append(f"   🎯 **Occurrences:** None created")
                else:
                    response_parts.append("**📅 Cycles:** No cycles created yet")
            else:
                response_parts.append("**🔄 Habit Details:** No habit details found")
        
        response_parts.append("")
        response_parts.append("💡 **Need help?**")
        response_parts.append("• Ask me to refine this plan")
        response_parts.append("• Request adjustments to timing or tasks")
        response_parts.append("• Create additional goals")
        
        return "\n".join(response_parts)
        
    except Exception as e:
        logger.error(f"Error getting plan details: {str(e)}")
        return f"❌ Error retrieving plan details: {str(e)}"
    finally:
        if 'db' in locals():
            db.close()


# Group the tools into a list - NOTE: save_generated_plan_tool_func REMOVED to prevent double-saving
all_tools = [
    get_user_plans,
    get_user_approved_plans,
    plan_feedback_tool,  # ✅ NEW: Complete feedback tool using backend logic
    refine_existing_plan,  # ✅ DEPRECATED: Kept for backward compatibility
    generate_plan_with_ai_tool,  # This tool now handles generation AND saving automatically
    get_plan_details_smart,  # ✅ SMART: Use existing CRUD + handle "latest plan" requests
]
