# Phase 7 — ReAct Planning Agent (Final Design)

Status: Proposal ready for implementation (no code changes in this step)

Scope: Production-grade agentic planning node powered by LangGraph ReAct with explicit controller state machine, atomic tools, PatternSpec + RFC flow, InteractionPolicy (user style), checkpoints, budget controls, and quantitative confidence thresholds. Aligned with v1.2 (patterns/grammar/dual-axis) and v1.3 (MegaGraph + routing).

---

## 0) Non-negotiables

- Single source of truth: PlanOutline → Roadmap → Schedule (Pydantic contracts)
- Tools-only ReAct; free text is user-facing only
- Deterministic guardrails: a rule validator must pass before advancing stages
- Explicit controller state machine with hard caps (turns, time, budget)
- Observability-first: per-step trace + AdaptationLogEntry for structural changes
- Router semantics unchanged; planning node owns approvals and emits planning_status accordingly

---

## 1) Pattern policy (RFC flow)

- Step 1: Map to nearest canonical top-level pattern
  - {milestone_project, recurring_cycle, progressive_accumulation_arc, hybrid_project_cycle, strategic_transformation}
- Step 2: If awkward, propose a new subtype as `subtype="proposed:<name>"` with a concise RFC rationale
- Step 3: New top-level patterns require human approval; subtypes can be proposed and reviewed

Agent behavior:
- Emits closest pattern_type and subtype; if proposing, includes RFC text and confidence
- If asynchronous approval is needed, return planning_status="needs_clarification" with response_text and escalate_reason that clearly state the pending decision (RFC)
- Router remains unchanged; no new keys introduced

---

## 2) Controller state machine (outer loop)

States:
- COLLECT_CONTEXT → DRAFT_OUTLINE → VALIDATE_OUTLINE
- DRAFT_ROADMAP → VALIDATE_ROADMAP
- DRAFT_SCHEDULE → VALIDATE_SCHEDULE
- SEEK_APPROVAL → COMPLETE | NEEDS_CLARIFICATION | NEEDS_SCHED_ESCALATION | ABORTED

Transitions (examples):
- VALIDATE_OUTLINE: valid → DRAFT_ROADMAP; invalid (repairable) → DRAFT_OUTLINE (≤2 retries); invalid (fatal) → NEEDS_CLARIFICATION
- VALIDATE_SCHEDULE: infeasible (capacity/conflicts) → NEEDS_SCHED_ESCALATION

Hard caps (config):
- TURN_LIMIT=10, RETRY_LIMIT_PER_STAGE=2, WALL_TIME_SEC=45, BUDGET_PER_SESSION_USD=2.0, SOFT_BUDGET_PER_TURN_USD=0.30

Approval handling (separated):
- Agent produces artifacts then calls ApprovalHandler inside SEEK_APPROVAL
- If async/pause required: set planning_status="needs_clarification" and response_text with a single explicit CTA (e.g., "Reply 'approve' or 'propose changes: …'")

---

💡 What the Controller State Machine is

In our architecture, the controller is the “brain behind the brain.”
It sits above the ReAct agent and coordinates its workflow — deciding what stage of planning we’re in, what tool to use next, and when to stop or escalate.

You can think of it as the director of the movie, while the ReAct agent and its tools are the actors.


---

🧩 1. Context in our system

Our planning node (the agentic meganode) needs to move in a predictable, controlled sequence:

Collect context → Draft outline → Validate → Build roadmap → Validate → Build schedule → Validate → Seek approval → Done

Each of those bold steps is a state.

The controller state machine governs these transitions — it ensures the agent:

does not skip ahead (e.g., can’t build a schedule before validating outline),

handles validation failures gracefully (retry or clarify),

stops looping infinitely, and

knows when to escalate (e.g., to scheduling escalation or user clarification).

---

⚙️ 2. Technically: what it does

Formally, the controller:

Keeps track of the current state (COLLECT_CONTEXT, DRAFT_OUTLINE, etc.).

