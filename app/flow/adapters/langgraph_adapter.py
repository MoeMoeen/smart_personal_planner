# app/flow/adapters/langgraph_adapter.py
# # implements GraphBuilder on top of LangGraph StateGraph



# =============================
# app/flow/adapters/langgraph_adapter.py
# =============================
from __future__ import annotations
from typing import Any, Callable
from langgraph.graph import StateGraph, END

class LangGraphBuilderAdapter:
    """GraphBuilder-compatible adapter around LangGraph's StateGraph.

    - Sets entry point on the first added node (typical for linear flows).
    - `add_edge(src, "END")` is supported and maps to `END`.
    - `build()` returns the compiled, runnable graph.
    """

    def __init__(self, state_type: type):
        self._sg = StateGraph(state_type)
        self._entry_set = False

    def add_node(self, name: str, func: Callable[..., Any]) -> None:
        self._sg.add_node(name, func)
        if not self._entry_set:
            self._sg.set_entry_point(name)
            self._entry_set = True

    def add_edge(self, src: str, dst: str) -> None:
        if isinstance(dst, str) and dst.lower() == "end":
            self._sg.add_edge(src, END)
        else:
            self._sg.add_edge(src, dst)

    def build(self):
        return self._sg.compile()
