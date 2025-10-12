# 🧠 Smart Planner AI — Checkpoint 3

**Date:** 11 October 2025
**Owner:** Moe Moeen
**Scope:** Architecture + Flow Design + World Model + Memory + Intents + Fallback Flows + Open Questions + Deprecations/Enhancements + Next Steps

> Nothing is set in stone. Several components are expected to be **replaced, deprecated, or enhanced** as we converge on the right long‑term architecture.

---

## 1) Introduction & Product Summary

**Smart Planner AI** is a full‑stack, AI‑powered goal planning assistant that supports natural language input, generates structured plans with timelines and tasks, tracks performance, and enables conversational refinement. It is built with **FastAPI**, **LangChain**, **LangGraph**, **SQLAlchemy**, and integrated with **Telegram** for real‑time assistant behavior.

**Core user value:**

* Create and track **project goals** or **habits**
* Break goals into tasks based on **time estimates** and **availability**
* Generate **personalized plans** using LLMs
* View **progress** and **adjust intelligently**
* Additional cases via intent routing and dynamic flows

**Tech stack:** FastAPI (backend), LangChain/LangGraph (AI orchestration), PostgreSQL + SQLAlchemy (DB), Telegram bot (conversational UI). React frontend planned as the next chapter.

---

## 2) Foundational Architecture (Dual Paradigm)

We intentionally combine two foundational paradigms that **work together**:

### 2.1 Cognitive AI Architecture (layers/nodes)

Covers the reasoning pipeline across perception → planning → validation → world update → persistence.

**Canonical nodes / layers (current set; may evolve):**

* **intent_recognition_node** — detects user intent from raw message
* **plan_outline_node** — builds the high‑level plan structure
* **task_generation_node** — expands the outline into tasks/subtasks
* **user_confirm_a_node** — first confirmation checkpoint (before elaboration)
* **world_model_integration_node** — merges outputs into the user’s world model
* **calendarization_node** — transforms tasks into scheduled blocks/events
* **validation_node** — verifies constraints: capacity, conflicts, blackout windows, recurrences, etc.
* **user_confirm_b_node** — final confirmation checkpoint (pre‑persistence)
* **persistence_node** — writes/updates SQLAlchemy entities
* **conversation_node** — general conversational handling where needed
* **clarification_node** — targeted Q&A to close information gaps

> The set is **not final**; nodes can be renamed, split, or merged as the architecture matures.

#### 2.1.a Memory Subcomponent

* **Episodic memory** — interaction history and significant events
* **Semantic memory** — user preferences, general rules, domain knowledge
* **Procedural memory** — learned procedures/heuristics for planning and scheduling
* **Memory context** — unified context injected into node reasoning & GraphState
* **Schemas & storage** — Pydantic/DB schemas defined for each memory type; persistence strategy defined; later vector memory optional (Chroma/Weaviate) for semantic retrieval

#### 2.1.b World Subcomponent (the user’s world)

World is the **DB‑backed source of truth** powered by SQLAlchemy models; it evolves with user actions and planner outputs.

**Modules:**

* **Models** — complete system schema (goals, plans, tasks, goal occurrences, habit cycles, calendarized tasks, capacity snapshots, feedback, memory models, etc.)
* **Query** — the cognitive query engine for world state: tasks, scheduling, **availability**, **semantic slot ranking**, constraints lookup, summaries
* **Updater** — world state updater ensuring **consistency** with task changes; handles **dynamic maintenance**, **load recalculation**, **capacity tracking**, **cache invalidation**, **query‑engine coordination**, **SQLAlchemy persistence**, **future semantic‑memory hooks for learning**, and **comprehensive logging**
* **Validator** — world state & schedule validator; enforces constraints (capacity, availability, blackout, recurrence), detects **task conflicts**, and returns validation results for the flow
* **Evolved State (pilot models)** — abstractions including **CalendarizedTask**, **TimeRange**, **AvailabilityMap**, **CapacityConstraints/CapacityMap**, **BlackoutWindow**, **RecurrencePattern**, **WorldState**, **TaskConflicts**, **WorldStateValidation**, etc.
* **States (Graph State)** — centralized **GraphState** module maintaining the live run state for flows (intent, memory context, partial outputs, world snapshot, router outcomes, etc.)

