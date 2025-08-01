# app/agent/tools.py

from langchain_core.tools import tool
from app.crud.planner import save_generated_plan
from app.ai.schemas import GeneratedPlan
from sqlalchemy.orm import Session
from app.db import SessionLocal
from typing import Optional

@tool
def save_generated_plan_tool(plan: dict, user_id: int, source_plan_id: Optional[int] = None) -> str:
    """
    Save a generated plan into the database using the existing save_generated_plan logic.
    
    Args:
        plan (dict): The plan object returned by the LLM (structured like GeneratedPlan).
        user_id (int): ID of the user owning the plan.
        source_plan_id (int): Optional ID of the plan this one refines.

    Returns:
        str: Confirmation message with the plan ID.
    """
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
    

# Group the tools into a list
all_tools = [
    save_generated_plan_tool,
    # We’ll add refine_plan_tool next
]
