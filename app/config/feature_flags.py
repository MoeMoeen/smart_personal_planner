#app/config/feature_flags.py
"""
Feature flags for Smart Personal Planner.
Toggles between agentic and deterministic fallback flows.
"""

import os
from typing import Dict, Any

# Phase 6 Feature Flag: Toggle between agentic and deterministic fallback planning
PLANNING_FALLBACK_MODE: bool = os.getenv("PLANNING_FALLBACK_MODE", "false").lower() == "true"

# Feature flag registry for easy management
FEATURE_FLAGS: Dict[str, Any] = {
    "PLANNING_FALLBACK_MODE": PLANNING_FALLBACK_MODE,
}

def is_fallback_mode_enabled() -> bool:
    """
    Check if deterministic fallback mode is enabled.
    
    When False (default): Use agentic planning_node (ReAct-style) 
    When True: Use deterministic modular flow (legacy)
    """
    return FEATURE_FLAGS["PLANNING_FALLBACK_MODE"]

def get_flag(flag_name: str, default: Any = None) -> Any:
    """Get feature flag value by name."""
    return FEATURE_FLAGS.get(flag_name, default)