### 2.2 Dynamic Flow Architecture (graph‑based)

Each user message instantiates a **dynamic flow** (graph) assembled from Cognitive nodes.

**Key elements:**

* **Flow Planner LLM** — receives recognized intent + memory context + world signals; proposes a **node sequence** (the flow) for **this message**
* **Flow Compiler** — builds the runtime graph **on the fly**: adds nodes, edges, attach **routers** & **conditions**, injects observability, validates topology
* **Graph Builder (LangGraph adapter)** — bespoke builder adapted from LangGraph’s `StateGraph` with familiar ops:

  * `add_node`, `add_edge`, `add_conditional_route`, `router`
  * aligns to LangGraph primitives while retaining custom behavior
* **Routers & Conditions** — especially around **`after_confirm_A`** and **`after_confirm_B`** checkpoints; branch outcomes drive continuation, revision, or abort
* **Node Registry / NodeSpec** — formal schema/catalog mapping node names → implementations + contracts; enables stable, testable flow construction

### 2.3 Orchestration & I/O (Telegram → Backend → Graph → DB)

* **Telegram client** = primary real‑time UI
* **Message handler (orchestrator)** executes per message:

  1. **Detect intent** (Intent Recognition LLM)
  2. **Plan flow sequence** (Flow Planner LLM)
  3. **Compile graph** with routers & conditions
  4. **Run graph** (LangGraph engine)
  5. **Return response** to the user (Telegram)
* **FastAPI** acts as the system spine between LangGraph, memory, and DB

---

## 3) Data Model & Schemas (World Model Backbone)

**SQLAlchemy entities (non‑exhaustive, current working set):**

* **Goal (abstract)** — base type

  * **ProjectGoal** — one‑off, deadline‑bound
  * **HabitGoal** — recurring (GFC: goal frequency per cycle; supports goal instances/occurrences per cycle)
* **Plan** — **central orchestration entity**; versions per goal & user; where goals/tasks/cycles/feedback meet
* **Task** — actionable units with estimates, dependencies, status
* **HabitCycle** — recurrence container per habit
* **GoalOccurrence** — specific instance within a cycle
* **ScheduledTask / CalendarizedTask** — time‑mapped tasks
* **CapacitySnapshot** — workload/availability state by period
* **Feedback** — approval/refinement notes per plan
* **Memory models** — episodic, semantic, procedural

**Utilities / functions:**

* **toCalendarizedTask / fromCalendarizedTask** — conversion utilities between logical tasks and calendarized time blocks

**Schemas:**

* **DB‑facing Pydantic schemas** for CRUD/API (aligned with SQLAlchemy)
* **AI‑facing schemas** for LLM I/O (validated intermediate plans); kept **separate** from DB schemas to avoid coupling

---

## 4) Supported Intents (Current Catalog)

These intents drive dynamic flow selection and fallback routing.

```python
SUPPORTED_INTENTS: List[Dict[str, str]] = [
   {"name": "create_new_plan", "description": "User wants to create a new plan for a goal or project."},
   {"name": "edit_existing_plan", "description": "User wants to make minor or specific changes to an existing plan (e.g., update a task, change a deadline, add/remove a step)."},
   {"name": "revise_plan", "description": "User wants to holistically rethink or restructure a plan."},
   {"name": "adaptive_replan", "description": "User is behind schedule and wants to intelligently replan."},
   {"name": "update_task", "description": "User wants to update details of a specific task."},
   {"name": "give_feedback", "description": "User provides feedback on a plan, task, or system behavior."},
   {"name": "pause_goal", "description": "User wants to pause progress on a goal."},
   {"name": "reschedule_task", "description": "User wants to change the scheduled time of a task."},
   {"name": "show_summary", "description": "User requests a summary of plans, goals, or progress."},
   {"name": "undo_last_action", "description": "User wants to undo the most recent change or action."},
   {"name": "add_constraint", "description": "User wants to add a constraint (e.g., time, resource) to a plan or task."},
   {"name": "remove_task", "description": "User wants to remove a task from a plan."},
   {"name": "update_goal", "description": "User wants to update the details or parameters of a goal."},
   {"name": "see_goal_performance", "description": "User wants to see performance metrics for a specific goal."},
   {"name": "see_overall_performance", "description": "User wants to see overall performance metrics across all goals."},
   {"name": "sync_all_plans_across_all_goals", "description": "User wants to synchronize all plans across all goals."},
   {"name": "reset_existing_plan", "description": "User wants to reset a plan to its initial state."},
   {"name": "ask_about_preferences", "description": "User asks about their own preferences or system's understanding of them."},
]
```

