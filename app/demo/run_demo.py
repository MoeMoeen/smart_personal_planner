# app/demo/run_demo.py



# =============================
# app/demo/run_demo.py  (optional local smoke test)
# =============================
from __future__ import annotations
from typing import Any

from app.flow.flow_compiler import FlowCompiler, CompileOptions
from app.flow.adapters.langgraph_adapter import LangGraphBuilderAdapter
from app.flow.registry import NODE_REGISTRY
from app.flow.intent_routes import DEFAULT_FLOW_REGISTRY
from app.flow.planner import plan_sequence
from app.cognitive.contracts.types import MemoryContext

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



class GraphState(dict):
    pass

if __name__ == "__main__":
    intent = "create_new_plan"
    mem = MemoryContext(user_id="demo-user", episodic=[], semantic=[], procedural=[])

    sequence, used_llm, meta = plan_sequence(intent, mem, NODE_REGISTRY, DEFAULT_FLOW_REGISTRY)
    print("Planner used LLM:", used_llm)

    compiler = FlowCompiler(lambda: LangGraphBuilderAdapter(GraphState))
    graph = compiler.compile(plan=sequence, registry=NODE_REGISTRY, options=CompileOptions())

    initial = GraphState(goal="Planner Demo Goal")
    result = graph.invoke(initial)
    print("FINAL STATE:")
    print(result)
