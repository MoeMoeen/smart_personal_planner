# app/orchestration/message_handler.py

import logging
from app.cognitive.brain.intent_recognition_node import detect_intent
from app.flow.flow_planner_llm import plan_flow_sequence
from app.flow.flow_compiler import FlowCompiler, CompileOptions
from app.flow.adapters.langgraph_adapter import LangGraphBuilderAdapter
from app.flow.node_registry import NODE_REGISTRY
from app.cognitive.state.graph_state import GraphState
from app.cognitive.brain.intent_registry_routes import DEFAULT_FLOW_REGISTRY
# from app.flow.conditions import route_after_confirm_a  # router (legacy, not used in agentic path)

logger = logging.getLogger(__name__)

async def handle_user_message(user_id: int, user_message: str, memory_context) -> str:
    """
    Orchestrates one user message end-to-end:
    1. Detect intent
    2. Plan flow sequence (LLM or fallback)
    3. Compile graph with routers
    4. Run graph
    5. Return response_text (for Telegram)
    """

    # Step A: intent recognition
    intent_result = detect_intent(user_message, memory_context)
    intent = intent_result.intent
    params = intent_result.parameters

    # Step B: plan flow sequence
    sequence, used_llm, meta = plan_flow_sequence(
        intent=intent,
        memory_context=memory_context,
        registry=NODE_REGISTRY,
        defaults=DEFAULT_FLOW_REGISTRY,
        parameters=params,
    )
    if not sequence:
        return "❌ Sorry, I couldn’t figure out a valid flow plan for that."

    # Step C: compile graph with routers
    compiler = FlowCompiler(lambda: LangGraphBuilderAdapter(GraphState))
    options = CompileOptions(
        conditional_routers={}
    )
    graph = compiler.compile(plan=sequence, registry=NODE_REGISTRY, options=options)

    # Step D: run graph
    state = GraphState(
        user_input=user_message,
        memory_context=memory_context,
        recognized_intent=intent_result.model_dump(),
    )
    result_state: GraphState = graph.invoke(state)

    # Step E: return formatted text
    if result_state.response_text:
        return result_state.response_text
    if result_state.plan_outline is not None:
        return f"📋 Plan Outline available (nodes: {len(result_state.plan_outline.nodes) if result_state.plan_outline.nodes else 0})."
    if result_state.schedule is not None:
        return f"🗓️ Schedule available (blocks: {len(result_state.schedule.blocks)})."
    if result_state.validation_result:
        return f"🔎 Validation:\n{result_state.validation_result}"

    return "🤖 I processed your request but didn’t generate a response."
