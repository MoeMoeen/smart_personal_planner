# Create a route that:
# Accepts a natural language goal_description from the frontend or API consumer
# Invokes your goal_parser_chain
# Returns a structured plan (GeneratedPlan) as JSON

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from app.ai.goal_parser_chain import goal_parser_chain, parser         # ✅ Your LangChain logic
from app.ai.schemas import GeneratedPlan
from app.ai.goal_code_generator import GeneratedPlanWithCode, parser as code_parser, goal_code_chain 

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