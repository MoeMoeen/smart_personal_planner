# app/cognitive/utils/prompt_utils.py
"""
Prompt utilities for intent recognition and LLM prompt construction.
- Versioned prompts
- Strict JSON output requirement
- MemoryContext summarization kept minimal & safe
"""

from __future__ import annotations
from typing import List, Dict, Any
import json

from app.cognitive.contracts.types import MemoryContext
from app.cognitive.brain.intent_registry import SUPPORTED_INTENTS  # [{name, description, ...}]

PROMPT_VERSION = "intent_planning_v1"

def build_intent_prompt(user_input: str, memory_context: MemoryContext) -> str:
    """
    Build the LLM prompt for intent recognition & planning.
    Returns a single string suitable for a system or user message, depending on your LLM backend.
    The response must be valid JSON ONLY (no prose).
    """
    template = _get_prompt_template()
    intents = _get_intents_for_prompt()
    memory_summary = _summarize_memory_context(memory_context)
    prompt = template.format(
        intents=intents,
        user_message=user_input,
        memory_summary=memory_summary,
        prompt_version=PROMPT_VERSION
    )
    return prompt

def _get_prompt_template() -> str:
    return """
You are the Intent Brain for a Smart Personal Planner. Read the user message and the memory summary.
1) Decide the single BEST intent from the supported list.
2) Extract any parameters needed to fulfill the intent.
3) If the intent is unclear, use "ask_question" and include clarifying info.

STRICT OUTPUT: Return ONLY valid JSON (UTF-8), no explanations, no markdown.

Schema:
{{
  "intent": "<one of the supported intents>",
  "parameters": {{}},
  "confidence": <float 0..1>,
  "notes": "<short optional string>"
}}

Supported intents:
{intents}

User message:
{user_message}

Memory summary (truncated):
{memory_summary}

Output rules:
- JSON only
- Keys as shown in schema
- Use null instead of empty strings when unknown
- confidence in [0.0, 1.0]
- Append no trailing commentary.

# Prompt-Version: {prompt_version}
""".strip()

def _get_intents_for_prompt() -> str:
    lines: List[str] = []
    for item in SUPPORTED_INTENTS:
        name = item.get("name") or ""
        desc = item.get("description") or ""
        lines.append(f'- "{name}": {desc}')
    return "\n".join(lines)

def _summarize_memory_context(memory_context: MemoryContext) -> str:
    """
    Keep it compact to avoid prompt bloat. Only top signals.
    """
    try:
        summary: Dict[str, Any] = {
            "user_id": getattr(memory_context, "user_id", None),
            "recent_events": [
                getattr(m, "content", {}) for m in (getattr(memory_context, "episodic", []) or [])[:3]
            ],
            "preferences": [
                getattr(m, "content", {}) for m in (getattr(memory_context, "semantic", []) or [])[:3]
            ],
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
        # Fail-closed to a minimal summary if unexpected structures appear.
        return json.dumps({"user_id": getattr(memory_context, "user_id", None)})
