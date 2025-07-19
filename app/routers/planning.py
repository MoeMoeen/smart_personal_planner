# Create a route that:
# Accepts a natural language goal_description from the frontend or API consumer
# Invokes your goal_parser_chain
# Returns a structured plan (GeneratedPlan) as JSON

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from app.ai.goal_parser_chain import goal_parser_chain, parser
from app.ai.schemas import GeneratedPlan, PlanFeedbackRequest, PlanFeedbackResponse, GoalDescriptionRequest, AIPlanResponse, AIPlanWithCodeResponse
from app.ai.goal_code_generator import GeneratedPlanWithCode, parser as code_parser, goal_code_chain 
from app.db import get_db  
from sqlalchemy.orm import Session
from app.crud import crud, planner
from app.models import PlanFeedbackAction

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

        saved_plan = planner.save_generated_plan(
            plan=generated_plan,
            db=db,
            user_id=request.user_id  # Pass the user ID
        )
        # Log the saved goal ID
        print(f"Generated plan saved with goal ID: {saved_plan.id}")

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
    

@router.post("/plan-feedback", response_model=PlanFeedbackResponse)
def plan_feedback(request: PlanFeedbackRequest, db: Session = Depends(get_db)) -> PlanFeedbackResponse:
    """
    Submit feedback on a generated plan.
    """

    try:
        # log the feedback for now.
        print(f"Feedback received: {request.model_dump()}")
        print(f"Feedback text: {request.feedback_text}")
        print(f"Feeback action : {request.plan_feedback_action}")
        print(f"Suggested changes: {request.suggested_changes}")
        print(f"User ID: {request.user_id}")
        print(f"Timestamp: {request.timestamp}")
        print(f"Plan ID: {request.plan_id}")
        print(f"Suggested changes: {request.suggested_changes}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing feedback: {str(e)}")
    
    if request.plan_feedback_action is None:
        raise HTTPException(status_code=400, detail="feedback action must be provided")

    try:
        # Save the feedback to the database
        feedback = crud.create_feedback(db=db, feedback_data=request)
        print(f"Feedback saved with ID: {feedback.id}")

        if request.plan_feedback_action == PlanFeedbackAction.APPROVE:
            print("Marking plan as approved.")
            plan = crud.get_plan_by_id(db, request.plan_id)
            if plan:
                setattr(plan, "is_approved", True)  # Mark the plan as approved (ensure is_approved is a boolean field in your Plan model)
                db.commit()
                db.refresh(plan)
                print(f"Plan {plan.id} marked as approved.")

                print("=" * 50)
                print("DEBUG:", type(plan), plan.__dict__)
                print("=" * 50)
                # Return the response with the feedback and plan details

                return PlanFeedbackResponse(
                    message="Plan approved and stored successfully",
                    feedback=feedback.feedback_text,
                    previous_plan_id=plan.id,
                    plan_feedback_action=request.plan_feedback_action,
                    refined_plan_id=None,
                    refined_plan=None,
                    goal_id=plan.goal_id
                )
            
            else:
                raise HTTPException(status_code=404, detail="Plan not found for the provided ID {request.plan_id}")
        elif request.plan_feedback_action == PlanFeedbackAction.REQUEST_REFINEMENT:
            plan = crud.get_plan_by_id(db, request.plan_id)

            if not plan:
                raise HTTPException(status_code=404, detail=f"Plan not found for the provided ID {request.plan_id}")

            print(f"Plan {plan.id} not approved, and marked for refinement. Feedback stored, feedback ID: {feedback.id}")
            
            # Generate a refined plan based on the feedback
            refined_plan = planner.generate_refined_plan_from_feedback(plan_id=request.plan_id, db=db)
            
            print(f"Refined plan generated with ID: {refined_plan.plan.plan_id}. The refined plan was generated from the plan with ID: {request.plan_id}")
            
            # Save the refined plan to the database
            saved_refined_plan = planner.save_generated_plan(
                plan=refined_plan.plan,
                db=db,
                user_id=request.user_id  # Pass the user ID
            )
            print(f"Refined plan saved with ID: {saved_refined_plan.id}")

            return PlanFeedbackResponse(
                message="Refinement needed. Feedback stored successfully, previous plan not approved. Refined plan generated and saved.",
                feedback=feedback.feedback_text,
                previous_plan_id=request.plan_id,
                plan_feedback_action=request.plan_feedback_action,
                refined_plan_id=saved_refined_plan.id,
                refined_plan=refined_plan.plan,
                goal_id=plan.goal_id,
            )
        else:
            raise HTTPException(status_code=400, detail="Invalid feedback action provided")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving feedback: {str(e)}")

# ------------------------------------------------

if __name__ == "__main__":
    from app.db import SessionLocal
    from app.ai.schemas import PlanFeedbackRequest
    from app.models import PlanFeedbackAction

    db = SessionLocal()

    request = PlanFeedbackRequest(
        plan_id=1,
        goal_id=1,
        feedback_text="This is a test feedback",
        plan_feedback_action=PlanFeedbackAction.APPROVE,
        suggested_changes="No changes needed",
        user_id=1
    )

    response = plan_feedback(request=request, db=db)
    print("Response:", response)