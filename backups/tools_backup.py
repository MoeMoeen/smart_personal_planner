# app/agent/tools.py

from langchain_core.tools import tool
from app.crud.planner import save_generated_plan
from app.ai.schemas import GeneratedPlan, GoalDescriptionRequest, AIPlanResponse
from sqlalchemy.orm import Session
from app.db.db import SessionLocal, get_db
from typing import Optional
from app.main import logging
from datetime import date
from app.ai.goal_parser_chain import goal_parser_chain, parser
from app.crud import planner
from app.routers.planning import generate_plan_from_ai  # ✅ Import the existing function

logger = logging.getLogger(__name__)

def run_ai_plan_generation_logic(goal_description: str, user_id: int, db: Session) -> dict:
    """
    Invokes the goal_parser_chain and saves the resulting plan to the DB.

    Returns:
        A dictionary with the structured plan and saved goal ID.
    """
    logger.info("🧠 LOGIC: Starting AI plan generation logic")
    logger.info(f"📝 LOGIC INPUT: goal_description='{goal_description}', user_id={user_id}")
    
    today = date.today().isoformat()
    logger.info(f"📅 LOGIC: Using today's date: {today}")

    logger.info("⚡ LOGIC: Invoking goal_parser_chain...")
    parsed_output = goal_parser_chain.invoke({
        "goal_description": goal_description,
        "format_instructions": parser.get_format_instructions(),
        "today_date": today
    })
    logger.info("✅ LOGIC: goal_parser_chain completed successfully")

    generated_plan: GeneratedPlan = parsed_output["plan"]
    logger.info(f"📋 LOGIC: Generated plan type: {type(generated_plan)}")
    logger.info(f"📊 LOGIC: Generated plan title: {getattr(generated_plan.goal, 'title', 'No title found')}")

    logger.info("💾 LOGIC: Saving generated plan to database...")
    saved_plan = planner.save_generated_plan(
        plan=generated_plan,
        db=db,
        user_id=user_id
    )
    logger.info(f"✅ LOGIC: Plan saved successfully with ID: {saved_plan.id}")

    result = {
        "plan": generated_plan,
        "goal_id": saved_plan.id
    }
    
    logger.info("🎯 LOGIC: AI plan generation logic completed")
    return result

@tool("generate_plan_with_ai")
def generate_plan_with_ai_tool(goal_prompt: str, user_id: int) -> dict:
    """
    Tool: Generate a structured goal + task plan from a natural language description.
    
    IMPORTANT: This tool ONLY generates the plan structure - it does NOT save to database.
    Use save_generated_plan tool separately to save the generated plan.

    Parameters:
    - goal_prompt: Natural language goal description (e.g. "I want to learn Python").
    - user_id: The user ID to associate with the plan.

    Returns:
    A dictionary containing the structured plan (NOT saved to DB yet).
    """
    logger.info("🔧 TOOL EXECUTION: generate_plan_with_ai_tool started")
    logger.info(f"📝 TOOL INPUT: goal_prompt='{goal_prompt}', user_id={user_id}")
    
    try:
        logger.info("🧠 LOGIC: Starting AI plan generation logic (generation only)")
        logger.info(f"� LOGIC INPUT: goal_description='{goal_prompt}', user_id={user_id}")
        
        today = date.today().isoformat()
        logger.info(f"📅 LOGIC: Using today's date: {today}")

        logger.info("⚡ LOGIC: Invoking goal_parser_chain...")
        parsed_output = goal_parser_chain.invoke({
            "goal_description": goal_prompt,
            "format_instructions": parser.get_format_instructions(),
            "today_date": today
        })
        logger.info("✅ LOGIC: goal_parser_chain completed successfully")

        generated_plan: GeneratedPlan = parsed_output["plan"]
        logger.info(f"📋 LOGIC: Generated plan type: {type(generated_plan)}")
        logger.info(f"📊 LOGIC: Generated plan title: {getattr(generated_plan.goal, 'title', 'No title found')}")

        result = {
            "plan": generated_plan,
            "user_id": user_id,
            "status": "generated_not_saved"
        }
        
        logger.info("🎯 LOGIC: AI plan generation completed (NOT saved to DB)")
        logger.info(f"✅ TOOL SUCCESS: Plan generated for user {user_id} - ready for saving")
        logger.info(f"📊 TOOL RESULT: {type(result)} with keys: {list(result.keys()) if isinstance(result, dict) else 'not a dict'}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ TOOL ERROR: generate_plan_with_ai_tool failed: {str(e)}")
        raise

