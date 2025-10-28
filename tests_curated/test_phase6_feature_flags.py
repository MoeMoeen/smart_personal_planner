"""
Phase 6 Integration Tests: Feature Flag Toggling for Agentic vs Fallback Flows
"""

import pytest
import os
from unittest.mock import patch
from app.config.feature_flags import is_fallback_mode_enabled, FEATURE_FLAGS
from app.cognitive.brain.intent_registry_routes import (
    get_flow_registry,
    AGENTIC_FLOW_REGISTRY, 
    FALLBACK_FLOW_REGISTRY
)


class TestPhase6FeatureFlagToggling:
    """Test agentic vs fallback flow toggling via feature flag."""
    
    def test_feature_flag_defaults(self):
        """Test that feature flags have correct default values."""
        # Default should be agentic mode (fallback=False)
        assert not is_fallback_mode_enabled()
        assert not FEATURE_FLAGS["PLANNING_FALLBACK_MODE"]
    
    def test_agentic_flow_registry_structure(self):
        """Test that agentic flows are minimal (planning_node only for planning intents)."""
        agentic = AGENTIC_FLOW_REGISTRY
        
        # Agentic planning flows should be minimal
        assert agentic["create_new_plan"] == ["planning_node"]
        assert agentic["revise_plan"] == ["planning_node"] 
        assert agentic["adaptive_replan"] == ["planning_node"]
        
        # Direct operations should not use planning_node
        assert "planning_node" not in agentic["update_task"]
        assert "planning_node" not in agentic["reschedule_task"]
        
    def test_fallback_flow_registry_structure(self):
        """Test that fallback flows are deterministic and modular."""
        fallback = FALLBACK_FLOW_REGISTRY
        
        # Fallback should have full deterministic flows
        assert len(fallback["create_new_plan"]) > 5  # Multiple modular nodes
        assert "plan_outline_node_legacy" in fallback["create_new_plan"]  # Deterministic, not agentic
        assert "user_confirm_a_node" in fallback["create_new_plan"]
        assert "task_generation_node" in fallback["create_new_plan"]
        assert "persistence_node" in fallback["create_new_plan"]
        
    @patch.dict(os.environ, {"PLANNING_FALLBACK_MODE": "false"})
    def test_get_flow_registry_agentic_mode(self):
        """Test get_flow_registry returns agentic flows when fallback mode is disabled."""
        # Force reload of feature flags
        from importlib import reload
        import app.config.feature_flags
        reload(app.config.feature_flags)
        
        registry = get_flow_registry()
        
        # Should return agentic registry
        assert registry == AGENTIC_FLOW_REGISTRY
        assert registry["create_new_plan"] == ["planning_node"]
        
    @patch.dict(os.environ, {"PLANNING_FALLBACK_MODE": "true"})  
    def test_get_flow_registry_fallback_mode(self):
        """Test get_flow_registry returns fallback flows when fallback mode is enabled."""
        # Force reload of feature flags
        from importlib import reload
        import app.config.feature_flags
        reload(app.config.feature_flags)
        
        registry = get_flow_registry()
        
        # Should return fallback registry
        assert registry == FALLBACK_FLOW_REGISTRY
        assert len(registry["create_new_plan"]) > 5  # Deterministic flow
        
    def test_agentic_vs_fallback_flow_differences(self):
        """Test that agentic and fallback flows are meaningfully different."""
        agentic_create = AGENTIC_FLOW_REGISTRY["create_new_plan"]
        fallback_create = FALLBACK_FLOW_REGISTRY["create_new_plan"]
        
        # Agentic should be much shorter (just planning_node)
        assert len(agentic_create) == 1
        assert len(fallback_create) > 5
        
        # Agentic should not have confirm nodes
        assert "user_confirm_a_node" not in agentic_create
        assert "user_confirm_b_node" not in agentic_create
        
        # Fallback should have confirm nodes
        assert "user_confirm_a_node" in fallback_create
        assert "user_confirm_b_node" in fallback_create
        
    def test_all_planning_intents_have_agentic_flows(self):
        """Test that all planning intents have corresponding agentic flows."""
        planning_intents = ["create_new_plan", "revise_plan", "adaptive_replan"]
        
        for intent in planning_intents:
            assert intent in AGENTIC_FLOW_REGISTRY
            assert intent in FALLBACK_FLOW_REGISTRY
            
            # Agentic should use planning_node exclusively for planning
            agentic_flow = AGENTIC_FLOW_REGISTRY[intent]
            assert agentic_flow == ["planning_node"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])