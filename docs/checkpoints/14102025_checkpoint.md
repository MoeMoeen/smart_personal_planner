**Date:** 14 October 2025
**Owner:** Moe Moeen
**Document Type:** Execution Plan (v1.2 patterns/grammar + v1.3 orchestration)

# Smart Personal Planner — Planning Node Refactor & Orchestration Plan (v1.2/v1.3)

This document records the agreed plan to implement the agentic Planning Node, align cognitive entities with the v1.2 model (patterns + grammar + dual-axis), wire the MegaGraph (v1.3), and aggressively clean up legacy models. It will be kept up to date as we execute.

---

## Progress tracker

- [x] Phase 1 — Rename + Scope Contract (Completed 2025-10-14)
- [x] Phase 2 — Cognitive Entities (Pydantic) (Completed 2025-10-14)
- [x] Phase 3 — GraphState Contract (Completed 2025-10-14)
- [x] Phase 4 — SQLAlchemy ORM (aggressive cleanup) (Completed 2025-10-24)
- [ ] Phase 5 — Router Function (post-planning branching)
- [ ] Phase 6 — Node Registry & Defaults
- [ ] Phase 7 — Planning Agent (ReAct) — Design Contract
- [ ] Phase 8 — Minimal Stub planning_node (Wiring Test)
- [ ] Phase 9 — Prompt/Policy Centralization
- [ ] Phase 10 — E2E Demo Harness
- [ ] Phase 11 — QA Matrix & Rollout

## Core decisions (source of truth)

- Planning is an agentic meganode (ReAct-style subgraph) that owns the entire dialogue loop and approvals. If Planning succeeds, Outline/Roadmap/Schedule are user-approved and no confirm nodes follow.
- Deterministic modular nodes (task_generation, validation, calendarization, confirm A/B) are for fallback-only flows; they are not downstream of the agentic path.
- Aggressive cleanup: legacy HabitCycle/GoalOccurrence/Task (ORM) and OccurrenceTask(s)/CalendarizedPlan (Pydantic) will be removed now; DB is disposable (no migration shims required).
- Schedule persistence truth is DB ScheduledTask; the in-memory Pydantic ScheduledBlock must map 1:1 to ScheduledTask.
- Router after planning branches only on planning_status.

---

## Phase 1 — Rename + Scope Contract (no logic changes)

Status: Completed (2025-10-14)

Artifacts touched:
- Replaced `plan_outline_node` with `planning_node` in `app/flow/node_registry.py` (entrypoint now `app.cognitive.nodes.planning_node:planning_node`).
- Added placeholder `app/cognitive/nodes/planning_node.py`.
- Deprecated legacy `app/cognitive/nodes/plan_outline_node.py` (raises NotImplementedError).

Actions:
- Rename plan_outline_node → planning_node (agentic meganode).
- Remove language/docs implying downstream confirm nodes on agentic path.
- Keep legacy modular nodes for deterministic fallback flows (behind optional feature flag).

Acceptance criteria:
- Node registry shows planning_node as primary entrypoint for create_new_plan (and revise_plan if applicable).
- Docs updated: planning_node = agent with self-contained loop; confirm nodes are fallback-only.

---

## Phase 2 — Cognitive Entities (Pydantic) — Create/Update/Retire

Status: Completed (2025-10-14)

Artifacts touched:
- Implemented new models in `app/cognitive/contracts/types.py`:
	- PlanNode, PlanOutline, PlanContext, Roadmap, RoadmapContext, ScheduledBlock, Schedule, StrategyProfile, AdaptationLogEntry.
- Removed legacy: OccurrenceTask(s), CalendarizedPlan, old GoalSpec-centered outline shape.

Create/Update (app/cognitive/contracts/types.py):
- PlanNode:
	- id, parent_id, node_type ∈ {goal, phase, cycle, sub_goal, task, sub_task, micro_goal},
	- level (L1…Ln), title, description,
	- recurrence ∈ {none, daily, weekly, monthly, quarterly, yearly},
	- dependencies: List[{node_id, type ∈ {finish_to_start, start_to_start}, lag_lead_minutes?: int}],
	- status ∈ {pending, in_progress, done, blocked}, progress ∈ [0,1],
	- origin ∈ {system, user_feedback, ai_adaptation}, tags: List[str], metadata: dict.
- PlanOutline: { root_id, nodes: List[PlanNode], plan_context: PlanContext }
- PlanContext: { assumptions: list|dict, constraints: list|dict, strategy_profile: StrategyProfile, user_prefs: dict }
- Roadmap: { root_id, nodes: List[PlanNode], roadmap_context: RoadmapContext }
- RoadmapContext: { scope, budget, cadence, stack/venue, region, time_horizon, pattern_type, subtype }
- Schedule: { blocks: List[ScheduledBlock] }
- ScheduledBlock: { plan_node_id, title, start: datetime, end: datetime, estimated_minutes: int, notes?: str, tags?: list[str] }
- StrategyProfile: { mode ∈ {push, relax, hybrid, manual}, weights?: {achievement?: float, wellbeing?: float, portfolio?: float} }
- AdaptationLogEntry: { ts, node_ids: list[str], action, reason, origin, strategy_applied, portfolio_impact?: dict }

