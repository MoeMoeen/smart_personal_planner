# app/cognitive/utils/prompt_utils.py
"""
Prompt utilities for intent recognition and LLM prompt construction.
- Versioned prompts
- Strict JSON output requirement
- MemoryContext summarization kept minimal & safe
"""

# =============================
# app/cognitive/utils/prompt_utils.py
# =============================
from __future__ import annotations
from typing import List, Dict, Any
import json

from app.cognitive.contracts.types import MemoryContext
from app.cognitive.brain.intent_registry_routes import SUPPORTED_INTENTS  # list[dict]
from app.cognitive.utils.llm_backend import ChatMessage

PROMPT_VERSION = "intent_planning_v1"

# --- Public API (messages-first) -------------------------------------------------------

def build_intent_messages(user_input: str, memory_context: MemoryContext) -> List[ChatMessage]:
    """Return OpenAI-style chat messages (system + user) for intent detection.

    Use with LLM backend like:
        backend.chat(messages=build_intent_messages(msg, mem_ctx), temperature=0)
    """
    system_text = _get_system_instruction()
    user_text = _format_user_block(user_input, memory_context)
    return [
        ChatMessage(role="system", content=system_text),
        ChatMessage(role="user", content=user_text),
    ]

# Backward-compatible (single-string) variant

def build_intent_prompt(user_input: str, memory_context: MemoryContext) -> str:
    return _get_system_instruction() + "\n\n" + _format_user_block(user_input, memory_context)

# --- Internals ------------------------------------------------------------------------

def _get_system_instruction() -> str:
    return f"""
You are the Intent Brain for a Smart Personal Planner. Read the user message and the memory summary.
1) Decide the single BEST intent from the supported list.
2) Extract any parameters needed to fulfill the intent.
3. If the intent is valid but REQUIRED parameters are missing, output intent="clarify".
   - List all missing fields in parameters.missing[]
   - Include a reason in parameters.reason.
4. If the intent itself is unclear, use intent="ask_question".

STRICT OUTPUT: Return ONLY valid JSON (UTF-8), no explanations, no markdown.

Schema:
{{
  "intent": "<one of the supported intents>",
  "parameters": {{}},
  "confidence": <float 0..1>,
  "notes": "<short optional string>"
}}

Supported intents:
{_get_intents_for_prompt()}

Output rules:
- JSON only
- Keys as shown in schema
- Use null instead of empty strings when unknown
- confidence in [0.0, 1.0]
- Append no trailing commentary.

# Prompt-Version: {PROMPT_VERSION}
""".strip()

def _format_user_block(user_input: str, memory_context: MemoryContext) -> str:
    memory_summary = _summarize_memory_context(memory_context)
    return (
        "User message:\n" + user_input + "\n\n" +
        "Memory summary (truncated):\n" + memory_summary
    )

def _get_intents_for_prompt() -> str:
    lines = []
    for item in SUPPORTED_INTENTS:
        name = item.get("name") or ""
        desc = item.get("description") or ""
        lines.append(f'- "{name}": {desc}')
    return "\n".join(lines)

def _summarize_memory_context(memory_context: MemoryContext) -> str:
    try:
        summary: Dict[str, Any] = {
            "user_id": getattr(memory_context, "user_id", None),
            "recent_events": [getattr(m, "content", {}) for m in (getattr(memory_context, "episodic", []) or [])[:3]],
            "preferences": [getattr(m, "content", {}) for m in (getattr(memory_context, "semantic", []) or [])[:3]],
            "rules": [
                {
                    "name": (getattr(m, "content", {}) or {}).get("name"),
                    "conditions": (getattr(m, "content", {}) or {}).get("conditions"),
                    "actions": (getattr(m, "content", {}) or {}).get("actions"),
                }
                for m in (getattr(memory_context, "procedural", []) or [])[:2]
            ],
        }
        return json.dumps(summary, ensure_ascii=False)
    except Exception:
        return json.dumps({"user_id": getattr(memory_context, "user_id", None)})


