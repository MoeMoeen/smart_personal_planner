# app/cognitive/utils/prompt_utils.py
"""
Prompt utilities for intent recognition and LLM prompt construction.
"""
from app.cognitive.contracts.types import MemoryContext
from app.cognitive.contracts.intents import SUPPORTED_INTENTS
import json

def build_intent_prompt(user_input: str, memory_context: MemoryContext) -> str:
    """
    Build the LLM prompt for intent recognition, including supported intents and memory context summary.
    """
    prompt_template = _get_prompt_template()
    intents = _get_intents_for_prompt()
    memory_summary = _summarize_memory_context(memory_context)
    full_prompt = prompt_template.format(intents=intents)
    full_prompt += f"\n\nUser message: {user_input}\n"
    full_prompt += f"Memory context summary: {memory_summary}\n"
    return full_prompt

def _get_prompt_template() -> str:
    return """
You are an intelligent assistant for a smart personal planning system. Your task is to analyze the user's message and determine their intent from the list below. For each intent, extract any relevant parameters (such as goal name, task details, time, etc.) and return your answer as a JSON object with the following schema:

{{
  \"intent\": \"<one of the supported intents>\",
  \"parameters\": {{ ...extracted parameters... }}
}}

Supported intents and their explanations:
{intents}

If the user's intent is unclear, return \"intent\": \"ask_question\" and include the original message in the parameters.

Examples:
1. User: \"I want to create a new plan for my fitness goal.\"
   Output: {{\"intent\": \"create_new_plan\", \"parameters\": {{\"goal\": \"fitness\"}}}}
2. User: \"I'm behind on my reading plan, help me catch up.\"
   Output: {{\"intent\": \"adaptive_replan\", \"parameters\": {{\"goal\": \"reading\"}}}}
3. User: \"Change the deadline for my project task to next Friday.\"
   Output: {{\"intent\": \"update_task\", \"parameters\": {{\"task\": \"project task\", \"new_deadline\": \"next Friday\"}}}}
4. User: \"What are my preferences for work-life balance?\"
   Output: {{\"intent\": \"ask_about_preferences\", \"parameters\": {{\"topic\": \"work-life balance\"}}}}
"""

def _get_intents_for_prompt() -> str:
    return "\n".join([
        f'- "{intent["name"]}": {intent["description"]}' for intent in SUPPORTED_INTENTS
    ])

def _summarize_memory_context(memory_context: MemoryContext) -> str:
    summary = {
        "user_id": memory_context.user_id,
        "goals": [getattr(m, 'goal_id', None) for m in (memory_context.episodic or []) if hasattr(m, 'goal_id')],
        "recent_events": [getattr(m, 'content', {}) for m in (memory_context.episodic or [])[:3]],
        "preferences": [getattr(m, 'content', {}) for m in (memory_context.semantic or [])[:3]],
        "procedural_rules": [
            {
                "name": getattr(m, 'content', {}).get('name'),
                "description": getattr(m, 'content', {}).get('description'),
                "conditions": getattr(m, 'content', {}).get('conditions'),
                "actions": getattr(m, 'content', {}).get('actions')
            }
            for m in (memory_context.procedural or [])[:3]
        ]
    }
    return json.dumps(summary)
