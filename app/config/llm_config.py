"""
LLM configuration and budget policy for the planning agent.

Primary provider: OpenAI GPT-4. Structured outputs (JSON/function calling),
low temperature for consistency. Includes budget envelope defaults.
"""

from __future__ import annotations
import os
import warnings

def _env(key: str, default: str | int | float | bool):
    val = os.getenv(key)
    if val is None:
        return default
    if isinstance(default, bool):
        return val.strip().lower() in {"1", "true", "yes", "on"}
    if isinstance(default, int):
        try:
            return int(val)
        except ValueError:
            return default
    if isinstance(default, float):
        try:
            return float(val)
        except ValueError:
            return default
    return val

_provider = _env("OPENAI_PROVIDER", "openai")
_model = _env("OPENAI_MODEL", "gpt-4o-mini")
_temperature = _env("OPENAI_TEMPERATURE", 0.1)
_max_tokens = _env("OPENAI_MAX_TOKENS", 4000)
_timeout = _env("OPENAI_TIMEOUT_SEC", 60)

# Structured output flags (can be turned off via env if model incompatible)
_function_calling = _env("OPENAI_FUNCTION_CALLING", True)
_json_mode = _env("OPENAI_JSON_MODE", True)

# Known models without OpenAI structured output support (legacy gpt-4, gpt-3.5-turbo)
_legacy_no_structured = {"gpt-4", "gpt-3.5-turbo"}
if _json_mode and _model in _legacy_no_structured:
    warnings.warn(
        f"Cannot enable json_mode/function calling reliably for legacy model '{_model}'. "
        f"Consider upgrading to gpt-4o / gpt-4.1 family or disable OPENAI_JSON_MODE=0.",
        UserWarning,
    )

LLM_CONFIG = {
    "provider": _provider,
    "model": _model,
    "temperature": _temperature,
    "max_tokens": _max_tokens,
    "timeout_sec": _timeout,
    "function_calling": _function_calling and _model not in _legacy_no_structured,
    "json_mode": _json_mode and _model not in _legacy_no_structured,
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
