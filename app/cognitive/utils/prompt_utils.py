# app/cognitive/utils/prompt_utils.py
"""
Prompt utilities for intent recognition and LLM prompt construction.
- Versioned prompts
- Strict JSON output requirement
- MemoryContext summarization kept minimal & safe
"""

from __future__ import annotations
import json
from app.cognitive.contracts.types import MemoryContext
from app.cognitive.brain.intent_registry_routes import SUPPORTED_INTENTS, SYSTEM_INTENTS
from app.cognitive.utils.llm_backend import ChatMessage


def build_intent_messages(user_input: str, memory_context: MemoryContext):
    """
    Build messages (system + user) for LLM intent recognition.
    Includes supported intents and explains the 'clarify' fallback case.
    """
    system_prompt = f"""
You are the Intent Brain for a Smart Personal Planner.

Your task:
1. Detect the user's intent from the supported list.
2. Extract any relevant parameters.
3. If the intent is valid but REQUIRED parameters are missing, use intent="clarify".
   - parameters.missing[] must list the missing fields.
   - parameters.reason must explain why clarification is needed.
4. If the intent itself is unclear, use intent="ask_question".
5. Always return STRICT JSON.

Schema:
{{
  "intent": "<one of the supported intents OR 'clarify' OR 'ask_question'>",
  "parameters": {{ ... }},
  "confidence": <float between 0 and 1>,
  "notes": "<short reasoning>"
}}

Supported intents:
{_format_intents_for_prompt()}
""".strip()

    user_payload = json.dumps(
        {
            "user_message": user_input,
            "memory_summary": _summarize_memory_context(memory_context),
        },
        ensure_ascii=False,
    )

    return [
        ChatMessage(role="system", content=system_prompt),
        ChatMessage(role="user", content=user_payload),
    ]


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

# app/cognitive/utils/prompt_utils.py


def _format_intents_for_prompt() -> str:
    """
    Format both user-facing and system intents into a readable list for the LLM.
    """
    lines = ["User-facing intents:"]
    for intent in SUPPORTED_INTENTS:
        lines.append(f'- "{intent["name"]}": {intent["description"]}')

    lines.append("\nSystem intents (control/meta):")
    for intent in SYSTEM_INTENTS:
        lines.append(f'- "{intent["name"]}": {intent["description"]}')

    return "\n".join(lines)


def _summarize_memory_context(memory_context: MemoryContext) -> str:
    """
    Return a lightweight summary of MemoryContext for the LLM.
    """
    try:
        summary = {
            "user_id": getattr(memory_context, "user_id", None),
            "goals": [getattr(m, "goal_id", None) for m in (memory_context.episodic or []) if hasattr(m, "goal_id")],
            "recent_events": [getattr(m, "content", {}) for m in (memory_context.episodic or [])[:3]],
            "preferences": [getattr(m, "content", {}) for m in (memory_context.semantic or [])[:3]],
            "procedural_rules": [
                {
                    "name": getattr(m, "content", {}).get("name"),
                    "description": getattr(m, "content", {}).get("description"),
                    "conditions": getattr(m, "content", {}).get("conditions"),
                    "actions": getattr(m, "content", {}).get("actions"),
                }
                for m in (memory_context.procedural or [])[:3]
            ],
        }
    except Exception:
        summary = {}
    return json.dumps(summary, ensure_ascii=False)