Decides what the next state should be based on the results returned by the tools or the agent.

Enforces caps (time, turns, retries, budget).

Writes observability traces (stage, confidence, violations, adaptations).

Updates the GraphState with new artifacts (PlanOutline, Roadmap, Schedule, etc.).

Determines when to exit (complete, clarification, escalation, or abort).


It’s implemented as a finite state machine — think of it as a table of “if-then” rules.


---

🧭 3. Example transition map

STATE_TRANSITIONS = {
    "COLLECT_CONTEXT": {
        "sufficient_context": "DRAFT_OUTLINE",
        "needs_clarification": "NEEDS_CLARIFICATION"
    },
    "DRAFT_OUTLINE": {
        "success": "VALIDATE_OUTLINE",
        "low_confidence": "COLLECT_CONTEXT",
        "fatal_error": "ABORTED"
    },
    "VALIDATE_OUTLINE": {
        "valid": "DRAFT_ROADMAP",
        "invalid_retryable": "DRAFT_OUTLINE",
        "invalid_fatal": "NEEDS_CLARIFICATION"
    },
    "VALIDATE_SCHEDULE": {
        "valid": "SEEK_APPROVAL",
        "infeasible": "NEEDS_SCHED_ESCALATION"
    },
    "SEEK_APPROVAL": {
        "approved": "COMPLETE",
        "rejected": "DRAFT_OUTLINE",
        "no_response": "NEEDS_CLARIFICATION"
    }
}

So each step calls a tool or agent and returns a result like "valid", "invalid_retryable", "needs_clarification", etc.
The controller checks this dictionary and jumps to the next appropriate state.


---

🔁 4. Inner vs Outer loops

We actually have two nested loops:

Outer loop = Controller state machine

→ Handles stages like “Draft”, “Validate”, “Seek approval”.
→ Uses the rules above to move forward, retry, or escalate.

Inner loop = ReAct agent

→ Within a given stage (e.g., “Draft Outline”), the agent may use several tools (PatternSelector, NodeGenerator, etc.) to complete its task.

So:

Controller: "We’re in DRAFT_OUTLINE state."
→ Runs ReAct agent with PatternSelector + NodeGenerator tools.
→ Agent outputs: success, low confidence, or error.
→ Controller decides next state based on that result.


---

🛡️ 5. Why this design matters

Without a controller, a ReAct agent can wander — it might:

Overthink or loop endlessly,

Forget validation rules,

Produce half-baked artifacts,

Skip critical steps.


With the controller: ✅ The flow is deterministic, auditable, and debuggable.
✅ Failures are handled predictably (retry vs escalate).
✅ Every stage is logged with reasoning and confidence.
✅ You can visualize the entire process as a simple flowchart.


---

🧠 6. In plain English (metaphor)

Imagine your planner AI is like an executive assistant building your plan.

The controller is the project manager who says:

> “Okay, we gathered enough info. Now generate a draft outline. Done? Validate it. All good? Move to roadmap.”



The tools are the specialists (pattern analyst, grammar checker, scheduler).

The ReAct agent is the coordinator of those specialists.

The controller ensures the whole team moves through the steps in order and on time.


---

✅ 7. Summary

Role	Responsibility

Controller (state machine)	Decides stage progression, retries, or escalation.
ReAct agent	Executes atomic tools to complete the current stage.
Tools	Perform atomic operations (select pattern, validate, build schedule, etc.).
Router	Handles post-agentic branching (e.g., to world model or scheduling escalation).
GraphState	Shared memory containing current plan, context, approvals, etc.


---

## 3) PatternSpec (first-class) and placements

PatternSpec fields:
- pattern_type (canonical top-level)
- subtype?: str (may be "proposed:<name>")
- variant?: str
- confidence?: float
- introduced_by: {system|user_feedback|ai_adaptation}
- source_pattern?: str (for audits when proposing a subtype)
- rfc?: str (short rationale when proposing a new subtype)