Retire/Replace (aggressive cleanup):
- Remove: OccurrenceTask, OccurrenceTasks, CalendarizedPlan (prefer Schedule).
- Replace Habit/Cycle occurrences with PlanNode + Schedule.
- If a separate Task Pydantic exists, eliminate in favor of PlanNode(node_type="task").

Acceptance criteria:
- Pydantic models compile; type checks pass; JSON schemas generate.
- Unit tests enforce grammar invariant: every Goal has a descendant Task (actionability).

---

## Phase 3 — GraphState Contract (Planner/Orchestrator)

Status: Completed (2025-10-14)

Artifacts touched:
- Updated `app/cognitive/state/graph_state.py` to include new artifacts (PlanOutline, Roadmap, Schedule), approvals flags, planning_status, escalate_reason, adaptation_log, planning_trace.
- Removed legacy fields: occurrence_tasks, calendarized_plan, confirm/validation router flags.

GraphState additions:
- intent: str
- goal_context: dict
- plan_outline: PlanOutline | None
- roadmap: Roadmap | None
- schedule: Schedule | None
- outline_approved: bool
- roadmap_approved: bool
- schedule_approved: bool
- planning_status: Literal["complete","needs_clarification","needs_scheduling_escalation","aborted"]
- escalate_reason: str | None
- response_text: str | None
- adaptation_log: list[AdaptationLogEntry]
- Optional: planning_trace: list[dict] (compact, capped)

Behavior:
- planning_node writes the artifacts and approval flags.
- Router branches exclusively on planning_status.

Acceptance criteria:
- Mock E2E: stub planning_node writes fields → router branches as expected.

---

## Phase 4 — SQLAlchemy ORM (aggressive cleanup in app/models.py)

Status: Completed (2025-10-24)

Artifacts touched:
- Completely rewrote `app/models.py` with aggressive cleanup and v1.2/v1.3 alignment.
- Removed legacy tables: HabitCycle, GoalOccurrence, Task and all their relationships.
- Added new PlanNode table with UUID PKs, proper constraints, and performance indices.
- Enhanced ScheduledTask with plan_node_id FK and UUID PK.

Add:
- PlanNode table:
	- id (UUID PK), plan_id (FK), parent_id (FK plan_nodes.id), node_type, level,
	- title, description, recurrence, dependencies JSONB, status, progress (Float 0.0-1.0), origin,
	- order_index, node_metadata JSONB, tags JSONB, created_at, updated_at.
	- Self-referential hierarchy with proper foreign_keys disambiguation.
	- Unique constraint: one root node (L1, parent_id=NULL) per plan.
	- Performance indices on plan_id, node_type, level, parent_order.
	- GIN indices on JSONB fields (tags, dependencies).
- ScheduledTask: add required plan_node_id (FK → plan_nodes.id), UUID PK, Text notes, CASCADE behavior.

Remove:
- Drop legacy tables: HabitCycle, GoalOccurrence, Task.
- Remove relationships from Goal, User, Plan that reference dropped tables.

Keep:
- Goal, Plan, ScheduledTask, Feedback, User, CapacitySnapshot, Episodic/Semantic/ProceduralMemory.

Surgical deltas applied:
- Progress alignment: Float 0.0-1.0 (matches Pydantic) vs Integer 0-100.
- Self-referential relationships: foreign_keys parameter to avoid ambiguity.
- Root uniqueness: partial unique index enforces one L1 goal per plan.
- Enhanced notes: Text column vs String for larger content.
- Metadata consistency: node_metadata column (avoids SQLAlchemy clash).

Acceptance criteria:
- ✅ DB schema compiles cleanly with all models importing successfully.
- ✅ CRUD: Plan → PlanNodes → ScheduledTasks with plan_node_id relationships work.
- ✅ All constraints, indices, and cascade behavior properly defined.
- ✅ 1:1 alignment with Pydantic contracts (progress Float, proper column mapping).

---

## Phase 5 — Router Function (post-planning branching)

Function:
- route_after_planning_result(state) -> str
- Mapping:
	- complete → "to_world_model"
	- needs_scheduling_escalation → "to_scheduling_escalation"
	- needs_clarification → "to_planning_loop"
	- aborted → "to_summary_or_end"

Edges:
- to_world_model → world_model_integration_node → persistence_node → reflection_node | summary_node
- to_scheduling_escalation → scheduling_escalation_node (HITL/tooling)
- to_planning_loop → planning_node
- to_summary_or_end → summary_node | END

Acceptance criteria:
- Unit tests for all routes; invalid status raises or defaults to summary with warning.

---

## Phase 6 — Node Registry & Defaults

Registry:
- Register planning_node (agentic entrypoint).
- Keep modular nodes for deterministic fallback only (optional feature flag: PLANNING_FALLBACK_MODE).