---

## 5) Fallback Deterministic Flows (when LLM planning is unavailable)

The **DEFAULT_FLOW_REGISTRY** provides resilient, deterministic node sequences per intent.

```python
DEFAULT_FLOW_REGISTRY = {
    # --- Plan lifecycle ---
    "create_new_plan": [
        "plan_outline_node",
        "user_confirm_a_node",
        "task_generation_node",
        "world_model_integration_node",
        "calendarization_node",
        "validation_node",
        "user_confirm_b_node",
        "persistence_node",
    ],
    "edit_existing_plan": [
        "update_task_node",
        "validation_node",
        "user_confirm_b_node",
        "persistence_node",
    ],
    "revise_plan": [
        "plan_outline_node",
        "user_confirm_a_node",
        "task_generation_node",
        "world_model_integration_node",
        "calendarization_node",
        "validation_node",
        "user_confirm_b_node",
        "persistence_node",
    ],
    "adaptive_replan": [
        "plan_outline_node",
        "task_generation_node",
        "world_model_integration_node",
        "calendarization_node",
        "validation_node",
        "user_confirm_b_node",
        "persistence_node",
    ],
    "reset_existing_plan": [
        "plan_reset_node",
        "plan_outline_node",
        "user_confirm_a_node",
        "task_generation_node",
        "calendarization_node",
        "validation_node",
        "user_confirm_b_node",
        "persistence_node",
    ],

    # --- Task-level operations ---
    "update_task": [
        "update_task_node",
        "validation_node",
        "user_confirm_b_node",
        "persistence_node",
    ],
    "reschedule_task": [
        "reschedule_task_node",
        "validation_node",
        "user_confirm_b_node",
        "persistence_node",
    ],
    "remove_task": [
        "remove_task_node",
        "validation_node",
        "user_confirm_b_node",
        "persistence_node",
    ],

    # --- Goal-level operations ---
    "update_goal": [
        "goal_update_node",
        "plan_outline_node",
        "user_confirm_a_node",
        "task_generation_node",
        "calendarization_node",
        "validation_node",
        "user_confirm_b_node",
        "persistence_node",
    ],
    "pause_goal": [
        "pause_goal_node",
        "persistence_node",
    ],
    # ... additional entries as needed
}
```

> These flows guarantee a working baseline in degraded mode. In healthy mode, the **Flow Planner LLM** produces an intent‑specific dynamic sequence and the **Flow Compiler** instantiates that graph.

---

## 6) The “Brains”: Present State & Upgrade Paths

Currently, two LLM components act as **“brains”**, but neither is fully agentic yet:

* **Intent Recognition LLM** — focuses **only** on intent detection (not an autonomous agent)
* **Flow Planner LLM** — proposes **node sequences** from intent + memory context (also not autonomous)

We have **open questions** about introducing a central orchestrator or upgrading one/both components.

### Option A — **Central Cognitive Controller (Orchestrator Agent)**

A single, **agentic** controller that:

1. Receives user message + memory + world snapshot
2. Determines **intent** (internally or via tool)
3. Drafts an **overarching strategy** for this message/session
4. Delegates **node‑sequence planning** to the Flow Planner (as a tool)
5. Validates results vs. strategy, decides next step, and commits

**Implications:**

* Clear locus of control; simpler global policy & safety enforcement
* Requires richer **tooling** and **state management** for the controller
* Flow Planner can remain simpler while controller ensures coherence

### Option B — **Promote Intent LLM → Main Brain (React‑style)**

Evolve Intent Recognition into a **React agent** with access to tools:

* Detects intent **and** drafts the **strategy**
* Calls Flow Planner LLM as a tool for node‑sequence generation
* Iterates until convergence; aligns with memory/world constraints

