"""
LLM configuration and budget policy for the planning agent.

Primary provider: OpenAI GPT-4. Structured outputs (JSON/function calling),
low temperature for consistency. Includes budget envelope defaults.
"""

from __future__ import annotations

LLM_CONFIG = {
    "provider": "openai",
    "model": "gpt-4-turbo-preview",
    "temperature": 0.1,
    "max_tokens": 4000,
    "timeout_sec": 60,
    "function_calling": True,
    "json_mode": True,
}

BUDGET_CONFIG = {
    # Daily global cap (dev and prod). Adjust via environment if needed.
    "daily_limit_usd": 5.0,
    # Per-session cap for a single planning run
    "per_session_limit_usd": 2.0,
    # Per-turn soft ceiling; if exceeded, agent should ask to continue
    "per_turn_soft_limit_usd": 0.30,
    # Alert thresholds (best-effort; surfaced via logs/telemetry)
    "alerts": {
        "pct_80": True,
        "pct_95": True,
    },
}
