from fastapi.testclient import TestClient
from app.main import app
from app.ai.schemas import PlanFeedbackAction


client = TestClient(app)

def test_plan_feedback_approve():
    payload = {
        "plan_id": 11,
        "goal_id": 5,
        "feedback_text": "Test approval feedback for plan id 11 goal id 5",
        "plan_feedback_action": PlanFeedbackAction.APPROVE.value,
        "suggested_changes": "None",
        "user_id": 1
    }

    response = client.post("/planning/plan-feedback", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["message"] == "Plan approved and stored successfully"
    assert data["feedback"] == payload["feedback_text"]
    assert data["plan_feedback_action"] == PlanFeedbackAction.APPROVE
    assert data["previous_plan_id"] == payload["plan_id"]
    assert data["refined_plan_id"] is None
    assert data["refined_plan"] is None
    assert "goal_id" in data