Defaults:
- create_new_plan: preferred = ["planning_node"].
- Deterministic fallback: separate path, guarded by feature flag; not a continuation after agentic planning.

Acceptance criteria:
- Integration tests toggle agentic vs fallback flows via the flag.

---

## Phase 7 — Planning Agent (ReAct) — Design Contract

Tools:
- PatternSelector, GrammarComposer, StructureValidator,
- ContextElicitor, RoadmapSculptor, Scheduler, PortfolioProbe.

Loop:
1) Infer pattern → draft Outline → validate → clarify if needed.
2) Produce Roadmap (explicit RoadmapContext options).
3) Produce Schedule (constraints, dependencies, recurrence).
4) Apply strategy (push/relax/hybrid/manual) if conflicts.
5) Set approvals & planning_status.

Adaptivity:
- Dynamic depth (L1…L5), split/merge streams, reschedule/resync across goals, log `AdaptationLogEntry` for each structural change.

Acceptance criteria:
- Spec tests (no LLM): tool simulations output valid artifacts; validator catches broken graphs.

---

## Phase 8 — Minimal Stub planning_node (Wiring Test)

Behavior:
- Reads intent & goal_context.
- Emits tiny valid PlanOutline (root + 1 task), placeholder Roadmap + Schedule.
- Sets approvals True and planning_status = "complete".
- Knobs to emit "needs_clarification" and "needs_scheduling_escalation".

Acceptance criteria:
- E2E harness exercises all route transitions.

---

## Phase 9 — Prompt/Policy Centralization

Files:
- app/cognitive/prompts/planner.py → planner system prompt (patterns + grammar + dual-axis, self-approval semantics).
- app/cognitive/prompts/intent.py → SUPPORTED_INTENTS classifier prompt.

Guardrails:
- Canonical vocabulary (PlanNode, Roadmap before Schedule, pattern names).
- Planner: if planning_node selected, do not append confirm nodes.

Acceptance criteria:
- Golden prompts stored; unit tests validate key invariants.

---

## Phase 10 — E2E Demo Harness

File:
- app/demo/e2e_demo.py → planning_node → router → world_model_integration_node → persistence_node.

Features:
- CLI flags to simulate complete / clarification / escalation.
- Prints GraphState per hop.

Acceptance criteria:
- Demo runs; JSON dumps saved for inspection.

---

## Phase 11 — QA Matrix & Rollout

Unit tests:
- Grammar invariants (Goal → Task), router paths, Pydantic schema round-trips.

Integration tests:
- Agentic happy path (stub), clarification loop (two iterations), escalation path, deterministic fallback flow (flagged).

Observability:
- Structured logs: {node, decision, planning_status, approvals, deltas}.
- AdaptationLogEntry appended on structural changes.

Rollout:
- Default to agentic planning for new goals.
- Optional: keep fallback for a short parity window, then remove.

---

## Entities — CRUD Summary

Create:
- Pydantic: PlanNode, PlanOutline, PlanContext, Roadmap, RoadmapContext, Schedule, ScheduledBlock, StrategyProfile, AdaptationLogEntry.
- ORM: PlanNode table; add plan_node_id to ScheduledTask.

Retire (immediate):
- ORM: HabitCycle, GoalOccurrence, Task.
- Pydantic: OccurrenceTask, OccurrenceTasks, CalendarizedPlan.

Router:
- Implement route_after_planning_result with mapping keys: "to_world_model", "to_scheduling_escalation", "to_planning_loop", "to_summary_or_end".

---

## Flags, enums, and keys (canonical)

- Feature flag: PLANNING_FALLBACK_MODE (bool), default False.
- planning_status ∈ {complete, needs_clarification, needs_scheduling_escalation, aborted}.
- Router mapping keys: to_world_model, to_scheduling_escalation, to_planning_loop, to_summary_or_end.

---

## Definition of Done (snapshot)

✓ Renamed node + docs reflect agent ownership of approvals.
✓ New Pydantic entities compiled & grammar-enforced.
✓ ORM cleaned: PlanNode added; ScheduledTask.plan_node_id in place; legacy tables removed.
✓ Surgical deltas applied: progress Float alignment, self-referential disambiguation, root uniqueness constraint.
- [ ] Router implemented + covered by tests.
- [ ] Minimal stub planning_node validates wiring.
- [ ] Fallback flows isolated behind optional flag.
- [ ] E2E harness and structured logs provide clear visibility.

---

## Changelog

- 2025-10-14: Initial execution plan recorded based on v1.2/v1.3 alignment and aggressive cleanup decision.
- 2025-10-24: Phase 4 completed - aggressive ORM cleanup with surgical deltas applied. Legacy cleanup complete, removed HabitCycle/GoalOccurrence/Task tables, added PlanNode with UUID PKs and proper constraints, enhanced ScheduledTask with plan_node_id FK. Perfect 1:1 alignment with Pydantic contracts achieved.

