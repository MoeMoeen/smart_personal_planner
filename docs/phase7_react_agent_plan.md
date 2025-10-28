# Phase 7 — ReAct Planning Agent (Final Design)

Status: Proposal ready for implementation (no code changes in this step)

Scope: Production-grade agentic planning node powered by LangGraph ReAct with explicit controller state machine, atomic tools, PatternSpec + RFC flow, InteractionPolicy (user style), checkpoints, budget controls, and quantitative confidence thresholds. Aligned with v1.2 (patterns/grammar/dual-axis) and v1.3 (MegaGraph + routing).


## Technical debt — stubs and temporary simplifications (Steps 1–6)

Purpose: Track every interim shortcut introduced during early implementation. This list must be cleared before declaring Phase 7 “complete” and before starting Phase 8 in the checkpoint doc.

### Step 1 — Contracts/state scaffolding

- PatternSpec placement only; DB persistence pending
    - Current: PatternSpec added to Pydantic models and GraphState mirrors.
    - Gap: ORM Plan fields (pattern_type, pattern_subtype, pattern_variant) not wired from state; migration and read/write paths pending.
    - Exit criteria: Migration adds indexed columns; planning node persists/reads back; tests validate round-trip.

- Confidence handling not persisted (by design) but not aggregated
    - Current: Confidence lives only in tool/controller logs; no composite metric.
    - Exit criteria: Composite confidence C reported per stage in planning_trace; tests assert threshold behavior.

- RoadmapContext.pattern_type kept for compatibility; usage audit pending
    - Current: Deprecation note exists; some reads may still use pattern_type.
    - Exit criteria: Audit usages; prefer Roadmap.pattern; add deprecation tests.

- InteractionPolicy discovery flow missing
    - Current: MemoryContext.interaction_policy exists; no PreferenceProbe to initialize/adjust it.
    - Exit criteria: Add PreferenceProbe tool + first-run prompt; cache in memory; tests cover probing_depth/verbosity effects.

### Step 2 — Configs (thresholds/flags/budgets)

- Budget policy not enforced
    - Current: SOFT_BUDGET_PER_TURN_USD present; no cost estimation/tracking; TurnBudget remains 0.0.
    - Exit criteria: BudgetManager computes/records cost per tool/LLM call; soft ceiling triggers summarizer/approval; session/daily caps tracked.

- Confidence thresholds defined but not applied
    - Current: CONTINUE/RETRY/ESCALATE thresholds configured; controller doesn’t compute composite confidence.
    - Exit criteria: Implement composite confidence; branching respects thresholds; tests cover boundary cases.

- RFC flags not integrated
    - Current: ALLOW_NEW_SUBTYPE_PROPOSALS, REQUIRE_RFC_FOR_NEW_SUBTYPE defined; no ApprovalHandler path; GraphState.rfc fields unused.
    - Exit criteria: PatternSelector emits proposed subtype + RFC; controller sets pattern_rfc_required/text; ApprovalHandler resumes flow on approval.

- ENFORCE_TOOL_DEPENDENCIES not used
    - Current: Tools expose prerequisites/produces; controller doesn’t enforce.
    - Exit criteria: Pre-flight checks validate prerequisites; errors return ToolResult(ok=False, confidence=0.0); tests simulate mis-ordered calls.

### Step 3 — Tool skeletons

- Core tools return placeholders (no LLM/logic)
    - PatternSelectorTool: ok=False; no mapping, confidence, or RFC generation.
    - GrammarValidatorTool: ok=False; no invariants/dual-axis checks or fixes.
    - NodeGeneratorTool: ok=False; no PlanOutline construction/dual-axis metadata/origin tags.
    - Exit criteria: Each tool produces valid outputs under mocked LLM; unit tests verify schemas and invariants.

- Utility tools exist but are deterministic stubs (Step 3 scope)
    - BrainstormerTool: ok=True deterministic echo of topic; no LLM or ideation heuristics.
    - OptionCrafterTool: ok=True deterministic variants; no LLM or contrastive reasoning.
    - Exit criteria: Integrate LLM-backed variants; policy-aware diversity and brevity; tests verify option quality knobs.

- Registry helper is stub-only (deferred beyond Step 4)
    - get_planning_tool_skeletons: returns only skeletons; no full registry or dependency graph.
    - Note: Production registry replacement is outside Steps 1–4 and will be tracked in later steps.

- Additional tools (outside Steps 1–5)
    - DependencyResolver, PreferenceProbe.
    - Note: These belong to later steps (Step 7); tracked separately.

- Step 3 stubs not yet implemented
    - Summarizer (stub).
    - Exit criteria: Minimal stub added with Pydantic I/O; covered by unit tests.

