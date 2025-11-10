"""
LangGraph ReAct agent scaffolding for the planning node (Phase 7 Step 7).

- Wraps existing planning tools as LangChain StructuredTool instances
- Provides a factory to create a ReAct agent with SqliteSaver checkpoints
- Lazily initializes the LLM; safe to import without API keys

This is a scaffold: the controller still calls tools directly. Wiring the
controller to drive the inner agent will be completed after prompts and
confidence/budget plumbing are finalized.
"""

from __future__ import annotations

from typing import Any, List, Callable, cast
import os

# Safe imports (guarded)
try:
    from langgraph.prebuilt import create_react_agent  # type: ignore
except ImportError:  # pragma: no cover
    create_react_agent = None  # type: ignore
    print("langgraph.prebuilt.create_react_agent not available")

try:
    from langgraph.checkpoint.sqlite import SqliteSaver  # type: ignore
except ImportError:  # pragma: no cover
    SqliteSaver = None  # type: ignore
    print("langgraph.checkpoint.sqlite.SqliteSaver not available")

try:
    from langchain_core.tools import StructuredTool  # type: ignore
except ImportError:  # pragma: no cover
    StructuredTool = None  # type: ignore
    print("langchain_core.tools.StructuredTool not available")

try:
    from langchain_openai import ChatOpenAI  # type: ignore
except ImportError:  # pragma: no cover
    ChatOpenAI = None  # type: ignore
    print("langchain_openai.ChatOpenAI not available")

from pydantic import BaseModel

from app.cognitive.agents.planning_tools import (
    PatternSelectorTool,
    GrammarValidatorTool,
    SemanticCriticTool,
    OntologySnapshotTool,
    QCDecisionTool,
    NodeGeneratorTool,
    RoadmapBuilderTool,
    ScheduleGeneratorTool,
    PortfolioProbeTool,
    ApprovalHandlerTool,
    # Input schemas
    PatternSelectorInput,
    GrammarValidatorInput,
    SemanticCriticInput,
    QCDecisionInput,
    NodeGeneratorInput,
    RoadmapBuilderInput,
    ScheduleGeneratorInput,
    PortfolioProbeInput,
    ApprovalHandlerInput,
)
from app.config.llm_config import LLM_CONFIG
from app.cognitive.agents.prompts import create_policy_aware_system_prompt


def _make_structured_tool(
    tool_name: str,
    description: str,
    input_model: type[BaseModel],
    run_fn: Callable[[BaseModel], Any],
):
    """Create a LangChain StructuredTool from a Pydantic input model and a run function."""
    if StructuredTool is None:
        return None

    def _func(**kwargs):
        params = input_model(**kwargs)
        result = run_fn(params)
        # return JSON-serializable output
        return result.model_dump()

    st = StructuredTool.from_function(
        func=_func,
        name=tool_name,
        description=description,
        args_schema=input_model,
    )
    return st


def get_structured_tools() -> List[Any]:
    """Return structured tools for use by a ReAct agent.

    Note: Underlying tool logic remains minimal/stubbed for some tools.
    """
    class EmptyArgs(BaseModel):
        pass

    mapping = [
        (
            PatternSelectorTool(),
            PatternSelectorInput,
        ),
        (
            NodeGeneratorTool(),
            NodeGeneratorInput,
        ),
        (
            GrammarValidatorTool(),
            GrammarValidatorInput,
        ),
        (
            OntologySnapshotTool(),
            EmptyArgs,
        ),
        (
            SemanticCriticTool(),
            SemanticCriticInput,
        ),
        (
            QCDecisionTool(),
            QCDecisionInput,
        ),
        (
            RoadmapBuilderTool(),
            RoadmapBuilderInput,
        ),
        (
            ScheduleGeneratorTool(),
            ScheduleGeneratorInput,
        ),
        (
            PortfolioProbeTool(),
            PortfolioProbeInput,
        ),
        (
            ApprovalHandlerTool(),
            ApprovalHandlerInput,
        ),
    ]
    tools: List[Any] = []
    for entry in mapping:
        tool, input_model = entry
        st = _make_structured_tool(
            tool_name=getattr(tool, "name", tool.__class__.__name__),
            description=getattr(tool, "description", "tool"),
            input_model=input_model,
            run_fn=tool.run,
        )
        if st is not None:
            tools.append(st)
    return tools


def get_llm(lazy: bool = True):
    """Return an LLM instance if available, otherwise None.

    If OPENAI_API_KEY is missing or lazy is True, this returns a callable to
    construct the model later to avoid import-time failures.
    """
    if ChatOpenAI is None:
        return None

    def _factory():
        model = LLM_CONFIG.get("model", "gpt-4o")
        temperature = float(LLM_CONFIG.get("temperature", 0.1))
        Chat = cast(Any, ChatOpenAI)
        return Chat(model=model, temperature=temperature)

    return _factory if lazy else _factory()


def get_checkpointer(db_path: str = "data/agent_conversations.db"):
    """Return a SqliteSaver checkpointer if available, else None.

    Creates the directory if missing. Safe to import in environments without
    sqlite checkpoint extras installed (returns None).
    """
    if SqliteSaver is None:
        return None
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return SqliteSaver(db_path)  # type: ignore


def create_planning_react_agent(
    db_path: str = "data/agent_conversations.db", 
    system_prompt: str | None = None,
    interaction_policy: object | None = None
) -> tuple[Any | None, dict]:
    """Create a ReAct agent with our structured tools and sqlite checkpoints.

    Args:
        db_path: Path to SQLite database for conversation checkpoints
        system_prompt: Custom system prompt (overrides policy-generated prompt)
        interaction_policy: InteractionPolicy instance to customize agent behavior
        
    Returns:
        tuple (graph, config) where graph is a Runnable-like agent and
        config includes the checkpointer and optional thread_id/namespace guidance.
        If dependencies are unavailable, returns (None, {}).
    """
    if create_react_agent is None:
        return None, {}
    tools = get_structured_tools()
    llm_factory = get_llm(lazy=True)
    if llm_factory is None:
        return None, {}
    checkpointer = get_checkpointer(db_path)
    cra = cast(Any, create_react_agent)
    kwargs = {"checkpointer": checkpointer}
    
    # Generate policy-aware system prompt if no custom prompt provided
    if system_prompt:
        final_prompt = system_prompt
    else:
        final_prompt = create_policy_aware_system_prompt(interaction_policy)
    
    # Some versions of create_react_agent accept state_modifier for system prompt
    kwargs["state_modifier"] = final_prompt
    graph = cra(
        llm_factory(),
        tools=tools,
        **kwargs,
    )
    config = {
        "checkpointer": checkpointer,
        # The caller should set a proper thread_id and checkpoint_ns per session
        "config": {
            "configurable": {
                "thread_id": None,
                "checkpoint_ns": "planning_agent",
            }
        },
    }
    return graph, config
