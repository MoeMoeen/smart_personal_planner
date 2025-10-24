# app/demo/run_demo.py
# =============================
# app/demo/run_demo.py  (optional local smoke test)
# =============================

from __future__ import annotations
from typing import Any

from app.flow.flow_compiler import FlowCompiler, CompileOptions
from app.flow.adapters.langgraph_adapter import LangGraphBuilderAdapter
from app.flow.node_registry import NODE_REGISTRY
from app.cognitive.brain.intent_registry_routes import get_flow_registry
from app.flow.flow_planner_llm import plan_flow_sequence
from app.cognitive.contracts.types import MemoryContext
from app.flow.conditions import route_after_confirm_a

# # Minimal GraphState stand-in for local test; replace with your real class
# class GraphState(dict):
#     pass

# if __name__ == "__main__":
#     # Fallback sequence for a known intent
#     sequence = DEFAULT_FLOW_REGISTRY["create_new_plan"][:3]  # take first 3 for this demo

#     compiler = FlowCompiler(lambda: LangGraphBuilderAdapter(GraphState))
#     graph = compiler.compile(plan=sequence, registry=NODE_REGISTRY, options=CompileOptions())

#     initial = GraphState(goal="Demo Goal")
#     result = graph.invoke(initial)
#     print("FINAL STATE:")
#     print(result)


# stand-in GraphState for demo
class GraphState(dict):
    pass

if __name__ == "__main__":
    intent = "create_new_plan"
    sequence = get_flow_registry()[intent][:3]  # ["plan_outline", "user_confirm_a", "task_generation"]

    # mem = MemoryContext(user_id="demo-user", episodic=[], semantic=[], procedural=[])

    # sequence, used_llm, meta = plan_sequence(intent, mem, NODE_REGISTRY, DEFAULT_FLOW_REGISTRY)
    # print("Planner used LLM:", used_llm)

    from app.flow.router import route_after_planning_result
    compiler = FlowCompiler(lambda: LangGraphBuilderAdapter(GraphState))
    options = CompileOptions(
        conditional_routers={
            "user_confirm_a": route_after_confirm_a,
            "planning_node": route_after_planning_result
        }
    )
    graph = compiler.compile(plan=sequence, registry=NODE_REGISTRY, options=options)

    initial = GraphState(goal="Planner Demo Goal")
    result = graph.invoke(initial)
    print("FINAL STATE:")
    print(result)
