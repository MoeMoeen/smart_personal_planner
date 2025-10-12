# app/flow/adapters/langgraph_adapter.py
# # implements GraphBuilder on top of LangGraph StateGraph



# =============================
# app/flow/adapters/langgraph_adapter.py
# =============================
from __future__ import annotations
from typing import Any, Callable, Dict, Tuple, Union, Hashable
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

    def add_conditional_router(
        self,
        node: str,
        route: Union[Callable[[Any], str], Dict[str, str], Tuple[Callable[[Any], str], Dict[str, str]]],
    ) -> None:
        """
        Install a router at `node`.
        - If a function is provided: it must be (state) -> next_node_name and we pass it directly.
        - If a dict mapping is provided: we install a key router that returns keys, with a mapping of key->dst.
          In this case, the route_func must be provided as a function via 'router' kwarg and mapping via 'conditional_map'.
        """
        if isinstance(route, tuple):
            router_func, mapping = route
            mapping_cast: Dict[Hashable, str] = {k: v for k, v in mapping.items()}
            self._sg.add_conditional_edges(node, router_func, mapping_cast)
        elif isinstance(route, dict):
            # Mapping router expects the node function to return a key present in mapping
            mapping: Dict[str, str] = route
            def key_router(state: Any) -> str:
                # Expect state to contain a key 'route_key' set by the node
                key = getattr(state, "route_key", None) if hasattr(state, "route_key") else state.get("route_key")
                if key is None:
                    # fallback to first mapping key
                    return next(iter(mapping.keys()))
                return str(key)
            # Cast mapping to satisfy type checkers expecting Hashable keys
            mapping_cast: Dict[Hashable, str] = {k: v for k, v in mapping.items()}
            self._sg.add_conditional_edges(node, key_router, mapping_cast)
        else:
            self._sg.add_conditional_edges(node, route)

    def build(self):
        return self._sg.compile()
