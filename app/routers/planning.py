# Create a route that:
# Accepts a natural language goal_description from the frontend or API consumer
# Invokes your goal_parser_chain
# Returns a structured plan (GeneratedPlan) as JSON

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from app.ai.goal_parser_chain import goal_parser_chain, parser         # ✅ Your LangChain logic
from app.ai.schemas import GeneratedPlan, PlanFeedbackRequest, PlanRefinementRequest
from app.ai.goal_code_generator import GeneratedPlanWithCode, parser as code_parser, goal_code_chain 
from app.db import get_db  
from sqlalchemy.orm import Session
from app.crud import crud

router = APIRouter(
    prefix="/planning",
    tags=["AI Planning"]
)

# ✅ Input schema for the user’s natural language goal
class GoalDescriptionRequest(BaseModel):
    goal_description: str = Field(..., description="User's natural language description of the goal")  

# ✅ Output schema: the full structured plan
class AIPlanResponse(BaseModel):
    plan: GeneratedPlan = Field(..., description="AI-generated structured plan")
    source: str = Field(default="AI", description="Source of the generated plan")   
    ai_version: str = Field(default="1.0", description="Version of the AI model used")

# ✅ Output schema for plan with code snippet
# 👇 This is what we expose as FastAPI response

class AIPlanWithCodeResponse(GeneratedPlanWithCode):
    # plan: GeneratedPlanWithCode = Field(..., description="AI-generated structured plan with code snippet")
    # code_block: str = Field(..., description="Python code snippet to save this plan to the database")   
    source: str = Field(default="AI", description="Source of the generated plan")   
    ai_version: str = Field(default="1.0", description="Version of the AI model used")


# ✅ Main route: POST /planning/ai-generate-plan
@router.post("/ai-generate-plan", response_model=AIPlanResponse)
def generate_plan_from_ai(request: GoalDescriptionRequest):
    """
    Generate a structured plan from a natural language goal description using AI.
    """
    try:
        # Run the LangChain pipeline with the user's goal description
        generated_plan: GeneratedPlan = goal_parser_chain.invoke(
            {
                "goal_description": request.goal_description,
                "format_instructions": parser.get_format_instructions()
            }    
        )
        response = AIPlanResponse(plan=generated_plan, source="AI", ai_version="1.0")
        # Return the structured plan as JSON
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ✅ Route for generating a plan with code snippet    
@router.post("/ai-generate-plan-with-code", response_model=AIPlanWithCodeResponse)
def generate_plan_with_code(request: GoalDescriptionRequest):
    """
    Generate a structured plan and code snippet from a natural language goal description using AI.
    """
    try:
        # Run the LangChain pipeline with the user's goal description
        generated_plan_with_code: GeneratedPlanWithCode = goal_code_chain.invoke(
            {
                "goal_description": request.goal_description,
                # "format_instructions": code_parser.get_format_instructions()
            }    
        )

        # Validate the plan structure
        if not generated_plan_with_code.plan or not generated_plan_with_code.code_snippet:
            raise HTTPException(status_code=500, detail="Plan generation failed or code snippet missing")
        
        # Ensure the code snippet is a valid string
        if not isinstance(generated_plan_with_code.code_snippet, str):
            raise HTTPException(status_code=500, detail="Code snippet is not a valid string")
        
        # Ensure the plan is a valid GeneratedPlan object
        if not isinstance(generated_plan_with_code.plan, GeneratedPlan):
            raise HTTPException(status_code=500, detail="Generated plan is not valid")

        # Create the response object
        response = AIPlanWithCodeResponse(
            plan=generated_plan_with_code.plan,
            code_snippet=generated_plan_with_code.code_snippet,
            source="AI+Code",
            ai_version="1.1"
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@router.post("/submit-feedback")
def submit_plan_feedback(request: PlanFeedbackRequest):
    """
    Submit feedback on a generated plan.
    """

    try:
        # log the feedback for now.
        print(f"Feedback received: {request.model_dump()}")
        print(f"Feedback text: {request.feedback_text}")
        print(f"Is approved: {request.is_approved}")
        print(f"Suggested changes: {request.suggested_changes}")
        print(f"User ID: {request.user_id}")
        print(f"Timestamp: {request.timestamp}")
        print(f"Plan ID: {request.plan_id}")
        print(f"Suggested changes: {request.suggested_changes}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing feedback: {str(e)}")
    
    # ✅ Here you would typically save the feedback to the database
    # For now, we just return it as a confirmation
    return {
        "message": "Feedback submitted successfully",
        "feedback": request.model_dump(),
    }

@router.post("/refine-plan")
def refine_plan(request: PlanRefinementRequest, db: Session = Depends(get_db)):
    """
    Refine a generated plan based on user feedback.
    """
    # 1. get the existing plan from the database
    existing_plan = crud.get_plan_by_id(db, request.plan_id)

    if not existing_plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    # 2. get the feedback if exists
    feedback = crud.get_feedback_by_plan_id(db, request.plan_id)

    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found for this plan")
    
    # 3. Build a feedback summary
    feedback_instructions = ""
    if feedback:
        feedback_instructions += f"\n\nFeedback: {feedback.feedback_text}\n"
        if feedback.suggested_changes:
            feedback_instructions += f"Suggested changes: {feedback.suggested_changes}\n"
        
    if request.custom_feedback:
        feedback_instructions += f"\nCustom feedback: {request.custom_feedback}\n"


    # If no feedback is provided, we can use the existing plan description
    if not feedback_instructions:
        feedback_instructions = existing_plan.goal.description or existing_plan.goal.title

    feedback_instructions = feedback_instructions.strip()

    # 4. Combine into prompt input
    ai_input = {
        "goal_description": existing_plan.goal.description or existing_plan.goal.title,
        # "format_instructions": parser.get_format_instructions(),
        "prior_feedback": feedback_instructions
    }

    # 5. Run the AI Chain: Invoke the goal parser chain with the feedback
    try:
        refined_plan: GeneratedPlan = goal_parser_chain.invoke(ai_input)

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
