# cognitive/langgraph_flow/flow_compiler.py
# flow_compiler.py  # stateless: sequence -> graph (edges, checks, hooks)

"""
Stateless FlowCompiler that takes a node registry + planned sequence and returns a compiled graph
object (builder.build()) with edges wired in the correct order. Designed to work with LangGraph via
an adapter, but decoupled for testability. Includes hooks for observability and guardrails for
cycles/missing nodes/dependencies.

This version includes OPTIONAL conditional routers: you can attach a router callable to any node.
If a node has a router, the compiler will install it (via the builder) instead of a linear edge.

Why this design?
- Stateless: easy to reuse and test; no hidden global state.
- Registry-driven (NodeSpec below): LLM (or deterministic map) can propose sequences by name; compiler resolves details.
- Safe-by-default: verifies nodes exist, inserts missing dependencies (optional), checks for cycles.
- Extensible: pre/post hooks for logging/metrics/tracing/observability; pluggable GraphBuilder adapter.
- Deterministic: stable ordering with dependency-first resolution, then planned sequence.
- Dependency expansion (deps run before dependents)
- Optional: conditional_routers={"user_confirm_a": route_after_confirm_a}
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Protocol, Sequence, Set, Tuple, runtime_checkable
import logging

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------------------
# Public types
# --------------------------------------------------------------------------------------

@dataclass(frozen=True)
class NodeSpec:
    """Metadata that the LLM and compiler both understand.

    name: Unique node name. Must be registry key.
    type: "node" | "tool" | other domain-specific type tags.
    description: Human-readable description for LLM planning & docs.
    inputs/outputs: Informational; can be leveraged for validation later.
    dependencies: Nodes that MUST run before this node.
    entrypoint: Callable or import path string to resolve a callable at compile time.
    latency_ms, cost_estimate, memory: Optional metadata for planning/observability.
    """

    name: str
    type: str
    description: str
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    entrypoint: Optional[Callable[..., Any]] = None
    entrypoint_path: Optional[str] = None  # e.g., "app.nodes.plan:planning_node" # "module:attr"
    latency_ms: Optional[int] = None
    cost_estimate: Optional[float] = None
    memory: Optional[str] = None


Registry = Dict[str, NodeSpec]


@dataclass
class CompileOptions:
    """
    Toggles & hooks to customize compilation behavior.
    [NEW] conditional_routers: mapping of node_name -> router(state) -> str (next node name)

    TODO: write all the options logic via corresponding methods.
    """

    insert_missing_dependencies: bool = True
    verify_cycles: bool = True
    verify_all_nodes_exist: bool = True
    pre_hook: Optional[Callable[[str, Dict[str, Any]], None]] = None
    post_hook: Optional[Callable[[str, Dict[str, Any], Any], None]] = None
    callable_resolver: Optional[Callable[[NodeSpec], Callable[..., Any]]] = None
    conditional_routers: Optional[Dict[str, Callable[[Any], str]]] = None  # <— NEW

# --------------------------------------------------------------------------------------
# GraphBuilder protocol + lightweight in-memory builder for tests/examples
# --------------------------------------------------------------------------------------

@runtime_checkable
class GraphBuilder(Protocol):
    def add_node(self, name: str, func: Callable[..., Any]) -> None: ...
    def add_edge(self, src: str, dst: str) -> None: ...
    def build(self) -> Any: ...

# in-memory test/dry-run builder to make it testable immediately; in prod we swap it for a LangGraphBuilderAdapter.
class InMemoryGraphBuilder:
    """
    Minimal builder that records nodes and edges for tests and dry-runs.
    The resulting `build()` returns a dict with `nodes` & `edges` lists.
    Later we plug in LangGraphBuilderAdapter that wraps a real StateGraph.
    This is the seam that lets us test without LangGraph, then switch to LangGraph for real runs.
    """

    def __init__(self) -> None:
        self.nodes: Dict[str, Callable[..., Any]] = {}
        self.edges: List[Tuple[str, str]] = []
        self.routers: Dict[str, Callable[[Any], str]] = {}

    def add_node(self, name: str, func: Callable[..., Any]) -> None:
        self.nodes[name] = func

    def add_edge(self, src: str, dst: str) -> None:
        if (src, dst) not in self.edges:
            self.edges.append((src, dst))

    def add_conditional_router(self, node: str, route_func: Callable[[Any], str]) -> None:
        self.routers[node] = route_func

    def build(self) -> Dict[str, Any]:
        return {"nodes": self.nodes, "edges": list(self.edges), "routers": dict(self.routers)}


# --------------------------------------------------------------------------------------
# Exceptions
# --------------------------------------------------------------------------------------

class FlowCompilerError(Exception):
    pass


class MissingNodeError(FlowCompilerError):
    def __init__(self, missing: Iterable[str]):
        super().__init__(f"Missing nodes in registry: {sorted(set(missing))}")
        self.missing = set(missing)


class CycleError(FlowCompilerError):
    def __init__(self, cycle_path: List[str]):
        super().__init__(f"Cycle detected involving: {' -> '.join(cycle_path)}")
        self.cycle_path = cycle_path


# --------------------------------------------------------------------------------------
# FlowCompiler
# --------------------------------------------------------------------------------------

class FlowCompiler:
    """Compile a planned sequence into a concrete, executable graph.

    Usage (with in-memory builder):
        compiler = FlowCompiler(builder_factory=InMemoryGraphBuilder)
        graph = compiler.compile(
            plan=["plan_outline", "user_confirm_a", "task_generation"],
            registry=REGISTRY,
            options=CompileOptions(
                pre_hook=lambda node, state: logger.info("→ %s", node),
                post_hook=lambda node, state, out: logger.info("✓ %s", node),
            ),
        )

    To integrate with LangGraph, provide a `builder_factory` that returns a wrapper implementing
    GraphBuilder (e.g., `LangGraphBuilderAdapter(StateGraph(initial_state))`).
    """

    def __init__(self, builder_factory: Callable[[], GraphBuilder]) -> None:
        self.builder_factory = builder_factory

    # ----- public API ---------------------------------------------------------
    def compile(
        self,
        plan: Sequence[str],
        registry: Registry,
        options: Optional[CompileOptions] = None,
    ) -> Any:
        if options is None:
            options = CompileOptions()

        logger.debug("Compiling plan: %s", list(plan))
        plan_list = list(plan)

        if options.verify_all_nodes_exist:
            missing = [n for n in plan_list if n not in registry]
            if missing:
                raise MissingNodeError(missing)

        ordered = self._resolve_order(plan_list, registry, insert_missing=options.insert_missing_dependencies)
        logger.debug("Resolved ordered sequence: %s", ordered)

        # Optional cycle check on dependency edges
        if options.verify_cycles:
            self._verify_no_cycles(ordered, registry)

        builder = self.builder_factory()

        # Add nodes
        for name in ordered:
            spec = registry.get(name)
            if spec is None:
                # Should be unreachable if verify_all_nodes_exist=True and dependencies were in registry.
                raise MissingNodeError([name])
            func = self._resolve_callable(spec, options)
            wrapped = self._wrap_with_hooks(name, func, options)
            builder.add_node(name, wrapped)

        # Add edges or routers: https://docs.google.com/document/d/1YE0nNw6qEGp56JzPdLklilnbDAMSdAspQTQnwIKrmv8/edit?tab=t.dkxl7jj1w70f#heading=h.g9l2sy6vx82b
        cond = options.conditional_routers or {}
        for i, src in enumerate(ordered):
            # If this node has a router, install it instead of a single linear edge
            if src in cond and hasattr(builder, "add_conditional_router"):
                # install router (it decides the next node at runtime)
                getattr(builder, "add_conditional_router")(src, cond[src])
                continue

            # Otherwise add linear edge to next node (if any)
            if i < len(ordered) - 1:
                builder.add_edge(src, ordered[i + 1])

        compiled = builder.build()
        logger.debug("Compilation complete. Nodes=%d", len(ordered))
        return compiled

    # ----- internals ----------------------------------------------------------
    def _resolve_order(self, plan: List[str], registry: Registry, insert_missing: bool) -> List[str]:
        """Topological expansion: Ensure all dependencies appear before dependents.

        Algorithm: DFS over dependencies for each planned node (classic topo expansion). De-dupe while
        preserving first occurrence order. If `insert_missing=False`, we only verify relative order and
        do NOT add unplanned dependencies—missing deps will raise MissingNodeError.
        """
        ordered: List[str] = []
        seen: Set[str] = set()
        temp: Set[str] = set()

        def dfs(node: str) -> None:
            if node in seen:
                return
            if node in temp:
                # cycle in dependency chain
                cycle_path = list(temp) + [node]
                raise CycleError(cycle_path)
            temp.add(node)

            spec = registry.get(node)
            if spec is None:
                raise MissingNodeError([node])

            for dep in spec.dependencies:
                if dep not in registry:
                    raise MissingNodeError([dep])
                dfs(dep)

            temp.remove(node)
            if node not in seen:
                seen.add(node)
                ordered.append(node)

        # If we are not inserting missing dependencies, we still need to validate all deps are present
        # in the *plan* before their dependents.
        if not insert_missing:
            missing_deps: Set[str] = set()
            plan_set = set(plan)
            for n in plan:
                spec = registry.get(n)
                if spec is None:
                    raise MissingNodeError([n])
                for d in spec.dependencies:
                    if d not in plan_set:
                        missing_deps.add(d)
            if missing_deps:
                raise MissingNodeError(sorted(missing_deps))

        for n in plan:
            if insert_missing:
                # Full dependency expansion
                dfs(n)
            else:
                # Only order the planned nodes; deps are guaranteed to be present in plan by above check
                pass

        if not insert_missing:
            # Maintain plan order strictly if we're not inserting deps
            return list(dict.fromkeys(plan))  # de-duplicate while preserving order

        # If we inserted dependencies via DFS, `ordered` includes deps-before-nodes; de-dup already handled
        return ordered

    def _verify_no_cycles(self, ordered: List[str], registry: Registry) -> None:
        """
        Detect cycles limited to dependency graph (not runtime conditional edges).
        Cycle check using Kahn's algorithm over dependency edges.
        """
        # Build adjacency from dependencies only
        adj: Dict[str, List[str]] = {n: [] for n in ordered}
        indeg: Dict[str, int] = {n: 0 for n in ordered}
        for n in ordered:
            spec = registry[n]
            for d in spec.dependencies:
                # Only consider dependencies that are in ordered list
                if d in adj:
                    adj[d].append(n)
                    indeg[n] += 1

        # Kahn's algorithm
        q: List[str] = [n for n, deg in indeg.items() if deg == 0]
        visited: List[str] = []
        while q:
            cur = q.pop(0)
            visited.append(cur)
            for nxt in adj[cur]:
                indeg[nxt] -= 1
                if indeg[nxt] == 0:
                    q.append(nxt)
        if len(visited) != len(ordered):
            # Find nodes with indeg>0 to report a cycle
            cyc_nodes = [n for n, deg in indeg.items() if deg > 0]
            raise CycleError(cyc_nodes)

    def _resolve_callable(self, spec: NodeSpec, options: CompileOptions) -> Callable[..., Any]:
        if options.callable_resolver:
            func = options.callable_resolver(spec)
            if not callable(func):
                raise FlowCompilerError(f"Resolved entrypoint for {spec.name} is not callable: {func}")
            return func
        if spec.entrypoint is not None:
            if not callable(spec.entrypoint):
                raise FlowCompilerError(f"NodeSpec.entrypoint for {spec.name} is not callable")
            return spec.entrypoint
        if spec.entrypoint_path:
            module_path, _, attr = spec.entrypoint_path.partition(":")
            if not module_path or not attr:
                raise FlowCompilerError(
                    f"Invalid entrypoint_path for {spec.name}: {spec.entrypoint_path}. Expected 'module:attr'."
                )
            mod = __import__(module_path, fromlist=[attr])
            func = getattr(mod, attr)
            if not callable(func):
                raise FlowCompilerError(f"Resolved entrypoint '{spec.entrypoint_path}' for {spec.name} is not callable")
            return func
        raise FlowCompilerError(f"No callable could be resolved for node '{spec.name}'")

    def _wrap_with_hooks(
        self,
        name: str,
        func: Callable[..., Any],
        options: CompileOptions,
    ) -> Callable[..., Any]:
        pre = options.pre_hook
        post = options.post_hook

        def wrapped(state: Dict[str, Any]) -> Any:
            if pre:
                try:
                    pre(name, state)
                except Exception as e:
                    logger.warning("Pre-hook for %s raised: %s", name, e)
            out = func(state)
            if post:
                try:
                    post(name, state, out)
                except Exception as e:
                    logger.warning("Post-hook for %s raised: %s", name, e)
            return out

        wrapped.__name__ = f"wrapped_{getattr(func, '__name__', name)}"
        return wrapped


# --------------------------------------------------------------------------------------
# Example usage (can be moved to tests later)
# --------------------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    # Fake node functions
    def plan_outline(state: Dict[str, Any]) -> Dict[str, Any]:
        state.setdefault("execution_history", []).append({"node": "plan_outline"})
        state["last_node"] = "plan_outline"
        return state

    def user_confirm_a(state: Dict[str, Any]) -> Dict[str, Any]:
        state.setdefault("execution_history", []).append({"node": "user_confirm_a"})
        state["last_node"] = "user_confirm_a"
        return state

    def task_generation(state: Dict[str, Any]) -> Dict[str, Any]:
        state.setdefault("execution_history", []).append({"node": "task_generation"})
        state["last_node"] = "task_generation"
        return state

    REGISTRY: Registry = {
        "plan_outline": NodeSpec(
            name="plan_outline",
            type="node",
            description="Create a high-level plan outline",
            outputs=["outline"],
            entrypoint=plan_outline,
        ),
        "user_confirm_a": NodeSpec(
            name="user_confirm_a",
            type="node",
            description="Ask user to confirm or revise the outline",
            inputs=["outline"],
            dependencies=["plan_outline"],
            entrypoint=user_confirm_a,
        ),
        "task_generation": NodeSpec(
            name="task_generation",
            type="node",
            description="Expand outline into tasks",
            inputs=["outline"],
            dependencies=["user_confirm_a"],
            entrypoint=task_generation,
        ),
    }

    compiler = FlowCompiler(builder_factory=InMemoryGraphBuilder)
    compiled = compiler.compile(
        plan=["plan_outline", "user_confirm_a", "task_generation"],
        registry=REGISTRY,
        options=CompileOptions(
            pre_hook=lambda n, s: logger.info("→ %s", n),
            post_hook=lambda n, s, o: logger.info("✓ %s", n),
        ),
    )

    print("NODES:", list(compiled["nodes"].keys()))
    print("EDGES:", compiled["edges"])
