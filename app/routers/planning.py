# app/routers/planning.py
# Create a route that:
# Accepts a natural language goal_description from the frontend or API consumer
# Invokes your goal_parser_chain
# Returns a structured plan (GeneratedPlan) as JSON

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from app.ai.goal_parser_chain import goal_parser_chain, parser
from app.ai.schemas import GeneratedPlan, PlanFeedbackRequest, PlanFeedbackResponse, GoalDescriptionRequest, AIPlanResponse, AIPlanWithCodeResponse, GeneratePlanRequest
from app.ai.goal_code_generator import GeneratedPlanWithCode, parser as code_parser, goal_code_chain 
from app.db import get_db  
from sqlalchemy.orm import Session
from app.crud import crud, planner
from app.models import PlanFeedbackAction, Feedback, Plan
from app.routers.users import get_current_user
from app.models import User
from datetime import date

router = APIRouter(
    prefix="/planning",
    tags=["AI Planning"]
)

# ------------------------------------------------

# 🎯 NEW: Generate plan for existing goal (RECOMMENDED)
@router.post("/generate-plan", response_model=AIPlanResponse)
def generate_plan_for_goal(
    request: GeneratePlanRequest, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate an AI plan for an existing goal. This is the recommended endpoint.
    Takes a goal_id and generates a plan based on the goal's title and description.
    """
    try:
        # Get the goal from database
        goal = crud.get_goal_by_id(db, request.goal_id)
        if not goal:
            raise HTTPException(status_code=404, detail=f"Goal with ID {request.goal_id} not found")
        
        # Verify user owns this goal
        if int(goal.user_id) != int(current_user.id):  # type: ignore
            raise HTTPException(status_code=403, detail="Not authorized to generate plan for this goal")
        
        # Create goal description from existing goal data + user preferences
        goal_description = f"Title: {goal.title}\nDescription: {goal.description}"
        if request.user_preferences:
            goal_description += f"\nUser Preferences: {request.user_preferences}"
        
        # Run the LangChain pipeline
        today = date.today().isoformat()
        generated_plan: GeneratedPlan = goal_parser_chain.invoke({
            "goal_description": goal_description,
            "format_instructions": parser.get_format_instructions(),
            "today_date": today
        })["plan"]

        # Save the plan (this will create a new goal in the database)
        # TODO: Modify save_generated_plan to link to existing goal instead of creating new one
        saved_plan = planner.save_generated_plan(
            plan=generated_plan,
            db=db,
            user_id=int(current_user.id)  # type: ignore
        )
        
        print(f"Generated plan saved with ID: {saved_plan.id} for goal ID: {request.goal_id}")

        response = AIPlanResponse(
            plan=generated_plan, 
            source="AI", 
            ai_version="1.0", 
            user_id=int(current_user.id)  # type: ignore
        )
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ✅ LEGACY: Generate plan from description (creates new goal)
@router.post("/ai-generate-plan", response_model=AIPlanResponse, deprecated=True)
def generate_plan_from_ai(request: GoalDescriptionRequest, db: Session = Depends(get_db)):
    """
    [DEPRECATED] Generate a structured plan from a natural language goal description using AI.
    Creates a new goal. Use POST /planning/generate-plan for existing goals instead.
    """
    try:
        # Run the LangChain pipeline with the user's goal description
        today = date.today().isoformat()

        generated_plan : GeneratedPlan = goal_parser_chain.invoke({
            "goal_description": request.goal_description,
            "format_instructions": parser.get_format_instructions(),
            "today_date": today
        })["plan"]

        response = AIPlanResponse(plan=generated_plan, source="AI", ai_version="1.0", user_id=request.user_id)

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
        print(f"Feedback action : {request.plan_feedback_action}")
        print(f"Suggested changes: {request.suggested_changes}")
        print(f"User ID: {request.user_id}")
        print(f"Timestamp: {request.timestamp}")
        print(f"Plan ID: {request.plan_id}")
        print(f"Suggested changes: {request.suggested_changes}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing feedback: {str(e)}")
    
    if request.plan_feedback_action is None:
        raise HTTPException(status_code=400, detail="feedback action must be provided")

    # First, validate that the plan exists
    plan_from_db = crud.get_plan_by_id(db, request.plan_id)
    if not plan_from_db:
        raise HTTPException(status_code=404, detail=f"Plan not found for the provided ID {request.plan_id}")

    # Check if feedback already exists for this plan
    existing_feedback = crud.get_feedback_by_plan_id(db, request.plan_id)
    if existing_feedback:
        raise HTTPException(status_code=400, detail=f"Feedback already exists for plan ID {request.plan_id}. Each plan can only have one feedback entry.")

    try:
        # Save the feedback to the database
        print("About to save feedback to database...")
        saved_feedback = crud.create_feedback(db=db, feedback_data=request)
        print(f"Feedback for plan ID: {request.plan_id} saved with ID: {saved_feedback.id}")

        if request.plan_feedback_action == PlanFeedbackAction.APPROVE:
            print("Marking plan as approved.")
            if plan_from_db:
                # Enforce business rule: Only one approved plan per goal at any time. Unapprove other approved plans for the same goal.
                other_approved_plans = db.query(Plan).filter(
                    Plan.goal_id == plan_from_db.goal_id,
                    Plan.is_approved.is_(True),
                    Plan.id != plan_from_db.id  # Exclude the current plan
                ).all()

                for other_plan in other_approved_plans:
                    setattr(other_plan, "is_approved", False)  # Mark as unapproved
                
                if other_approved_plans:
                    print(f"Unapproved {len(other_approved_plans)} plan(s) for goal {plan_from_db.goal_id}")
                
                setattr(plan_from_db, "is_approved", True)  # Mark the current plan as approved 

                db.commit()
                db.refresh(plan_from_db)
                print(f"Plan {plan_from_db.id} marked as approved.")
                
                # Return the response with the feedback and plan details
                return PlanFeedbackResponse(
                    message="Plan approved and stored successfully",
                    feedback=getattr(saved_feedback, "feedback_text"), 
                    plan_id=getattr(plan_from_db, "id"), 
                    plan_feedback_action=request.plan_feedback_action,
                    refined_plan_id=None,
                    refined_plan=None,
                    goal_id=getattr(plan_from_db, "goal_id")
                )
            
            else:
                raise HTTPException(status_code=404, detail="Plan not found for the provided ID {request.plan_id}")
        
        elif request.plan_feedback_action == PlanFeedbackAction.REQUEST_REFINEMENT:
            print(f"Plan {plan_from_db.id} not approved, and marked for refinement. Feedback stored, feedback ID: {saved_feedback.id}")
            
            # Generate a refined plan based on the feedback
            print("About to generate refined plan from feedback...")
            refinement_result = planner.generate_refined_plan_from_feedback(
                db=db, 
                plan_id=request.plan_id, 
                feedback_text=request.feedback_text,
                suggested_changes=request.suggested_changes or ""
            )
            print("Refined plan generated successfully!")
            
            # Extract the saved plan and generated plan from the result
            saved_refined_plan = refinement_result["saved_plan"]
            generated_plan = refinement_result["generated_plan"]
            
            print(f"Refined plan generated with ID: {saved_refined_plan.id}. The refined plan was generated from the plan with ID: {request.plan_id}")
            
            # The refined plan is already saved by the generate_refined_plan_from_feedback function
            # No need to save again
            
            return PlanFeedbackResponse(
                message="Refinement needed. Feedback stored successfully, previous plan not approved. Refined plan generated and saved.",
                feedback=getattr(saved_feedback, "feedback_text"),
                plan_id=request.plan_id,
                plan_feedback_action=request.plan_feedback_action,
                refined_plan_id=getattr(saved_refined_plan, "id"),
                refined_plan=generated_plan,  # Return the actual GeneratedPlan object
                goal_id=getattr(plan_from_db, "goal_id"),
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
        plan_id=2,
        goal_id=5,
        feedback_text="This is a test feedback",
        plan_feedback_action=PlanFeedbackAction.APPROVE,
        suggested_changes="No changes needed",
        user_id=2
    )

    response = plan_feedback(request=request, db=db)
    print("Response:", response)