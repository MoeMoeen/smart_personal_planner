# Create a route that:
# Accepts a natural language goal_description from the frontend or API consumer
# Invokes your goal_parser_chain
# Returns a structured plan (GeneratedPlan) as JSON

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from app.ai.goal_parser_chain import goal_parser_chain, parser, refine_plan_chain         # ✅ Your LangChain logic
from app.ai.schemas import GeneratedPlan, PlanFeedbackRequest, PlanRefinementRequest, GoalDescriptionRequest, AIPlanResponse, AIPlanWithCodeResponse
from app.ai.goal_code_generator import GeneratedPlanWithCode, parser as code_parser, goal_code_chain 
from app.db import get_db  
from sqlalchemy.orm import Session
from app.crud import crud, planner

router = APIRouter(
    prefix="/planning",
    tags=["AI Planning"]
)
# ------------------------------------------------

# ✅ Main route: POST /planning/ai-generate-plan
@router.post("/ai-generate-plan", response_model=AIPlanResponse)
def generate_plan_from_ai(request: GoalDescriptionRequest, db: Session = Depends(get_db)):
    """
    Generate a structured plan from a natural language goal description using AI.
    """
    try:
        # Run the LangChain pipeline with the user's goal description
        generated_plan : GeneratedPlan = goal_parser_chain.invoke(
            {
                "goal_description": request.goal_description,
                "format_instructions": parser.get_format_instructions()
            }    
        )["plan"]
        
        response = AIPlanResponse(plan=generated_plan, source="AI", ai_version="1.0")

        saved_goal = planner.save_generated_plan(
            plan=generated_plan,
            db=db,
            user_id=request.user_id  # Pass the user ID
        )
        # Log the saved goal ID
        print(f"Generated plan saved with goal ID: {saved_goal.id}")

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
            code_block=generated_plan_with_code.code_snippet,
            source="AI+Code",
            ai_version="1.1"
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@router.post("/plan-feedback")
def plan_feedback(request: PlanFeedbackRequest, db: Session = Depends(get_db)):
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
    
    if request.is_approved is None:
        raise HTTPException(status_code=400, detail="is_approved must be provided")

    try:
        # Save the feedback to the database
        feedback = crud.create_feedback(db=db, feedback_data=request)
        if request.is_approved:
            print("Marking plan as approved.")
            plan = crud.get_plan_by_id(db, request.plan_id)
            if plan:
                setattr(plan, "is_approved", True)  # Mark the plan as approved (ensure is_approved is a boolean field in your Plan model)
                db.commit()
                db.refresh(plan)
                print(f"Plan {plan.id} marked as approved.")

                return {
                    "message": "Plan approved and stored successfully",
                    "feedback": feedback.model_dump(),
                    "plan_id": plan.id,
                    "is_approved": request.is_approved,
                }
            
            else:
                raise HTTPException(status_code=404, detail="Plan not found for the provided ID {request.plan_id}")
        else:
            print("Plan not approved, no changes made to the plan. Only feedback stored.")
            return {
                "message": "Refinement needed. Feedback stored successfully, plan not approved.",
                "feedback": feedback.model_dump(),
                "is_approved": request.is_approved,
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving feedback: {str(e)}")

# ------------------------------------------------

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
        refined_plan: GeneratedPlan = refine_plan_chain.invoke(ai_input)["plan"]

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
