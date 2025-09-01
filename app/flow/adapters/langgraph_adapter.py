# app/flow/adapters/langgraph_adapter.py
# # implements GraphBuilder on top of LangGraph StateGraph



# =============================
# app/flow/adapters/langgraph_adapter.py
# =============================
from __future__ import annotations
from typing import Any, Callable
from langgraph.graph import StateGraph, END

class LangGraphBuilderAdapter:
    """
    GraphBuilder-compatible adapter around LangGraph's StateGraph.

    - First added node becomes entry point
    - add_edge supports "END"
    - add_conditional_router(node, route_func): installs a router using add_conditional_edges
      The router is a callable(state) -> str that returns the NEXT node name.
      (If your LangGraph version requires a key-to-destination mapping, see the note below.)
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

    def add_conditional_router(self, node: str, route_func: Callable[[Any], str]) -> None:
        """
        Install a router at `node` that returns the next node name.
        If your LangGraph version expects (router, mapping), you can wrap like:
            self._sg.add_conditional_edges(node, lambda s: route_func(s), {})
        and ensure all possible destinations are already added as nodes.
        """
        self._sg.add_conditional_edges(node, route_func)

    def build(self):
        return self._sg.compile()
