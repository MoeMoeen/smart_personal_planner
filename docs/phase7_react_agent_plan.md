# Phase 7 — High-Autonomy ReAct Planning Agent (Final Design)

Status: Updated to High-Autonomy design (controller as thin harness). Implementation partially in progress; no breaking changes required.

Scope: Production-grade agentic planning node powered by LangGraph ReAct where the agent owns sequencing (think → decide → tool → observe) and the controller is a minimal safety harness. Tools are atomic (LLM + deterministic), PatternSpec + RFC flow is first-class, InteractionPolicy drives UX, and the controller enforces budgets, checkpoints, schemas, and validators. Aligned with v1.2 (patterns/grammar/dual-axis) and v1.3 (MegaGraph + routing).

Note on design shift: The prior design emphasized an outer controller state machine orchestrating stages while the agent executed within them. The new High-Autonomy design flips ownership: the ReAct agent chooses which tool to call and when; the controller validates, budgets, checkpoints, and persists. The previous controller FSM remains as a fallback path for safety and CI stability.


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

### Step 3 — Tool skeletons (updated for High-Autonomy)

- Core tools (status update)
    - PatternSelectorTool: LLM-backed with structured output and RFC fields (implemented; gated by feature flag).
    - GrammarValidatorTool: stub; invariants/dual-axis checks + repair suggestions pending (to be upgraded to LLM-backed).
    - NodeGeneratorTool: LLM-backed PlanOutline generation with structured output (implemented; gated by feature flag).
    - Exit criteria: All core tools produce valid outputs (mocked LLM tests). GrammarValidator upgraded with rules + auto-repair suggestions.

- Utility tools (updated)
    - ClarifierTool (new): Ask a single, specific question when inputs are missing; agent calls this autonomously to elicit context (implemented, deterministic; respects style).
    - BrainstormerTool: deterministic stub; will be upgraded to LLM-backed for ideation heuristics.
    - OptionCrafterTool: deterministic stub; will be upgraded to LLM-backed for contrastive options.
    - Summarizer: add minimal stub to shape user-facing summaries per policy.
    - Exit criteria: Clarifier wired; Brainstormer/OptionCrafter upgraded to LLM; Summarizer stub present and policy-aware.

- Registry/helper
    - Structured tool registry provided to `create_react_agent` (current mapping includes Clarifier, PatternSelector, GrammarValidator, NodeGenerator, RoadmapBuilder, ScheduleGenerator, PortfolioProbe, ApprovalHandler).
    - Note: Production registry and dependency graph remain a later enhancement.

- Additional tools (outside Steps 1–5)
    - DependencyResolver, PreferenceProbe.
    - Note: These belong to later steps (Step 7); tracked separately.

- Step 3 stubs not yet implemented
    - Summarizer (stub).
    - Exit criteria: Minimal stub added with Pydantic I/O; covered by unit tests.

- Session caching minimal and in-memory only
    - Current: ToolExecutor caches by params hash; no persistence.
    - Exit criteria: Integrate LangGraph SqliteSaver checkpointing; cache keys include model/version and InteractionPolicy.

### Step 4 — Controller (thin harness) — supersedes FSM in High-Autonomy mode

- High-Autonomy controller path
    - Current: When High-Autonomy flag is enabled, the controller delegates the entire planning loop to the ReAct agent and acts only as a safety harness (budgets, schema validation, checkpoints, persistence, tracing). The prior FSM is retained as a fallback path.
    - Exit criteria: Agent-first path is default for planning; fallback FSM remains gated for CI/stability.

- Agent integration
    - Current: `react_agent.py` wraps tools as structured tools and builds a ReAct agent with SqliteSaver checkpoints; controller invokes agent with `thread_id`.
    - Exit criteria: Controller passes through calls (no stage orchestration); thread_id/checkpoint_ns wired; resume verified.

- Budget/cost and confidence
    - Current: Budget placeholders exist; no real cost tracking or composite confidence yet.
    - Exit criteria: Track model/tool costs; compute composite confidence; thresholds aid controller safety decisions.

- Prerequisites/produces
    - Current: Metadata present; agent decides sequencing. Controller may still pre-flight critical dependencies in fallback path.
    - Exit criteria: Safety checks for obvious mis-ordering (fallback); agent tool docs guide correct usage.

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

### Step 7 — High-Autonomy ReAct agent + prompts + checkpoints

- Agent integration (agent-first)
    - Current: `react_agent.py` creates a ReAct agent with the full tool registry (including Clarifier). Controller delegates entire planning flow when enabled. SqliteSaver is configured; `thread_id` set for continuity.
    - Exit criteria: High-Autonomy path is primary; controller does not orchestrate stages. Agent owns tool selection/order.

- Prompts
    - Current: System prompt guides tool-only reasoning; more policy- and grammar-rich prompts needed.
    - Exit criteria: Author agent/tool prompts emphasizing autonomy + safety: use Clarifier early, validate before finalize, respect InteractionPolicy.

- Cost/confidence
    - Current: Not yet implemented within agent loop.
    - Exit criteria: Add callbacks to collect token usage; compute composite C; controller enforces soft caps.

