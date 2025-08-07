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
from app.models import GoalType, HabitCycle, GoalOccurrence, Task, PlanFeedbackAction, Plan

# ✅ CONFIGURATION: Display limits for task summaries
MAX_DISPLAY_TASKS_PROJECT = 5  # Show up to 5 tasks for project goals
MAX_DISPLAY_TASKS_HYBRID = 3   # Show up to 3 tasks for hybrid goals (to leave room for habit info)
MAX_DISPLAY_TASKS_DETAILS = 10 # Show up to 10 tasks in detailed view

logger = logging.getLogger(__name__)

@tool("generate_plan_with_ai")
def generate_plan_with_ai_tool(goal_prompt: str, user_id: int) -> str:
    """
    🎯 Tool: Generate a structured goal + task plan from a natural language description and save it to database.
    
    This tool generates AND saves the plan in one step - no separate saving needed.
    
    🧠 **Usage Context:**
    - When user describes a new goal they want to achieve
    - For converting abstract goals into actionable plans
    - Supports project goals (one-time), habit goals (recurring), and hybrid goals (both)
    
    🎯 **Example Usage Phrases:**
    - "I want to learn Python programming in 6 months"
    - "I want to exercise 3 times per week"
    - "Help me plan to read 24 books this year"
    - "I want to build a mobile app and maintain a coding habit"
    
    ⚠️ **Important Notes:**
    - This tool automatically saves the plan to database
    - Returns plan ID for future reference
    - Handles all three goal types: project, habit, hybrid
    - AI determines goal type based on user description

    **Parameters:**
    - goal_prompt: Natural language goal description (e.g. "I want to learn Python")
    - user_id: The user ID to associate with the plan

    **Returns:**
    A formatted string containing the plan details and confirmation of saving.
    """
    logger.info("🔧 TOOL EXECUTION: generate_plan_with_ai_tool started")
    logger.info(f"📝 TOOL INPUT: goal_prompt='{goal_prompt[:100]}...' (length={len(goal_prompt)}), user_id={user_id}")
    
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
        plan = response.plan.plan
        
        # Extract tasks information
        tasks_info = ""
        if plan.goal_type.value == "project" and plan.tasks:
            tasks_list = []
            for i, task in enumerate(plan.tasks[:MAX_DISPLAY_TASKS_PROJECT], 1):  # ✅ Use configurable limit
                due_date = task.due_date.strftime("%Y-%m-%d") if task.due_date else "No due date"
                time_str = f" ({task.estimated_time} min)" if task.estimated_time else ""
                tasks_list.append(f"{i}. {task.title}{time_str} - Due: {due_date}")
            tasks_info = "\n".join(tasks_list)
            if len(plan.tasks) > MAX_DISPLAY_TASKS_PROJECT:
                tasks_info += f"\n... and {len(plan.tasks) - MAX_DISPLAY_TASKS_PROJECT} more tasks"
                
        elif plan.goal_type.value == "habit" and plan.habit_cycles:
            # For habits, show cycle and frequency info
            cycle_info = []
            cycle_info.append(f"📅 Schedule: {plan.recurrence_cycle}")
            cycle_info.append(f"🔄 Frequency: {plan.goal_frequency_per_cycle} times per {plan.recurrence_cycle}")
            if plan.default_estimated_time_per_cycle:
                cycle_info.append(f"⏱️ Time per session: {plan.default_estimated_time_per_cycle} minutes")
            tasks_info = "\n".join(cycle_info)
            
        elif plan.goal_type.value == "hybrid":
            # For hybrid goals, show both project tasks and habit cycles
            hybrid_info = []
            
            # Show project component
            if plan.tasks:
                hybrid_info.append("📋 Project Tasks:")
                for i, task in enumerate(plan.tasks[:MAX_DISPLAY_TASKS_HYBRID], 1):  # ✅ Use configurable limit
                    due_date = task.due_date.strftime("%Y-%m-%d") if task.due_date else "No due date"
                    time_str = f" ({task.estimated_time} min)" if task.estimated_time else ""
                    hybrid_info.append(f"  {i}. {task.title}{time_str} - Due: {due_date}")
                if len(plan.tasks) > MAX_DISPLAY_TASKS_HYBRID:
                    hybrid_info.append(f"  ... and {len(plan.tasks) - MAX_DISPLAY_TASKS_HYBRID} more tasks")
                hybrid_info.append("")
            
            # Show habit component
            if plan.habit_cycles:
                hybrid_info.append("🔄 Habit Component:")
                hybrid_info.append(f"  📅 Schedule: {plan.recurrence_cycle}")
                hybrid_info.append(f"  🔄 Frequency: {plan.goal_frequency_per_cycle} times per {plan.recurrence_cycle}")
                if plan.default_estimated_time_per_cycle:
                    hybrid_info.append(f"  ⏱️ Time per session: {plan.default_estimated_time_per_cycle} minutes")
            
            tasks_info = "\n".join(hybrid_info)
        
        # Format timeline
        timeline = f"{plan.start_date}"
        if plan.end_date:
            timeline += f" to {plan.end_date}"
        
        result = {
            "plan_title": goal.title,
            "goal_type": plan.goal_type.value,
            "goal_description": goal.description,
            "timeline": timeline,
            "tasks_info": tasks_info,
            "user_id": response.user_id,
            "source": response.source,
            "status": "generated_and_saved",
            "message": f"✅ Created {plan.goal_type.value} goal: '{goal.title}' with detailed plan structure"
        }
        
        # Return a clear success message that the agent can understand
        return f"✅ PLAN SUCCESSFULLY CREATED AND SAVED!\n\nTitle: {goal.title}\nType: {plan.goal_type.value}\nDescription: {goal.description}\nTimeline: {timeline}\n\n{tasks_info}\n\nPlan ID: {response.plan.plan_id}"
        
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
    📋 Retrieve all plans (approved or not) created by the user.
    
    🧠 **Usage Context:**
    - When user wants to see their planning history
    - For reviewing previous attempts and iterations
    - To understand what goals they've worked on
    - For plan comparison and selection
    
    🎯 **Example Usage Phrases:**
    - "Show me all my plans"
    - "What plans have I created?"
    - "List my goal planning history"
    - "What have I been working on?"
    
    ⚠️ **Important Notes:**
    - Shows ALL plans including drafts and refinements
    - Includes both approved and pending plans
    - Useful for context when creating related goals
    - Each plan shows goal title, type, and progress

    **Args:**
        user_id (int): ID of the user

    **Returns:**
        str: List of all plans with their goal titles, types, and statuses
    """
    try:
        from app.db import SessionLocal
        from app.crud import crud

        db = SessionLocal()

        logger.info(f"🔧 TOOL EXECUTION: get_user_plans for user_id={user_id}")
        logger.info(f"📝 TOOL CONTEXT: Retrieving all plans (approved + drafts)")

        plans = crud.get_plans_by_user(db, user_id=user_id)

        if not plans:
            logger.warning(f"No plans found for user {user_id}")
            return "No plans found for this user."

        lines = []
        for plan in plans:
            goal = plan.goal
            if goal:
                lines.append(f"- Plan ID {plan.id}: '{goal.title}' ({plan.goal_type.value}, Progress: {plan.progress}%)")

        logger.info(f"✅ TOOL SUCCESS: Retrieved {len(plans)} total plans for user {user_id}")
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"❌ TOOL ERROR: get_user_plans failed for user {user_id}: {str(e)}")
        return f"❌ Error retrieving plans: {str(e)}"
    finally:
        db.close()

@tool("get_user_approved_plans")
def get_user_approved_plans(user_id: int) -> str:
    """
    ✅ Retrieve the user's currently approved and active plans.
    
    🧠 **Usage Context:**
    - When user asks about their current commitments
    - For checking what they should be working on now
    - To avoid goal conflicts and over-commitment
    - For progress tracking and status updates
    
    🎯 **Example Usage Phrases:**
    - "What am I currently working on?"
    - "What's my active plan?"
    - "Show me my approved goals"
    - "What should I be doing now?"
    - "What plans am I committed to?"
    
    ⚠️ **Important Notes:**
    - Only shows APPROVED plans (user has confirmed commitment)
    - These are the goals user should actively work on
    - Excludes drafts and pending refinements
    - Only one plan per goal can be approved at a time

    **Args:**
        user_id (int): ID of the user

    **Returns:**
        str: List of approved plans with associated goal titles, types, and progress
    """
    try:
        from app.db import SessionLocal
        from app.crud import crud

        db = SessionLocal()

        logger.info(f"🔧 TOOL EXECUTION: get_user_approved_plans for user_id={user_id}")
        logger.info(f"📝 TOOL CONTEXT: Retrieving APPROVED plans only")
        plans = crud.get_approved_plans_by_user(db, user_id=user_id)

        if not plans:
            logger.warning(f"No approved plans found for user {user_id}")
            return "No approved plans found for this user."

        lines = []
        for plan in plans:
            goal = plan.goal
            if goal:
                lines.append(f"- Approved Plan ID {plan.id}: '{goal.title}' ({plan.goal_type.value}, Progress: {plan.progress}%)")

        logger.info(f"✅ TOOL SUCCESS: Retrieved {len(plans)} approved plans for user {user_id}")
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"❌ TOOL ERROR: get_user_approved_plans failed for user {user_id}: {str(e)}")
        return f"❌ Error retrieving approved plans: {str(e)}"
    finally:
        db.close()

def _plan_feedback_helper(plan_id: int, feedback_text: str, action: str, user_id: int, suggested_changes: Optional[str] = None) -> dict:
    """
    Helper function to handle plan feedback without LangChain tool decorators.
    This allows us to call it from other tools without issues.
    """
    logger.info("🔧 HELPER: _plan_feedback_helper started")
    logger.info(f"📝 HELPER INPUT: plan_id={plan_id}, action='{action}', user_id={user_id}")
    logger.info(f"📝 HELPER CONTEXT: feedback_text length={len(feedback_text)}, has_suggestions={suggested_changes is not None}")
    
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
                refined_plan_structure = response.refined_plan.plan
                result["refined_plan_title"] = refined_goal.title
                result["refined_plan_type"] = refined_plan_structure.goal_type.value
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
    🔧 Tool: Submit feedback on a generated plan - either approve it or request refinement.
    
    🧠 **Usage Context:**
    - After user reviews a generated plan
    - When user wants to approve a plan for execution
    - When user wants modifications before approval
    - For iterative plan improvement workflow
    
    🎯 **Example Usage Phrases:**
    - "Approve this plan" → action="approve"
    - "This looks good, let's go with it" → action="approve"  
    - "Can you make the timeline shorter?" → action="refine"
    - "Add more detail to the tasks" → action="refine"
    - "I want to change the frequency" → action="refine"
    
    ⚠️ **Important Notes:**
    - Approval sets is_approved=True and deactivates other plans for same goal
    - Refinement creates a new plan version with improvements
    - Feedback is stored for plan history tracking
    - Only one plan per goal can be approved at a time
    
    **Parameters:**
    - plan_id: ID of the plan to provide feedback on
    - feedback_text: The user's feedback about the plan
    - action: Either "approve" or "refine" 
    - user_id: The user ID submitting feedback
    - suggested_changes: Optional specific changes requested (used for refinement)
    
    **Returns:**
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
    🧠 SMART plan details tool that handles multiple scenarios using existing CRUD functions.
    
    🎯 **Example Usage Phrases:**
    - "Show me plan 123 details" (specific plan_id)
    - "Show me the plan you just created" (latest plan)
    - "Tell me about my latest plan" (latest plan)
    - "What's in the plan we just made?" (latest plan)
    - "Give me full details of my current plan"
    
    🧠 **Usage Context:**
    - When user wants comprehensive plan information
    - After creating a plan and wanting to review it
    - For checking task lists, habits, cycles, and progress
    - Smart detection: if no plan_id provided, shows latest plan
    
    ⚠️ **Important Notes:**
    - Automatically finds latest plan if plan_id not specified
    - Shows different details based on goal type (project/habit/hybrid)
    - Includes hierarchical structure: cycles → occurrences → tasks
    - Only shows plans belonging to the requesting user
    
    **Args:**
        user_id (int): ID of the user
        plan_id (Optional[int]): Specific plan ID, or None for latest plan
        
    **Returns:**
        str: Detailed plan information with task lists, habit cycles, and progress
    """
    try:
        from app.db import SessionLocal
        from app.crud.crud import get_plan_by_id, get_plans_by_user  # ✅ USE EXISTING CRUD!
        
        db = SessionLocal()
        logger.info(f"🔧 TOOL EXECUTION: get_plan_details_smart for user_id={user_id}, plan_id={plan_id}")
        logger.info(f"📝 TOOL CONTEXT: {'Latest plan mode' if plan_id is None else 'Specific plan mode'}")
        
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
        goal_type_emoji = "🎯" if plan.goal_type.value == "project" else "🔄"
        
        response_parts = [
            f"{status_emoji} **Detailed Plan Information**",
            "",
            f"**📝 Plan ID:** {plan.id}",
            f"**📝 Title:** {goal.title}",
            f"**📋 Type:** {plan.goal_type.value.title()} Goal", 
            f"**📖 Description:** {goal.description or 'No description provided'}",
            f"**📅 Timeline:** {plan.start_date} to {plan.end_date or 'Ongoing'}",
            f"**📊 Progress:** {plan.progress}%",
            f"**🔄 Refinement Round:** {plan.refinement_round or 0}",
            f"**✅ Status:** {'Approved' if is_approved else 'Pending Review'}",
            ""
        ]
        
        # Add task details for project goals using existing database models
        if plan.goal_type.value == "project":
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
        elif plan.goal_type.value == "habit":
            # Get the habit goal details from the plan itself (Plan-centric)
            response_parts.append(f"**🔄 Habit Details:**")
            response_parts.append(f"• **Recurrence:** {plan.recurrence_cycle}")
            response_parts.append(f"• **Frequency:** {plan.goal_frequency_per_cycle} times per {plan.recurrence_cycle}")
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
                
        # ✅ FIX: Add complete hierarchical details for hybrid goals
        elif plan.goal_type.value == "hybrid":
            # Get both project and habit components
            # First show project tasks
            tasks = db.query(Task).filter(Task.goal_id == goal.id).order_by(Task.due_date).all()
            if tasks:
                response_parts.append("**📋 Project Tasks:**")
                for i, task in enumerate(tasks, 1):
                    due_date = task.due_date.strftime("%Y-%m-%d") if task.due_date is not None else "No due date"
                    time_str = f" ({task.estimated_time} min)" if task.estimated_time is not None else ""
                    task_completed = getattr(task, 'completed', False) or False
                    status = "✅" if task_completed else "⭕"
                    response_parts.append(f"{i}. {status} {task.title}{time_str} - Due: {due_date}")
                response_parts.append("")
            else:
                response_parts.append("**📋 Project Tasks:** No tasks created yet")
                response_parts.append("")
            
            # Then show habit details from plan (Plan-centric architecture)
            if plan:
                response_parts.append(f"**🔄 Habit Component:**")
                response_parts.append(f"• **Recurrence:** {plan.recurrence_cycle}")
                response_parts.append(f"• **Frequency:** {plan.goal_frequency_per_cycle} times per {plan.recurrence_cycle}")
                response_parts.append("")
                
                # Get all cycles for this hybrid goal's habit component
                cycles = db.query(HabitCycle).filter(HabitCycle.habit_id == goal.id).order_by(HabitCycle.start_date).all()
                if cycles:
                    response_parts.append(f"**📅 Habit Cycles ({len(cycles)} cycles):**")
                    for cycle in cycles:
                        response_parts.append(f"")
                        response_parts.append(f"📅 **Cycle: {cycle.cycle_label}**")
                        response_parts.append(f"   📊 **Target:** {cycle.target_occurrences} occurrences")
                        response_parts.append(f"   ✅ **Completed:** {cycle.completed_occurrences}")
                        response_parts.append(f"   📈 **Progress:** {cycle.completion_percentage}%")
                        response_parts.append(f"   📅 **Period:** {cycle.start_date.strftime('%Y-%m-%d')} to {cycle.end_date.strftime('%Y-%m-%d')}")
                        
                        # Get occurrences for this cycle using GoalOccurrence
                        occurrences = db.query(GoalOccurrence).filter(GoalOccurrence.cycle_id == cycle.id).order_by(GoalOccurrence.scheduled_date).all()
                        if occurrences:
                            response_parts.append(f"   🎯 **Occurrences ({len(occurrences)}):**")
                            for occ in occurrences:
                                completed_status = "✅" if getattr(occ, 'completed', False) else "⭕"
                                scheduled_date = occ.scheduled_date.strftime("%Y-%m-%d") if occ.scheduled_date else "No date"
                                response_parts.append(f"     {completed_status} {scheduled_date}")
                        else:
                            response_parts.append(f"   🎯 **Occurrences:** None created")
                else:
                    response_parts.append("**📅 Habit Cycles:** No cycles created yet")
            else:
                response_parts.append("**🔄 Habit Component:** No habit details found")
        
        response_parts.append("")
        response_parts.append("💡 **Need help?**")
        response_parts.append("• Ask me to refine this plan")
        response_parts.append("• Request adjustments to timing or tasks")
        response_parts.append("• Create additional goals")
        
        logger.info(f"✅ TOOL SUCCESS: Generated plan details for plan_id={plan.id}, goal_type={plan.goal_type.value}")
        return "\n".join(response_parts)
        
    except Exception as e:
        logger.error(f"❌ TOOL ERROR: get_plan_details_smart failed for user {user_id}, plan_id={plan_id}: {str(e)}")
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
