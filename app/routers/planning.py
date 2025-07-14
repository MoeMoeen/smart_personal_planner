# Create a route that:
# Accepts a natural language goal_description from the frontend or API consumer
# Invokes your goal_parser_chain
# Returns a structured plan (GeneratedPlan) as JSON

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from app.ai.goal_parser_chain import goal_parser_chain, parser         # ✅ Your LangChain logic
from app.ai.schemas import GeneratedPlan

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