- Registry/caching
    - Current: StructuredTool registry is in place. Persistent caching remains future work.
    - Exit criteria: Production registry + persistent cache keys (model/version + policy).

#### Example (High-Autonomy) — “Flu recovery” (summary)
1) Agent calls PatternSelector → recurring_cycle/protocol_routine.
2) Agent calls Clarifier to elicit missing context (kitchen access, meds, preferences).
3) Agent calls NodeGenerator → PlanOutline; then GrammarValidator → valid.
4) Agent calls RoadmapBuilder → daily cadence, options_tried.
5) Agent calls ScheduleGenerator → morning/evening blocks.
6) Agent calls ApprovalHandler per policy → approve or propose changes.
Controller: validates schemas, budgets, checkpoints, persists, traces; no stage orchestration.


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
| 7 | Agent | create_react_agent wired + SqliteSaver checkpoints | [ ] Open |
| 7 | Prompts | Author and wire prompts (agent + tools) | [ ] Open |
| 7 | Budget/Confidence | Real cost tracking + composite C in agent loop | [ ] Open |
| 7 | Registry/Caching | Production registry + persistent cache keys | [ ] Open |

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
- Deterministic guardrails: a rule validator must pass before finalizing artifacts
- Controller is a thin harness (budgets, time caps, schema/validator gates, checkpoints)
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


## 2) Controller (thin harness) and fallback FSM

Primary behavior (High-Autonomy):
- The controller does not orchestrate stages. It delegates to the agent, enforces hard caps (turns/time/budget), validates outputs (schemas + GrammarValidator), checkpoints, persists, and logs trace data. It returns agent prompts to the user when the agent needs more info.

Fallback FSM (for safety/CI):
- A minimal stage machine can be used when High-Autonomy mode is disabled to reach a safe baseline (Outline → Roadmap → Schedule → Approval) under mocks.
- Caps (config): TURN_LIMIT=10, RETRY_LIMIT_PER_STAGE=2, WALL_TIME_SEC=45, BUDGET_PER_SESSION_USD=2.0, SOFT_BUDGET_PER_TURN_USD=0.30


---

🔁 4. Agent-first loop vs fallback

- Agent-first loop: The agent thinks/acts autonomously across the whole planning scope, selecting and calling tools as needed. The controller only guards and records.
- Fallback: The controller may use a shallow FSM to reach a baseline plan when autonomy is disabled or unavailable.

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

## 5) LangGraph ReAct agent (inner loop) with atomic tools (agent-first)

Use LangGraph `create_react_agent` with SqliteSaver. The agent receives a registry of StructuredTools with clear docstrings and Pydantic schemas and decides which to call next. The controller does not dictate stage order.

All tools share:
- Pydantic inputs, JSON outputs: { ok, confidence, explanations[], data }
- Metadata: prerequisites: list[str], produces: list[str]
- Idempotent + cacheable within session

Core tools (agent-facing):
1) Clarifier → { question } — ask for missing info (respects InteractionPolicy.probing_depth/conversation_style)
2) PatternSelector → { pattern: PatternSpec } — may emit proposed subtype + RFC
3) NodeGenerator → PlanOutline (dual-axis metadata; origin="system")
4) GrammarValidator → { valid, violations[], confidence, suggested_fixes[] }
5) RoadmapBuilder → { roadmap, options_tried[] }
6) ScheduleGenerator → Schedule (tz-aware; respects StrategyProfile)
7) ApprovalHandler → { decision, cta }
8) (Later) DependencyResolver, PreferenceProbe, Summarizer, BudgetOracle, MinimalInfoChecklist

Utility tools:
- PortfolioProbe (conflicts/utilization/suggested shifts)
- ApprovalHandler (cadence via approval_policy)
- Summarizer (verbosity/tone control)
- Brainstormer (mini ideation bursts)
- OptionCrafter (2–3 concise variants)
- PreferenceProbe (style discovery)

Tool dependency management:
- The agent follows tool docstrings and schemas to choose correct order. Controller may enforce hard prerequisites in fallback mode. Tools remain idempotent within a session.

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
- Per-turn trace: { tool, duration_ms, confidence, cost_delta, violations, adaptations, agent_output_preview }
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

## 11) Implementation order (revised for High-Autonomy)

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
7) High-Autonomy agent integration with LangGraph + SqliteSaver
    - 7a: Introduce High-Autonomy mode flag; add Clarifier (done), MinimalInfoChecklist, BudgetOracle tools
    - 7b: Update agent prompt + safety guards; run create_new_plan end-to-end in High-Autonomy mode (controller as harness)
    - 7c: Telemetry + human-in-the-loop for PatternSpec RFCs
    - 7d: Extend to revise_plan/adaptive_replan intents
     - Covers design sections:
         - 5) LangGraph ReAct agent — agent-first sequencing + registry
         - 9) Prompts — authored + wired for agent/tools
         - 7) Budget, checkpoints, observability — cost tracking + checkpoints + traces
         - 6) Confidence, retries, escalation — composite computation used for safety
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
