
✅ Checkpoint Summary: Plan Feedback and Refinement Logic (Mid-July 2025)

📍 Core Features Implemented

1. Completed the /plan-feedback endpoint in routers/planning.py, with full handling of both user actions:

Approval path (PlanFeedbackAction.APPROVE):

Saves the feedback.

Approves the current plan and unapproves all other plans for the same goal.

Returns a clean response using the PlanFeedbackResponse Pydantic schema.


Refinement path (PlanFeedbackAction.REQUEST_REFINEMENT):

Saves the feedback.

Triggers generate_refined_plan_from_feedback(), which:

Aggregates all feedback for the given goal.

Builds a structured refinement prompt.

Includes the most recent plan summary in the prompt as context.


The new plan is saved using save_generated_plan() with metadata.

Returns the refined plan with appropriate response data.




2. Prompt Engineering Enhancements

Designed a refinement prompt format that includes:

Accumulated feedback text from previous rounds.

The most recent (rejected) plan in structured summary format.


Ensures better context for the LLM to improve output iteratively.



3. Refinement Metadata Tracking

Added 2 fields to the plans table via Alembic migration:

refinement_round: tracks the round number.

refined_from_plan_id: foreign key to the parent plan.


This supports:

Analytics of user iteration behavior.

Better UX feedback in the future ("You’re on refinement round 3").




4. Database + Pydantic Model Updates

Updated Plan model in models.py.

Added the new metadata fields to the GeneratedPlan Pydantic schema in ai/schemas.py.

Logic in save_generated_plan() was updated to:

Auto-calculate the next refinement round.

Assign parent refined_from_plan_id.




5. Swagger + Testing Readiness

All changes are reflected in response models for Swagger auto-documentation.

System is ready for full test via Swagger UI.





---

📌 Additional Notes (Important Context)

✅ Business logic enforced: Only one approved plan per goal at a time.

✅ Transactions now use with db.begin() to ensure atomic commits and rollback safety.

✅ We agreed that refinements don’t have to be from approved plans only — the system supports refining any previously generated plan.

✅ The current setup automatically saves each generated plan to the DB, so refinements always have a valid base plan to build on.



---