**Implications:**

* Reuses current intent entrypoint, adds autonomy
* Keeps Flow Planner modular
* Requires stronger guardrails around tool selection & loop control

### Option C — **Promote Flow Planner → Agentic Strategist**

Make the Flow Planner **define the overarching strategy** **and** the node sequence.

Example of the strategy it would yield for **create_new_plan**:

1. Determine goal type (**project vs habit**)
2. Recall preferences & constraints from **world** and **memories**
3. Produce a **plan outline** and seek **Confirm A**
4. Generate **tasks & occurrences** under constraints
5. Seek **Confirm B**, then **calendarize** and **persist**
6. Notify user of schedule; hand back summary

**Implications:**

* Strong, single place for planning logic
* Risk of overloading one agent; may blur concerns with intent handling

> Decision pending. Short‑term, we can prototype A vs B behind a feature flag and measure observability & failure modes.

---

## 7) Deprecations, Replacements & Enhancements (Candidates)

**Naming & role clarity**

* “Brain” labels → clarify: **Intent Detector**, **Flow Planner**, **Controller**

**Static registries**

* Keep **DEFAULT_FLOW_REGISTRY** for resilience, but shift primary to **LLM‑planned flows**; deprecate any unused static entries

**Graph Builder**

* Consolidate bespoke builder with **LangGraph StateGraph adapter**; ensure all `addNode/addEdge/addConditionalRoute/router` map 1‑to‑1; remove legacy shims

**Routers & Conditions**

* Normalize router outcomes around **Confirm A/B**; extract condition predicates into a shared module for reuse & unit testing

**Memory integration**

* Ensure **episodic/semantic/procedural** are injected consistently into GraphState; add **learned preference hooks** during validation/task‑gen

**World modules**

* Unify **Query/Updater/Validator** contracts; define clear interfaces; add **cache policies** & **invalidations** (time‑ and event‑based)

**Scheduling utilities**

* Harden **toCalendarizedTask/fromCalendarizedTask**; ensure idempotency & reversible mapping; add conflict explanations for UX

**Observability**

* Promote per‑node **audit logging** + structured events; correlate runs across Telegram messages; capture routing decisions & validations

**Capacity model**

* Elevate **CapacitySnapshot** + **AvailabilityMap** to first‑class constraints; move from implicit assumptions to explicit checks

**Testing**

* Golden flows for each intent; deterministic snapshots of node sequences under fixed memory/world inputs

---

## 8) Immediate Next Steps (Execution Checklist)

1. **Decide controller model (A vs B vs C)** and introduce a **feature flag** to allow A/B testing
2. **Refactor Flow Compiler** to:

   * standardize router predicates for Confirm A/B
   * accept **either** LLM‑planned sequences **or** fallback registry
   * emit richer observability (graph topology, branch decisions)
3. **GraphState v2** — unify memory context + world snapshot + router outcomes; formalize a typed schema
4. **World: Validator pass‑through** — return structured conflicts (capacity, blackouts, overlaps) with human‑readable reasons
5. **Updater hooks** — capacity recalculation & cache invalidation on task changes (create/update/delete)
6. **Intent Detector upgrade** — lightweight tool‑enabled reasoning (if Option B)
7. **Flow Planner upgrade** — add strategy section in its output (if Option C)
8. **Telegram integration** — wire full round‑trip: message → graph → reply; log per‑message run IDs
9. **Tests** — golden tests for: create_new_plan, revise_plan, adaptive_replan, reschedule_task
10. **Docs** — keep this checkpoint as the canonical reference; add a brief ADR for the chosen controller model

---

**End of Checkpoint 3** — This document intentionally captures **all** architectural elements you outlined: the Cognitive layers/nodes, Memory (episodic/semantic/procedural + context), World subcomponents (Models/Query/Updater/Validator/Evolved State), GraphState, the Dynamic Flow architecture (Flow Planner LLM, Flow Compiler, Graph Builder adapter, routers/conditions, Node Registry), the Telegram‑to‑Flow orchestrator, the full **SUPPORTED_INTENTS** catalog, the **DEFAULT_FLOW_REGISTRY** mappings, and the open options for a central brain / agentic upgrades.
