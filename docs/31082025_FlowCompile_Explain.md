### FlowCompiler (plain-English walkthrough)

Think of the module as four pieces:

A) NodeSpec

A small metadata record for each node/tool so both the LLM and the compiler understand what exists and how it fits:

name, type, description, inputs, outputs

dependencies: what must run before it

entrypoint: the callable to execute (or an import path string to resolve later)

Optional runtime hints: latency_ms, cost_estimate, memory

Why? The LLM returns names; the compiler uses the registry of NodeSpecs to wire everything correctly and safely.

B) GraphBuilder protocol (+ InMemoryGraphBuilder)

A tiny interface the compiler targets: add_node, add_edge, build.

InMemoryGraphBuilder is a test/dry-run implementation that just records nodes + edges.

Later we plug in LangGraphBuilderAdapter that wraps a real StateGraph.

This is the seam that lets us test without LangGraph, then switch to LangGraph for real runs.

C) CompileOptions

Toggles + hooks:

insert_missing_dependencies: if a planned node has deps, auto-insert them.

verify_cycles, verify_all_nodes_exist: guardrails.

pre_hook(node, state) / post_hook(node, state, out): for logging/metrics/tracing.

callable_resolver(NodeSpec): central place to resolve the executable callable (supports "module:attr" later).

D) FlowCompiler.compile(plan, registry, options)

What it does step-by-step:

Validate the plan: make sure every named node exists (or raise MissingNodeError).

Resolve order with dependencies (topological expansion using DFS):

Ensures every dependency is placed before the node that needs it.

Optionally auto-inserts missing deps.

Detects cycles early and raises CycleError with a helpful path.

Build graph using the provided builder:

For each NodeSpec, resolve the callable (direct callable or "module:attr").

Wrap each callable with pre/post hooks (for observability).

add_node() all nodes in the resolved order.

Add linear edges (S → S+1). (Branching/conditions can be a v0.2 add-on.)

Return whatever the builder’s build() returns
(for InMemoryGraphBuilder: a dict of { nodes, edges }; for LangGraph: a runnable graph).

Example usage (what’s happening):

We define three fake node functions: plan_outline, user_confirm_a, task_generation.

We define a REGISTRY mapping names → NodeSpec (with deps: confirm depends on outline, etc.).

We create FlowCompiler(InMemoryGraphBuilder) and call:

compiler.compile(
  plan=["plan_outline", "user_confirm_a", "task_generation"],
  registry=REGISTRY,
  options=CompileOptions(pre_hook=..., post_hook=...)
)


The compiler:

checks the names,

expands dependencies (plan_outline → user_confirm_a → task_generation),

wires edges [("plan_outline","user_confirm_a"), ("user_confirm_a","task_generation")],

returns a compiled structure you can inspect or execute (if this were the LangGraph adapter, you’d get back a runnable LangGraph object).


### “Tools” vs “Nodes” vs “Agent” vs “Graph” (what’s what?)

Graph (LangGraph): the orchestra/conductor. It defines a control-flow structure (nodes + edges). It runs deterministically (or semi-dynamically via routers), with state passed between steps.

Nodes: the musicians. Each node is an executable step (a function / callable class) that takes state and returns updated state/outputs. Examples: plan_outline, task_generation, calendarization. Nodes can do anything inside—call APIs, hit DB, or even call tools.

Agent: an LLM loop that decides which tool to call next based on the conversation—classic “tool calling / ReAct” style. This is typical in LangChain/OpenAI tools world. It’s less deterministic: the LLM chooses actions each step.

Tools: the instruments exposed to an Agent. They’re simple, stateless callables with a schema (think: “search_web”, “get_weather”, “find_meeting_slots”). They are invoked via LLM tool-calling. In LangChain, you often see @tool decorators.

How they relate:

You can have a Graph of Nodes where some nodes internally call tools, or a Node that wraps a small Agent that in turn chooses among tools.

We keep tools under agent/ to keep the conceptual boundary: tools are agent-facing capabilities; nodes are graph steps. It avoids mixing two orchestration paradigms in one folder.

So: different paradigms, compatible layers. Our default path is graph-first (nodes, compiler). If/when we need an agent, it lives beside the graph and can be called from a node.