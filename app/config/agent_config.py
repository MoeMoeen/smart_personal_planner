"""
Agent configuration for Phase 7 (ReAct planning agent).

Contains controller caps, confidence thresholds, RFC policy, and feature toggles
that modulate agent behavior. These are safe-to-import constants with clear
docstrings and conservative defaults.
"""

from __future__ import annotations
import os

# ─────────────────────────────────────────────────────────────
# Controller limits (hard/soft caps)
# ─────────────────────────────────────────────────────────────

# Maximum end-to-end tool/turn iterations inside the controller state machine
TURN_LIMIT: int = 10

# Maximum repair/prompt-narrow retries per validation stage
RETRY_LIMIT_PER_STAGE: int = 2

# End-to-end wall clock guard for a single planning session (seconds)
WALL_TIME_SEC: int = 45

# Soft cost ceiling per controller turn (USD). If exceeded, the agent should
# summarize and ask the user whether to continue before proceeding.
SOFT_BUDGET_PER_TURN_USD: float = 0.30


# ─────────────────────────────────────────────────────────────
# Confidence thresholds (quantitative policy)
# ─────────────────────────────────────────────────────────────

# Continue when >= CONTINUE_MIN; Retry when in [RETRY_MIN, CONTINUE_MIN);
# Escalate when < ESCALATE_MAX.
CONTINUE_MIN: float = 0.70
RETRY_MIN: float = 0.40
ESCALATE_MAX: float = 0.40

# Pattern-specific convenience thresholds
PATTERN_CONFIDENCE_MIN: float = 0.70
PATTERN_RETRY_MIN: float = 0.50


# ─────────────────────────────────────────────────────────────
# RFC / pattern proposal policy
# ─────────────────────────────────────────────────────────────

ALLOW_NEW_SUBTYPE_PROPOSALS: bool = True
REQUIRE_RFC_FOR_NEW_SUBTYPE: bool = True


# ─────────────────────────────────────────────────────────────
# Tool metadata enforcement (optional controller checks)
# ─────────────────────────────────────────────────────────────

# When True, the controller performs a topological check using tool
# prerequisites/produces metadata before executing a tool.
ENFORCE_TOOL_DEPENDENCIES: bool = True


# 
# ─────────────────────────────────────────────────────────────
# Debug / tracing controls
# ─────────────────────────────────────────────────────────────
#
# PLANNING_DEBUG enables compact run-event echo to stdout at the end of a run
# and ensures collected run events are available in state.run_metadata.
# It is populated from the environment (e.g., .env) for easy toggling.
def _str2bool(val: str | None, default: bool = False) -> bool:
	if val is None:
		return default
	return val.strip().lower() in {"1", "true", "yes", "on"}

PLANNING_DEBUG: bool = _str2bool(os.getenv("PLANNING_DEBUG"), default=False)