def _save_generated_plan_logic(plan: dict, user_id: int, source_plan_id: Optional[int] = None) -> str:
    """Core logic for saving a generated plan."""
    try:
        db: Session = SessionLocal()
        parsed_plan = GeneratedPlan(**plan)  # validate and convert dict to Pydantic model
        saved = save_generated_plan(
            plan=parsed_plan,
            db=db,
            user_id=user_id,
            source_plan_id=source_plan_id
        )
        return f"Plan saved successfully with ID {saved.id}"
    except Exception as e:
        return f"Error saving plan: {str(e)}"

# Method 1: Using @tool decorator for save_generated_plan
@tool("save_generated_plan")
def save_generated_plan_tool_func(plan: dict, user_id: int, source_plan_id: Optional[int] = None) -> str:
    """
    Use this tool to save a structured plan (goal + tasks) generated by the AI into the database.
    
    IMPORTANT SCHEMA REQUIREMENTS:
    - goal.goal_type: Must be "habit" or "project" (use "goal_type", NOT "type")
    - goal.start_date: Must be in YYYY-MM-DD format (e.g., "2025-01-15")  
    - goal.end_date: Must be in YYYY-MM-DD format (e.g., "2025-07-15")
    - tasks[].due_date: Must be in YYYY-MM-DD format (e.g., "2025-02-01")
    
    Example valid plan structure:
    {
        "goal": {
            "title": "Learn Python Programming", 
            "goal_type": "project",
            "start_date": "2025-01-01",
            "end_date": "2025-06-01"
        },
        "tasks": [
            {"title": "Complete Python basics", "due_date": "2025-02-01"}
        ]
    }
    
    Args:
        plan (dict): The structured plan data containing goal and tasks
        user_id (int): ID of the user who owns this plan  
        source_plan_id (int, optional): ID of the source plan if this is a refinement
        
    Returns:
        str: Success message with plan ID or error message
    """
    return _save_generated_plan_logic(plan, user_id, source_plan_id)


# Method 2: Using @tool decorator with custom name (LLM uses docstring as description)
@tool("get_user_plans")
def get_user_plans(user_id: int) -> str:
    """
    Retrieve all plans (approved or not) created by the user.

    Use this when the user wants to see all the plans they’ve worked on, including drafts and refinements.
    This gives context for previous attempts and decisions made in goal planning.

    Args:
        user_id (int): ID of the user

    Returns:
        str: List of all plans with their goal titles and statuses
    """
    try:
        from app.db.db import SessionLocal
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
        from app.db.db import SessionLocal
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

@tool("refine_existing_plan")
def refine_existing_plan(plan_id: int, user_feedback: str, user_id: int) -> str:
    """
    Refine an existing plan based on user feedback and create a new version.

    Use this tool when the user wants to revise, improve, or adjust a plan they previously created or received from the AI.
    This tool uses the original plan, the accumulated feedback, and the user’s latest input to generate a refined version.
    
    Args:
        plan_id (int): ID of the plan to refine
        user_feedback (str): Feedback text from the user describing the desired changes
        user_id (int): ID of the user making the request

    Returns:
        str: Confirmation message with the new refined plan's ID, user ID, and source plan ID.
    Raises:
        Exception: If there is an error during the refinement process.
    """
    try:
        from app.crud.planner import generate_refined_plan_from_feedback
        from app.db.db import SessionLocal

        db = SessionLocal()
        logger.info(f"Refining plan {plan_id} for user {user_id} with feedback: {user_feedback}")
        result = generate_refined_plan_from_feedback(
            db=db,
            plan_id=plan_id,
            feedback_text=user_feedback,
            suggested_changes="",  # You can split this later if needed
        )
        new_plan = result["saved_plan"]
        return f"✅ Refined plan created successfully with ID {new_plan.id} for user {user_id} and source plan {plan_id}."
    except Exception as e:
        logger.error(f"Error refining plan {plan_id} for user {user_id}: {str(e)}")
        return f"❌ Error refining plan: {str(e)}"





# Group the tools into a list
all_tools = [
    # save_generated_plan_tool_func,  # ✅ REMOVED: generate_plan_with_ai_tool now handles saving automatically
    get_user_plans,
    get_user_approved_plans,
    refine_existing_plan,
    generate_plan_with_ai_tool,
]
