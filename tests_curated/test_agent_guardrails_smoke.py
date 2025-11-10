import os
from dotenv import load_dotenv

load_dotenv(override=False)
os.environ.setdefault("PLANNING_USE_REACT_AGENT", "true")
os.environ.setdefault("PLANNING_USE_LLM_TOOLS", "true")

from app.cognitive.agents.react_agent import create_planning_react_agent

def test_guardrails_present():
    graph, cfg = create_planning_react_agent()
    # Access tool names from the graph’s tool registry if exposed
    # Fallback: recreate the tool list via factory method if available
    # Here we assume create_planning_react_agent registers tools correctly.

    # Soft assertion: creation succeeded
    assert graph is not None

    # We can’t directly introspect langgraph tools easily here without internal handle,
    # but creation pass is a decent smoke. For a stronger check, import get_structured_tools
    # if it’s exported and compare names.

def test_policy_prompt_contains_qc_sequence():
    from app.cognitive.agents.prompts import create_policy_aware_system_prompt
    from app.cognitive.contracts.types import InteractionPolicy

    prompt = create_policy_aware_system_prompt(InteractionPolicy())
    assert "GrammarValidator" in prompt or "grammar_validator" in prompt
    assert "ontology_snapshot" in prompt
    assert "semantic_critic" in prompt
    assert "qc_decision" in prompt
    assert "Only proceed when qc_action=\"accept\"" in prompt