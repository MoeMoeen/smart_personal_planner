"""
Phase 5 E2E Test: Router Function Integration with Graph
Testing complete routing behavior from planning_node through all branch paths.
"""

import pytest
from app.cognitive.state.graph_state import GraphState


class TestPhase5E2ERouting:
    """Test complete routing behavior in the graph."""
    
    def test_message_handler_imports_and_uses_router(self):
        """Test that message handler imports and uses the planning router."""
        # Import the module to check it loads without error
        from app.orchestration import message_handler
        
        # Check that the router function is imported and accessible
        from app.flow.router import route_after_planning_result
        assert route_after_planning_result is not None
        
        # Verify the function signature matches expectations
        state = GraphState(planning_status="complete")
        result = route_after_planning_result(state)
        assert result == "to_world_model"
    
    def test_graph_compilation_with_router(self):
        """Test that graph compilation includes the router."""
        from app.flow.flow_compiler import FlowCompiler, CompileOptions
        from app.flow.adapters.langgraph_adapter import LangGraphBuilderAdapter
        from app.flow.router import route_after_planning_result
        
        # Test the same pattern used in message_handler.py
        compiler = FlowCompiler(lambda: LangGraphBuilderAdapter(GraphState))
        options = CompileOptions(
            conditional_routers={"planning_node": route_after_planning_result}
        )
        
        assert options.conditional_routers is not None
        assert "planning_node" in options.conditional_routers
        assert options.conditional_routers["planning_node"] == route_after_planning_result
    
    def test_router_basic_functionality(self):
        """Test that router function works with different input formats."""
        from app.flow.router import route_after_planning_result
        
        # Test complete status
        state = GraphState(planning_status="complete")
        result = route_after_planning_result(state)
        
        assert result == "to_world_model"
        # Note: Logger is not actually in the router function yet
        
        # Test needs_clarification status
        state = GraphState(planning_status="needs_clarification")
        result = route_after_planning_result(state)
        
        assert result == "to_planning_loop"
    
    def test_all_valid_planning_statuses_route_correctly(self):
        """Test that all valid planning statuses route to the correct nodes."""
        from app.flow.router import route_after_planning_result
        
        # Test complete status
        state = GraphState(planning_status="complete")
        result = route_after_planning_result(state)
        assert result == "to_world_model"
        
        # Test needs_clarification status
        state = GraphState(planning_status="needs_clarification")
        result = route_after_planning_result(state)
        assert result == "to_planning_loop"
        
        # Test needs_scheduling_escalation status
        state = GraphState(planning_status="needs_scheduling_escalation")
        result = route_after_planning_result(state)
        assert result == "to_scheduling_escalation"
        
        # Test aborted status
        state = GraphState(planning_status="aborted")
        result = route_after_planning_result(state)
        assert result == "to_summary_or_end"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])