Placements:
- PlanContext.pattern: Optional[PatternSpec]
- PlanOutline.pattern: Optional[PatternSpec] (mirror)
- Roadmap.pattern: Optional[PatternSpec] (mirror)
- RoadmapContext: keep `pattern_type` (deprecated) and add `pattern: Optional[PatternSpec]`
  - Docstring: "present for backward compatibility—source of truth is pattern"
- GraphState.selected_pattern: Optional[PatternSpec]
- GraphState.pattern_rfc_required: bool
- GraphState.pattern_rfc_text: Optional[str]
- ORM Plan: pattern_type, pattern_subtype, pattern_variant (indexed)

Note: Confidence can remain in logs/observability; not persisted in DB.

---

## 4) InteractionPolicy (user style)

Sliders:
- conversation_style: "concise" | "standard" | "conversational" | "coach"
- talkativeness: 0..1
- autonomy: "high" | "medium" | "low"
- brainstorming_preference: "on_demand" | "suggest_when_uncertain" | "always_offer"
- approval_policy: "single_final" | "milestone_approvals" | "strict_every_step"
- probing_depth: 0..3
- tone: "neutral" | "friendly" | "clinical"

Where stored:
- MemoryContext.interaction_policy: long-term default per user
- GraphState.interaction_policy: session override (e.g., "be brief today")

Policy-aware routing:
- ContextElicitor: number of questions ≤ probing_depth
- Brainstormer: triggered if brainstorming_preference suggests and confidence borderline
- OptionCrafter: 2–3 variants based on conversation_style/talkativeness (e.g., 2 for concise)
- ApprovalHandler: cadence chosen via approval_policy
- Summarizer: trims verbosity and applies tone
- PreferenceProbe: one-time “concise or conversational?” if style unknown

---

## 5) LangGraph ReAct agent (inner loop) with atomic tools

Use LangGraph `create_react_agent` with SqliteSaver. The controller enforces state transitions and calls the agent; the agent uses tools only.

All tools share:
- Pydantic inputs, JSON outputs: { ok, confidence, explanations[], data }
- Metadata: prerequisites: list[str], produces: list[str]
- Idempotent + cacheable within session

Core tools (7):
1) PatternSelector → { pattern: PatternSpec }
2) NodeGenerator → PlanOutline (dual-axis metadata; origin="system")
3) GrammarValidator → { valid, violations[], confidence, suggested_fixes[] }
4) ContextElicitor → { questions[], confidence } (respects probing_depth; can ask for proposed subtype approval)
5) DependencyResolver → nodes_with_dependencies (FS/SS/FF/SF + lag/lead)
6) RoadmapBuilder → { roadmap, options_tried[] }
7) ScheduleGenerator → Schedule (tz-aware; respects StrategyProfile)

Utility tools:
- PortfolioProbe (conflicts/utilization/suggested shifts)
- ApprovalHandler (cadence via approval_policy)
- Summarizer (verbosity/tone control)
- Brainstormer (mini ideation bursts)
- OptionCrafter (2–3 concise variants)
- PreferenceProbe (style discovery)

Tool dependency management:
- ToolExecutor verifies prerequisites present and inputs valid before execution; on exception returns ok=False with error and confidence=0.0
- Controller can topologically check produces/prerequisites to avoid mis-ordering

Session caching:
- Memoize tool outputs by a stable key (hash of inputs + policy + LLM model/version)

---

## 6) Confidence, retries, escalation

Composite stage confidence:
- C = 0.50*(LLM self-score) + 0.30*(rule validator score) + 0.20*(heuristics)

Thresholds:
- continue ≥ 0.70
- retry 0.40–0.69 (apply suggested fix once, prompt narrowing once)
- escalate < 0.40

Escalations:
- Schedule infeasible → planning_status="needs_scheduling_escalation" (with escalate_reason)
- Pattern RFC awaiting human approval → planning_status="needs_clarification" with pattern_rfc_required=True and pattern_rfc_text

---

## 7) Budget, checkpoints, observability

LLM: OpenAI GPT‑4 (JSON/function calling), low temperature