- Session caching minimal and in-memory only
    - Current: ToolExecutor caches by params hash; no persistence.
    - Exit criteria: Integrate LangGraph SqliteSaver checkpointing; cache keys include model/version and InteractionPolicy.

### Step 4 — Controller state machine scaffold

- Partial stages and early exits
    - Current: Implements COLLECT_CONTEXT → DRAFT_OUTLINE → VALIDATE_OUTLINE; other stages stubbed; returns needs_clarification.
    - Exit criteria: Implement DRAFT_ROADMAP/VALIDATE_ROADMAP, DRAFT_SCHEDULE/VALIDATE_SCHEDULE, SEEK_APPROVAL; happy path reaches COMPLETE under mocks.

- No LangGraph integration yet
    - Current: Direct tool calls; no create_react_agent or SqliteSaver.
    - Exit criteria: Controller invokes LangGraph ReAct agent per stage; checkpoints written with thread IDs.

- Budget/cost and confidence not computed
    - Current: Per-turn budget check uses 0.0; no cost deltas; no composite confidence.
    - Exit criteria: Track cost_delta per step; compute composite confidence C; thresholds gate transitions; traces record both.

- Prerequisites/produces not enforced
    - Current: Metadata exists but not validated before tool execution.
    - Exit criteria: Pre-flight checks reject invalid ordering; errors captured in trace; tests ensure enforcement.

- RFC flow and approvals not wired
    - Current: No ApprovalHandler; pattern_rfc_required/text never set; selected_pattern not propagated into PlanContext/Outline/Roadmap mirrors.
    - Exit criteria: SEEK_APPROVAL implements cadence; RFC path sets GraphState flags and pauses; resume completes flow.

- Observability is minimal
    - Current: planning_trace records sparse fields; no durations, violations, cost, or adaptations.
    - Exit criteria: Trace includes stage, tool, duration_ms, confidence, cost_delta, violations, adaptations; AdaptationLogEntry appended on structural changes.

### Step 5 — Roadmap/Schedule/Portfolio (minimal implementations)

- RoadmapBuilder is a mirror transform
    - Current: Mirrors PlanOutline nodes to Roadmap dict with minimal `roadmap_context`; does not enforce dependencies or produce `options_tried`.
    - Exit criteria: Generates roadmap variants and `options_tried` with selection rationale; respects constraints/pattern; unit tests verify invariants.

- ScheduleGenerator is naive
    - Current: Produces a few sequential 60-minute blocks from task-like nodes; no working-hours, no external calendar, no capacity heuristics.
    - Exit criteria: Calendar/constraints-aware scheduling; working-hours and timezone handling; capacity/utilization checks; unit tests cover edge cases.

- PortfolioProbe is simplistic
    - Current: Assumes non-overlapping blocks; always returns no conflicts; reports aggregate utilization only.
    - Exit criteria: Detect overlapping blocks, external calendar conflicts via `world_model`, and utilization against capacity thresholds; tests verify detection.

- Controller transitions for Step 5 are minimal
    - Current: VALIDATE_ROADMAP checks presence of nodes only; VALIDATE_SCHEDULE relies on PortfolioProbe stub; traces lack durations/cost.
    - Exit criteria: Add structural/semantic validations (e.g., dependencies, unreachable nodes); capture duration_ms and cost_delta per stage in trace; tests added.


### Step 6 — Approval/RFC (minimal integration)

- ApprovalHandler is synchronous and minimal
    - Current: Approves on explicit "approve" feedback or auto-approves for policy=single_final without RFC; otherwise returns pending with a CTA.
    - Exit criteria: Add asynchronous approval support with resume mechanics; cadence templates per approval_policy; richer CTA library; unit tests for cadence variants.

- RFC enforcement is partial
    - Current: Controller consumes GraphState.pattern_rfc_required/text but PatternSelector does not emit RFC fields yet; no human-in-the-loop persistence.
    - Exit criteria: PatternSelector emits proposed subtype + RFC; controller sets RFC flags and pauses; ApprovalHandler resumes on approval; tests verify pause/resume.

- SEEK_APPROVAL resume semantics are coarse
    - Current: On approval, marks outline/roadmap/schedule approved together and completes.
    - Exit criteria: Respect approval_policy (e.g., milestone_approvals) to gate stages individually; resume to correct next state; tests for each policy.

- Observability is limited for approvals
    - Current: planning_trace lacks duration/cost for approval path and does not record approval decisions.
    - Exit criteria: Trace includes duration_ms, cost_delta, decision, and CTA used; AdaptationLogEntry updated on structural changes due to requested modifications.

