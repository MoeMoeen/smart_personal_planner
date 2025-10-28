from app.cognitive.agents.planning_tools import ApprovalHandlerTool, ApprovalHandlerInput

def test_approval_handler_pending_with_rfc():
    tool = ApprovalHandlerTool()
    res = tool.run(ApprovalHandlerInput(approval_policy="milestone_approvals", pattern_rfc_required=True, pattern_rfc_text="Propose subtype X"))
    assert res.ok
    assert res.data.get("decision") == "pending"
    assert "approve" in res.data.get("cta", "").lower()


def test_approval_handler_auto_approve_single_final():
    tool = ApprovalHandlerTool()
    res = tool.run(ApprovalHandlerInput(approval_policy="single_final", pattern_rfc_required=False))
    assert res.ok
    assert res.data.get("decision") == "approved"


def test_approval_handler_user_approve_feedback():
    tool = ApprovalHandlerTool()
    res = tool.run(ApprovalHandlerInput(approval_policy="milestone_approvals", pattern_rfc_required=True, user_feedback="approve"))
    assert res.ok
    assert res.data.get("decision") == "approved"