Budget controls:
- Daily cap default $5; per-session cap $2; per-turn soft ceiling $0.30
- Estimate before call; track actual after call; trigger Summarizer + user prompt if turn ceiling exceeded

Checkpoints:
- SqliteSaver("data/agent_conversations.db")
- thread_id=f"user_{user_id}:{goal_id or 'new'}", checkpoint_ns="planning_agent"

Observability:
- Per-step trace: { stage, tool, duration_ms, confidence, cost_delta, violations, adaptations }
- Append AdaptationLogEntry on structural changes
- Persist PatternSpec to state and Plan (DB)

---

## 8) Contracts & placements (implementation checklist)

Pydantic:
- Add PatternSpec (with introduced_by, source_pattern, rfc)
- Add InteractionPolicy
- PlanContext.pattern, PlanOutline.pattern, Roadmap.pattern
- RoadmapContext: keep pattern_type (deprecated docstring) + add pattern

GraphState:
- selected_pattern: Optional[PatternSpec]
- pattern_rfc_required: bool
- pattern_rfc_text: Optional[str]
- interaction_policy: Optional[InteractionPolicy]

MemoryContext:
- interaction_policy: Optional[InteractionPolicy]

ORM (Plan):
- pattern_type, pattern_subtype, pattern_variant (indexed)

Config:
- Confidence thresholds, retry caps, budget caps
- Feature flags: ALLOW_NEW_SUBTYPE_PROPOSALS, REQUIRE_RFC_FOR_NEW_SUBTYPE

Router:
- No changes required

---

## 9) Prompts (high level)

- Agent system prompt: tool-only reasoning; Outline → Roadmap → Schedule; GrammarValidator gate; dual-axis grammar; taxonomy adherence; policy-aware messaging
- PatternSelector: mapping to nearest pattern + RFC subtype behavior
- RoadmapBuilder: enumerate 2–3 options; select with rationale; store options_tried
- Summarizer: apply conversation_style and tone
- Brainstormer/OptionCrafter: concise, actionable variants; clarify differences

---

## 10) Testing

Unit (mocked LLM):
- PatternSelector emits valid PatternSpec (including proposed subtype + RFC)
- Planning node propagates selected_pattern into PlanContext/Outline/Roadmap mirrors
- GrammarValidator catches L1 issues, cycles, unreachable tasks, pattern mismatches
- Policy gating: probing_depth caps questions; approval_policy changes cadence; conversation_style/talkativeness modulates variants and summarization

Integration (real GPT‑4, gated):
- recurring_cycle with subtype=protocol_routine → valid Schedule
- milestone_project with overlapping phases; options_tried recorded
- RFC path: subtype="proposed:daily_health_protocol_v2" → needs_clarification + pattern_rfc_required=True; ApprovalHandler resumes → completes
- Style variations: concise/high autonomy vs conversational/brainstorming

E2E:
- planning_node → router → world_model_integration_node → persistence_node
- DB persists Plan.pattern_*; ScheduledTask FKs intact

---

## 11) Implementation order

1) Contracts/state scaffolding: PatternSpec + InteractionPolicy fields (Pydantic, GraphState, MemoryContext)
2) Configs: thresholds, flags, budgets
3) Tool skeletons + metadata (prereqs/produces): PatternSelector, GrammarValidator, NodeGenerator; plus Brainstormer, OptionCrafter, Summarizer, ApprovalHandler stubs
4) Controller state machine scaffold (caps, BudgetManager, ToolExecutor, policy checks per turn)
5) RoadmapBuilder, ScheduleGenerator, PortfolioProbe
6) ApprovalHandler + RFC path integration
7) planning_node integration with LangGraph ReAct + SqliteSaver
8) Tests: unit → integration (mocked) → integration (real GPT‑4) → E2E

---

Notes:
- This document captures design only. No code changes performed as part of this step.
- Backward compatibility: RoadmapContext.pattern_type retained with clear deprecation note; source of truth is PatternSpec.