- Change requests not handled
    - Current: "propose changes: …" feedback is not interpreted; no loop-back to repair stages.
    - Exit criteria: Route change requests back to appropriate draft/validate stage with retry budget; tests cover round-trips.


### Technical debt checklist (Steps 1–6)

Note: The Step column refers to the Implementation order items 1–8 at the end of this document.

| Step | Area | Item | Status |
|---|---|---|---|
| 1 | Contracts/State | Audit RoadmapContext.pattern_type usages (prefer pattern) | [ ] Open |
| 2 | Configs | BudgetManager cost estimation/tracking + caps | [ ] Open |
| 2 | Configs | Apply CONTINUE/RETRY/ESCALATE thresholds (composite confidence) | [ ] Open |
| 2 | Observability | Surface composite confidence in planning_trace | [ ] Open |
| 3 | Tools — Core | PatternSelector (LLM + RFC fields emission) | [ ] Open |
| 3 | Tools — Core | GrammarValidator (rules + fixes) | [ ] Open |
| 3 | Tools — Core | NodeGenerator (outline + dual-axis) | [ ] Open |
| 3 | Tools — Utility | Brainstormer (LLM-backed) | [ ] Open |
| 3 | Tools — Utility | OptionCrafter (LLM-backed) | [ ] Open |
| 3 | Tools — Utility | Summarizer (stub) | [ ] Open |
| 3 | Tools — Utility | ApprovalHandler (stub) | [ ] Open |
| 4 | Controller | Implement remaining stages + happy path COMPLETE | [ ] Open |
| 4 | Controller | Enforce prerequisites/produces checks | [ ] Open |
| 4 | Observability | Trace: durations, cost deltas, violations, adaptations | [ ] Open |
| 5 | Tools — Core | RoadmapBuilder (variants + options_tried + constraints) | [ ] Open |
| 5 | Tools — Core | ScheduleGenerator (calendar/constraints-aware) | [ ] Open |
| 5 | Tools — Utility | PortfolioProbe (real conflicts + capacity) | [ ] Open |
| 5 | Controller | Roadmap/Schedule validations beyond presence | [ ] Open |
| 5 | Observability | Trace: duration/cost/confidence for Step 5 stages | [ ] Open |
| 6 | Tools — Utility | ApprovalHandler (async path, CTA templates) | [ ] Open |
| 6 | Controller | SEEK_APPROVAL integration (resume flow post-approval) | [ ] Open |
| 6 | RFC Policy | Enforce REQUIRE_RFC_FOR_NEW_SUBTYPE and set GraphState flags | [ ] Open |

Out-of-scope for Steps 1–6 (tracked in later steps):
- RFC/Approvals full wiring beyond minimal sync (Step 6 complete path is iterative)
- LangGraph ReAct + SqliteSaver integration (Step 7)
- Production registry replacing get_planning_tool_skeletons (Step 7)
- Persistent caching keyed by model/version + policy (Step 7)
- DependencyResolver, PreferenceProbe (Step 7)


Design Sections:

## 0) Non-negotiables

- Single source of truth: PlanOutline → Roadmap → Schedule (Pydantic contracts)
- Tools-only ReAct; free text is user-facing only
- Deterministic guardrails: a rule validator must pass before advancing stages
- Explicit controller state machine with hard caps (turns, time, budget)
- Observability-first: per-step trace + AdaptationLogEntry for structural changes
- Router semantics unchanged; planning node owns approvals and emits planning_status accordingly

## 1) Pattern policy (RFC flow)

- Step 1: Map to nearest canonical top-level pattern
    - {milestone_project, recurring_cycle, progressive_accumulation_arc, hybrid_project_cycle, strategic_transformation}
- Step 2: If awkward, propose a new subtype as `subtype="proposed:<name>"` with a concise RFC rationale
- Step 3: New top-level patterns require human approval; subtypes can be proposed and reviewed

Agent behavior:
- Emits closest pattern_type and subtype; if proposing, includes RFC text and confidence
- If asynchronous approval is needed, return planning_status="needs_clarification" with response_text and escalate_reason that clearly state the pending decision (RFC)
- Router remains unchanged; no new keys introduced


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
        "success": "VALIDATE_OUTLINE",
        "low_confidence": "COLLECT_CONTEXT",
        "fatal_error": "ABORTED"
    "VALIDATE_OUTLINE": {
        "valid": "DRAFT_ROADMAP",
        "invalid_retryable": "DRAFT_OUTLINE",
    },
    "VALIDATE_SCHEDULE": {
        "valid": "SEEK_APPROVAL",
    },
    "SEEK_APPROVAL": {
        "approved": "COMPLETE",
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
     - Covers design sections:
         - 3) PatternSpec (first-class) — models + GraphState mirrors
         - 4) InteractionPolicy (user style) — models + GraphState override
         - 8) Contracts & placements — primary implementation
         - 0) Non-negotiables — adhered
