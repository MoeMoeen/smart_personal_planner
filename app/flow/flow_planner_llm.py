# app/flow/flow_planner_llm.py
# =============================

from __future__ import annotations
from typing import List, Dict, Any, Tuple
import json
import logging

from app.cognitive.contracts.types import MemoryContext
from app.cognitive.utils.llm_backend import get_llm_backend, ChatMessage
from app.flow.flow_compiler import NodeSpec
from app.cognitive.brain.intent_registry_routes import get_flow_registry

logger = logging.getLogger(__name__)

# ---- LLM-based planner ---------------------------------------------------------------

def build_planner_messages(intent: str, memory_context: MemoryContext, registry: Dict[str, NodeSpec], parameters: Dict[str, Any] | None = None) -> List[ChatMessage]:
    """Return chat messages asking the LLM to propose the best sequence of nodes/tools
    given the user's intent, memory summary, and the registry (with dependencies).
    """
    system = (
        "You are a Flow Strategist for a Smart Personal Planner.\n"
        "Given an intent and a registry of available nodes (with dependencies), propose the BEST sequence\n"
        "of node names to fulfill the intent. Respect dependencies: a node's dependencies MUST appear before it.\n"
        "Return ONLY strict JSON with schema: {\"sequence\": [<node_name>...], \"reason\": <short string>}\n"
        "Do NOT include nodes that are not in the registry.\n"
        "\n"
        "Reference defaults (for safety only, not mandatory), "
        "which are deterministic default flows used as a last resort. "
        "You don't have to follow them, but you may take inspiration and are still encouraged to improve or adapt them if context suggests:\n"
        f"{json.dumps(get_flow_registry(), indent=2)}\n"
    )

    # Compact registry spec for the LLM
    reg_list = []
    for name, spec in registry.items():
        reg_list.append({
            "name": name,
            "description": spec.description,
            "dependencies": list(spec.dependencies or []),
        })

    user = json.dumps({
        "intent": intent,
        "parameters": parameters or {},
        "memory_summary": _summarize_memory_context(memory_context),
        "registry": reg_list,
    }, ensure_ascii=False)

    user_message = ChatMessage(
        role="user",
        content=user
    )
    system_message = ChatMessage(
        role="system",
        content=system
    )
    return [
        system_message,
        user_message
    ]


def propose_sequence_llm(intent: str, memory_context: MemoryContext, registry: Dict[str, NodeSpec], temperature: float = 0.0, parameters: Dict[str, Any] | None = None) -> Dict[str, Any]:
    backend = get_llm_backend("openai")
    messages = build_planner_messages(intent, memory_context, registry, parameters=parameters)
    resp = backend.chat(messages=messages, temperature=temperature)
    try:
        data = json.loads(resp.content)
    except Exception as e:
        raise ValueError(f"Planner LLM returned non-JSON: {resp.content[:120]}...") from e

    seq = data.get("sequence")
    if not isinstance(seq, list) or not all(isinstance(x, str) for x in seq):
        raise ValueError("Planner JSON missing a valid 'sequence' array")

    # Filter to known nodes only
    seq = [n for n in seq if n in registry]
    if not seq:
        raise ValueError("Planner produced empty/unknown sequence")

    return {"sequence": seq, "reason": data.get("reason"), "raw": resp.content}


def plan_flow_sequence(intent: str, memory_context: MemoryContext, registry: Dict[str, NodeSpec], defaults: Dict[str, List[str]], temperature: float = 0.0, parameters: Dict[str, Any] | None = None) -> Tuple[List[str], bool, Dict[str, Any]]:
    """Try LLM-based proposal first; fall back to deterministic defaults on failure.
    Returns: (sequence, used_llm, meta)
    """
    try:
        result = propose_sequence_llm(intent, memory_context, registry, temperature, parameters)
        return result["sequence"], True, result
    except Exception as e:
        logger.warning("LLM planner failed; falling back. error=%s", e)
        seq = defaults.get(intent) or []
        return seq, False, {"error": str(e)}


def _summarize_memory_context(memory_context: MemoryContext) -> Dict[str, Any]:
    """Local summarizer to avoid importing underscore-private utils."""
    try:
        return {
            "user_id": getattr(memory_context, "user_id", None),
            "recent_events": [getattr(m, "content", {}) for m in (getattr(memory_context, "episodic", []) or [])[:3]],
            "preferences": [getattr(m, "content", {}) for m in (getattr(memory_context, "semantic", []) or [])[:3]],
        }
    except Exception:
        return {"user_id": getattr(memory_context, "user_id", None)}