2) Configs: thresholds, flags, budgets
     - Covers design sections:
         - 6) Confidence, retries, escalation — thresholds/caps defined
         - 7) Budget, checkpoints, observability — budget caps configured
         - 0) Non-negotiables — adhered
3) Tool skeletons + metadata (prereqs/produces): PatternSelector, GrammarValidator, NodeGenerator; plus Brainstormer, OptionCrafter, Summarizer, ApprovalHandler stubs
     - Covers design sections:
         - 5) LangGraph ReAct agent (inner loop) — tool definitions prepared
         - 1) Pattern policy (RFC flow) — PatternSelector skeleton for mapping/RFC placeholders
         - 4) InteractionPolicy (user style) — policy-aware utility stubs (brainstorm/option/summarizer/approval)
         - 8) Contracts & placements — Pydantic I/O schemas for tools
4) Controller state machine scaffold (caps, BudgetManager, ToolExecutor, policy checks per turn)
     - Covers design sections:
         - 2) Controller state machine (outer loop) — scaffold and caps
         - 6) Confidence, retries, escalation — initial gating wiring
         - 7) Budget, checkpoints, observability — trace placeholders
         - 0) Non-negotiables — adhered
5) RoadmapBuilder, ScheduleGenerator, PortfolioProbe
     - Covers design sections:
         - 2) Controller state machine — DRAFT_ROADMAP/VALIDATE_ROADMAP, DRAFT_SCHEDULE/VALIDATE_SCHEDULE
         - 5) LangGraph ReAct agent — roadmap/schedule tool behaviors (mocked/minimal)
         - 7) Budget, checkpoints, observability — stage trace entries
6) ApprovalHandler + RFC path integration
     - Covers design sections:
         - 1) Pattern policy (RFC flow) — enforce flags; proposed subtype approvals
         - 2) Controller state machine — SEEK_APPROVAL stage
         - 6) Confidence, retries, escalation — clarification/escalation outcomes
         - 7) Budget, checkpoints, observability — approval traces
7) planning_node integration with LangGraph ReAct + SqliteSaver
    - Includes authoring and wiring of Prompts (section 9) for agent and tools
     - Covers design sections:
         - 5) LangGraph ReAct agent — create_react_agent + SqliteSaver + registry
         - 9) Prompts (high level) — authored + wired for agent/tools
         - 7) Budget, checkpoints, observability — real cost tracking + checkpoints + full traces
         - 6) Confidence, retries, escalation — composite computation in agent loop
         - 3) PatternSpec (first-class) — DB persistence/write-through
         - 4) InteractionPolicy (user style) — enforced via prompts/policy
         - 8) Contracts & placements — finalized wiring
8) Tests: unit → integration (mocked) → integration (real GPT‑4) → E2E
     - Covers design sections:
         - 10) Testing — unit/integration/E2E across artifacts and flows
         - Cross-cuts prior sections for verification of behavior and invariants

---

### Mapping to design sections (0–10)

This matrix mirrors each design headline to its implementation step(s) so nothing is left ambiguous:

| Design section | Title | Implementation step(s) |
|---|---|---|
| 0 | Non-negotiables | Applies across all steps (guidance) |
| 1 | Pattern policy (RFC flow) | 3 (PatternSelector skeleton), 6 (RFC + ApprovalHandler), 7 (prompts enforce policy) |
| 2 | Controller state machine (outer loop) | 4 (scaffold), 5 (roadmap/schedule transitions), 7 (finalize with LangGraph + checkpoints) |
| 3 | PatternSpec (first-class) | 1 (contracts/state), 7 (DB persistence/write-through) |
| 4 | InteractionPolicy (user style) | 1 (contracts/state), 3 (policy-aware utility stubs), 7 (prompts apply policy) |
| 5 | LangGraph ReAct agent (inner loop) | 7 (create_react_agent + SqliteSaver + tool registry) |
| 6 | Confidence, retries, escalation | 2 (thresholds/caps), 4–5 (controller gating), 7 (confidence computation in agent) |
| 7 | Budget, checkpoints, observability | 2 (budget configs), 4–5 (trace placeholders), 7 (checkpointer + cost tracking + full traces) |
| 8 | Contracts & placements (implementation checklist) | 1 (primary), 7 (finalize and persist) |
| 9 | Prompts (high level) | 7 (authored + wired during agent integration) |
| 10 | Testing | 8 (unit → integration → E2E) |

Notes:
- This document captures design only. No code changes performed as part of this step.
- Backward compatibility: RoadmapContext.pattern_type retained with clear deprecation note; source of truth is PatternSpec.
