
**Date:** 13 October 2025
**Owner:** Moe Moeen
**Scope:**


---

# 🧭 Smart Personal Planner — Integrated Hierarchy Model (v1.2)

> **This version fully includes v1.0 + v1.1**: canonical terms, dual-axis, PlanOutline→Roadmap→Schedule, PlanContext vs RoadmapContext, Strategic Adaptation Layer, Multi-Goal Balancer, Dynamic Node Expansion, Cycle–Phase flexibility, AdaptationLog lineage, plus all validated examples.
> **New in v1.2**: Plan Pattern Taxonomy with **Progressive Accumulation Arc** umbrella + subtypes, **Planning Grammar**, **Contextual Inference Layer**, **Pattern metadata**.

---

## 0) Canonical Terminology (preserved)

* **Entity:** `PlanNode` (the only structural unit across all layers).
* **`PlanNode.node_type`:** `goal`, `phase`, `cycle`, `sub_goal`, `task`, `sub_task`, `micro_goal`.
* **`PlanNode.level`:** dynamic (L1…Ln), no fixed limit.
* **`PlanNode.origin`:** `system`, `user_feedback`, `ai_adaptation`.
* **`PlanNode.recurrence`:** `none`, `daily`, `weekly`, `monthly`, `quarterly`, `yearly`.
* **PlanOutline:** conceptual skeleton (no dates).
* **Roadmap:** operational realization (concrete but non-temporal).
* **Schedule:** time-bound instantiation (dates, durations, recurrence).
* **PlanContext:** AI + user **meta** assumptions (global, conceptual).
* **RoadmapContext:** **real-world** parameters (scope, budget, region, horizon).
* **PlanAdaptationLog:** versioned log of all structural/timing changes (who/why/what/strategy).
* **UserStrategyProfile:** adaptation mode preference.
* **MultiGoalBudget / Balancer:** cross-goal time/energy constraints & trade-offs.

---

## 1) Conceptual Overview (preserved)

```
USER GOAL (L1)
  ↓
PLAN OUTLINE (conceptual skeleton)
  ↓
PlanNodes Graph (phases, cycles, sub_goals, tasks, sub_tasks, micro_goals)
  ↓
PLAN CONTEXT (AI + user meta assumptions)
  ↓
ROADMAP (operational realization)
  ↓
ROADMAP CONTEXT (real-world specifics)
  ↓
SCHEDULE (time-bound instantiation)
  ↓
PLAN ADAPTATION LOG (all changes + reasons)
  ↓
STRATEGIC ADAPTATION LAYER (push / relax / hybrid / manual)
  ↓
MULTI-GOAL BALANCER (portfolio-wide feasibility)
```

* **Lineage preserved:** same `PlanNode` IDs trace from Outline → Roadmap → Schedule.

---

## 2) Dual-Axis PlanNode Graph (preserved)

**Vertical axis (depth):** L1 Goal → L2 Phase/Cycle → L3 Sub-Goal → L4 Task → L5 Sub-Task / Micro-Goal.
**Horizontal axis (breadth):** parallel **streams** (phases can overlap; cycles recur).

```
Goal (L1)
├─ Stream / Phase A (may overlap)
│   ├─ Sub-Goal
│   │   ├─ Task
│   │   │   ├─ Sub-Task
│   │   │   └─ Micro-Goal
│   └─ Sub-Goal
├─ Stream / Cycle B (recurring)
│   ├─ Sub-Goal
│   └─ Task (+ recurring sub_tasks)
└─ Stream C (optional)
```

* **Cycle–Phase flexibility:** Streams may be **phases** (sequential/overlapping) or **cycles** (recurring), or both (nested).

---

## 3) Data-Model Alignment (preserved + clarified)

| Entity                  | Description                        | Key Fields (incl. v1.1 addenda)                                                                       |
| ----------------------- | ---------------------------------- | ----------------------------------------------------------------------------------------------------- |
| **Goal**                | Top-level intent                   | `id`, `title`, `pattern_type` (v1.2), `subtype` (v1.2), `priority_weight`                             |
| **PlanOutline**         | Conceptual skeleton                | Graph of `PlanNode`s + `PlanContext`                                                                  |
| **PlanContext**         | AI+user meta assumptions           | e.g., preferred intensity, hours/week, strategy hint                                                  |
| **Roadmap**             | Operational realization of outline | Same `PlanNode` graph + `RoadmapContext`                                                              |
| **RoadmapContext**      | Real-world specifics               | e.g., location, budget, time horizon, venue                                                           |
| **Schedule**            | Time binding                       | start/end, recurrence, dependencies                                                                   |
| **PlanNode**            | Generic hierarchy node             | `id`, `parent_id`, `node_type`, `level`, `origin`, `recurrence`, `dependencies`, `status`, `progress` |
| **PlanAdaptationLog**   | Change history                     | `timestamp`, `node_ids`, `action`, `reason`, `origin`, `strategy_applied`, `portfolio_impact`         |
| **UserStrategyProfile** | Strategy policy                    | `mode` in {push, relax, hybrid, manual}, weights                                                      |
| **MultiGoalBudget**     | Portfolio constraints              | time/energy caps, conflict resolutions                                                                |

---

## 4) Strategic Adaptation Layer (preserved)

* **Modes:** `push`, `relax`, `hybrid`, `manual`.
* **Behavior:** governs *how* adaptations occur (compress, catch-up, skip, merge, extend).
* **Portfolio-aware:** consults **Multi-Goal Balancer** before changes to avoid starving other goals.
* **Logged:** `PlanAdaptationLog.strategy_applied` stores the mode per change.

---

## 5) Cycle–Phase Flexibility (preserved)

* **Phases** = conceptual progression (may overlap).
* **Cycles** = recurring containers (habit loops, repeating projects).
* They can **coexist** and **nest** (e.g., phases with an end-of-phase recurring mini-project cycle).
* AI can **lift** a cycle from within a phase to an independent stream if the user continues it indefinitely.

---

## 6) Dynamic Node Expansion / Contraction (preserved)

* **Triggers:** user feedback or AI observation.
* **Actions:** add/move/remove/merge `PlanNode`s at any depth; regenerate dependent schedules; always log changes with `origin` + `strategy_applied`.
* **Example (kept):** per-session reflections added as **L5** `sub_task` under each session (massage goal).
* **Example (kept):** micro-goal “Startup finance basics” added under CTO roadmap.

---

## 7) Validated Examples (preserved)

1. **Buy a house in ~2 years** — *milestone project*

   * Phases (financial readiness runs **in parallel** with later phases), sub_goals, tasks.
   * **RoadmapContext** matters (budget, region); **Schedule** assigns saves, viewings, offers.

2. **Read 1 general history + 1 U.S. history per month** — *recurring cycles with goal segmentation*

   * **Two separate Goals** (General vs U.S. history) reusing same Outline template.
   * Monthly **cycle** → select book, reading sessions, summary, spaced reviews.

3. **Get familiar with Jungian psychology** — *progressive accumulation (learning_arc)*

   * **Phases**: Orientation → Deep Reading → Application; recurring reflection cadence.

4. **Become CTO (Series B+)** — *strategic transformation*

   * **Parallel phase streams** (Foundation, Capability, Visibility, Transition); micro-goals as gaps arise; portfolio-aware adaptations.

5. **Massage: 2 per month for 12 months** — *simple recurring_cycle*

   * Monthly **cycle**; user adds per-session reflections → **L5** expansion under each session; strategy changes catch-up vs skip.

6. **Walk daily (indefinite)** — *simple recurring_cycle*

   * Daily recurring **task** inside monthly container; weather fallback; strategy-based make-up vs lighten.

7. **Build 1 AI project / quarter** — *hybrid_project_cycle*

   * **Cycle** per quarter; within each cycle **phases** (Ideation → Dev → Deploy → Reflect); portfolio balancing during sprint weeks.

8. **Learn Python & apply via mini-projects** — *progressive accumulation + nested cycles*

   * **Phases** (Fundamentals → APIs → OOP → Advanced) each ending with a **mini-project cycle**; could later lift cycles to a standalone ongoing stream.

---

## 8) Plan Pattern Taxonomy (v1.2 **addition**)

Each Goal/Outline declares a **`pattern_type`** and optional **`subtype`** to guide structure & defaults.

### A) Primary pattern families

| `pattern_type`                 | Description                             | Typical Structure                   | Examples                      |
| ------------------------------ | --------------------------------------- | ----------------------------------- | ----------------------------- |
| `milestone_project`            | One-off project with defined end        | Phases → Tasks                      | Buy a house, Publish a book   |
| `recurring_cycle`              | Habitual repetition                     | Cycle → Task                        | Walk daily, Massages 2×/month |
| `progressive_accumulation_arc` | Gradual, sequential build-up            | Phases (+ optional cycles)          | Learn Python, Marathon        |
| `hybrid_project_cycle`         | Repeating projects with internal phases | Cycles → Phases → Tasks             | 1 AI project/quarter          |
| `strategic_transformation`     | Long-term multi-stream change           | Parallel phases → sub_goals → tasks | Become CTO                    |

### B) Subtypes under `progressive_accumulation_arc`

| `subtype`         | Domain         | Example                   |
| ----------------- | -------------- | ------------------------- |
| `learning_arc`    | Knowledge      | Jung, Python              |
| `training_arc`    | Physical/skill | Marathon, strength blocks |
| `creative_arc`    | Artistic       | Photography portfolio     |
| `career_arc`      | Role growth    | Junior → Senior track     |
| `therapeutic_arc` | Behavioural    | Mindfulness program       |
| `financial_arc`   | Economic       | Investment literacy       |

> **Pattern-aware defaults:** reflection frequency, typical sub-structures, and adaptation tendencies can be pre-configured per pattern/subtype.

---

## 9) Planning Grammar (v1.2 **addition**)

**Purpose:** ensure every composed plan is structurally valid and actionable.

### 9.1 Base grammar (cardinality)

```
Goal
 ├─ (Phase | Cycle)*          # 0..n streams allowed; may coexist
 │    ├─ Sub-Goal*            # 0..n
 │    │    ├─ Task+           # 1..n (must lead to action)
 │    │    │    └─ Sub-Task*  # 0..n
 │    │    │          └─ Micro-Goal*  # 0..n (AI/user-added)
```

### 9.2 Rules

1. Every `Goal` must have ≥1 descendant `task`.
2. **Phases** may overlap (temporal concurrency supported).
3. **Cycles** recur; can include structured sub-phases if the cycle itself has stages.
4. **Micro-goals** can be injected at any depth (gap-filling).
5. Depth is unbounded; AI may **expand** or **collapse** based on feedback and progress.
6. **Dependencies** across streams are supported (`PlanNode.dependencies`).
7. Schedule must satisfy dependencies and recurrence constraints.

### 9.3 Schema validation

* Outline composition is validated against grammar before Roadmap/Schedule generation.
* Violations produce corrective prompts (e.g., “No actionable tasks detected under Sub-Goal X — shall I add a default task?”).

---

## 10) Contextual Inference Layer (v1.2 **addition**)

**Goal:** choose the **pattern** and **grammar subset** that fits the user’s intent.

### 10.1 Signals considered

* Lexical cues (“learn”, “every week”, “by [date]”, “become”, “build one per quarter”).
* Time horizon (fixed end vs open-ended).
* Recurrence hints (habit vs project).
* Domain markers (fitness, study, career).
* UserStrategyProfile (push/relax defaults).

### 10.2 Mapping (examples)

| Detected intent           | Pattern chosen                                  | Grammar subset                          |
| ------------------------- | ----------------------------------------------- | --------------------------------------- |
| “Learn/Study/Master X”    | `progressive_accumulation_arc` (`learning_arc`) | Phases (+ optional mini-project cycles) |
| “Do X every week/month”   | `recurring_cycle`                               | Cycle → Tasks (+ optional sub_tasks)    |
| “Achieve X by [date]”     | `milestone_project`                             | Phases → Tasks                          |
| “Build one X per quarter” | `hybrid_project_cycle`                          | Cycle → Phases → Tasks                  |
| “Become/Transform into Y” | `strategic_transformation`                      | Parallel phases → sub_goals → tasks     |

---

## 11) Declarative Pattern Metadata (v1.2 **addition**)

```python
patterns = {
  "progressive_accumulation_arc": {
    "allowed_axes": ["vertical", "horizontal"],
    "vertical_levels": ["goal", "phase", "sub_goal", "task", "sub_task"],
    "optional_nested_cycles": True,
    "default_reflection": "per_phase"
  },
  "recurring_cycle": {
    "allowed_axes": ["vertical"],
    "vertical_levels": ["goal", "cycle", "task", "sub_task"],
    "optional_phases": False,
    "default_reflection": "per_cycle"
  },
  "milestone_project": {
    "allowed_axes": ["vertical"],
    "vertical_levels": ["goal", "phase", "task", "sub_task"],
    "optional_cycles": False,
    "default_reflection": "per_phase"
  },
  "hybrid_project_cycle": {
    "allowed_axes": ["vertical", "horizontal"],
    "vertical_levels": ["goal", "cycle", "phase", "task", "sub_task"],
    "optional_phases": True,
    "optional_cycles": True
  },
  "strategic_transformation": {
    "allowed_axes": ["vertical", "horizontal"],
    "vertical_levels": ["goal", "phase", "sub_goal", "task", "sub_task"],
    "parallel_streams": True
  }
}
```

---

## 12) Evolution Lifecycle (preserved)

```
User Intent
 → (Goal Segmentation if needed)
 → PlanOutline + PlanContext
 → Roadmap + RoadmapContext
 → Schedule
 → Feedback & Observation
 → Strategic Adaptation Layer (governed by user strategy)
 → Multi-Goal Balancer (portfolio feasibility)
 → PlanAdaptationLog (transparent history)
 → Loop
```

---

## 13) Invariants & Principles (preserved + extended)

1. **Single Structural Engine:** `PlanNode` powers all layers.
2. **Persistent Lineage:** `PlanNode` IDs persist through versions/stages.
3. **Context Separation:** PlanContext (meta) vs RoadmapContext (real-world).
4. **Dynamic Depth:** unlimited L2…Ln; expand/collapse at will.
5. **Parallel Streams:** phases can overlap; cycles recur.
6. **Strategic Intelligence:** adaptation governed by strategy mode.
7. **Portfolio Awareness:** Multi-Goal Balancer mediates cross-goal trade-offs.
8. **Transparent History:** every mutation recorded with cause + strategy.
9. **Semantic Consistency:** only canonical terms (no synonyms).
10. **Pattern-Aware Reasoning:** structure chosen via pattern + grammar.
11. **Actionability Guarantee:** every Goal resolves to actionable Tasks.

---

## 14) Schema Additions (preserved from v1.1 + v1.2 fields)

```python
class Goal(BaseModel):
    id: UUID
    title: str
    pattern_type: Literal[
        "milestone_project",
        "recurring_cycle",
        "progressive_accumulation_arc",
        "hybrid_project_cycle",
        "strategic_transformation"
    ]
    subtype: Optional[str]  # e.g., "learning_arc", "training_arc", ...
    priority_weight: float
```

*(Other entities remain as specified; `PlanNode` includes `origin`, `recurrence`, `dependencies`, `status`, `progress`.)*

---

### ✅ v1.2 Summary

* **Everything from v1.0 & v1.1 is retained** (no drops).
* **New**: Pattern taxonomy (with **Progressive Accumulation Arc** umbrella + subtypes), **Planning Grammar**, **Contextual Inference Layer**, **Pattern metadata** to guide composition.
* The system remains **dual-axis**, **strategy-aware**, **portfolio-aware**, and **fully transparent**.

---

############################################################################################################################################################################################################################################################################################################################
---

# What the Planning Node is (in simple terms)

It’s the place where a user’s **goal** is turned into a **structured plan**:

1. pick the **right pattern** for the goal (habit, project, progressive mastery, hybrid, transformation),
2. build a valid **PlanNode** structure using our **planning grammar**,
3. produce **PlanOutline → Roadmap → Schedule**, ready for confirmation.

---

# The Dual-Axis Model (how we think in 2 directions at once)

* **Vertical axis (depth / detail)** = how far we break things down from abstract to concrete.
* **Horizontal axis (breadth / streams)** = what runs **in parallel** (phases, cycles, domains).

Think of a **matrix**: we can zoom **down** for detail (L1→L5) and move **sideways** across streams (overlapping phases or recurring cycles).

**Examples**

* **Buy a house**: multiple **streams** (Finance, Search, Paperwork) run **in parallel**; each stream has its **own tasks** (vertical depth).
* **Learn Python**: **phases** (Fundamentals → APIs → OOP → Advanced) run left-to-right; inside each phase we drill **down** into tasks; some phases include a **cycle** (a mini-project every ~6 weeks).

---

# The Hierarchy: L1…L5 (PlanNode levels & node_type)

| Level  | What it represents                              | `node_type` (canonical)        | Example (Learn Python)                    |
| ------ | ----------------------------------------------- | ------------------------------ | ----------------------------------------- |
| **L1** | The goal itself                                 | `goal`                         | Learn Python & apply in mini-projects     |
| **L2** | High-level containers (sequential or recurring) | `phase` or `cycle`             | Phase 2: Data & APIs                      |
| **L3** | Intermediate objectives                         | `sub_goal` (or nested `cycle`) | “Master HTTP + JSON + requests”           |
| **L4** | Concrete, do-able steps                         | `task`                         | “Build an API client and parse responses” |
| **L5** | Smallest additions / refinements                | `sub_task` or `micro_goal`     | “Write README”, “Log a reflection”        |

> Depth is **dynamic**: the AI can stop at L3 for a simple habit, or go to L5+ for a complex plan.

---

# How the Planning Node builds plans (grammar + patterns, simply)

1. It detects **which pattern** fits:

   * `milestone_project` (e.g., buy a house)
   * `recurring_cycle` (e.g., walk daily, massages)
   * `progressive_accumulation_arc` (e.g., learn Python; training arcs)
   * `hybrid_project_cycle` (e.g., 1 AI project/quarter)
   * `strategic_transformation` (e.g., become CTO)

2. It composes a PlanNode graph using the **planning grammar**:

```
Goal
 ├─ Phase* and/or Cycle*
 │    ├─ Sub-Goal*
 │    │    ├─ Task+     (must reach actionability)
 │    │    │    └─ Sub-Task*/Micro-Goal*
```

3. It validates the structure (must have actionable tasks), then moves on to **Roadmap**.

---

# Roadmap: what exactly gets decided here (options & context)

The **Roadmap** is the **operational** version of the Outline: concrete but still **non-temporal**.
We fill in **RoadmapContext**: scope, location, budget, cadence, tech stack, constraints—details that make the plan **real-world**.

**Common Roadmap options by pattern (examples)**

| Pattern                        | Typical Roadmap decisions                                             | Example                                                                          |
| ------------------------------ | --------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| `milestone_project`            | Streams/phases, gating criteria, artifact checklists, external actors | **Buy a house**: budget band, target areas, lender short-list, viewing cadence   |
| `recurring_cycle`              | Cadence rules, per-cycle tasks, exceptions/fallbacks                  | **Massages 2×/mo**: venue, price, “book by 3rd”, 10-day spacing, reflections     |
| `progressive_accumulation_arc` | Phase scope, learning resources, practice formula, reflection cadence | **Learn Python**: topics per phase, 6-week mini-project template, repo standards |
| `hybrid_project_cycle`         | Cycle template + internal phases, portfolio conventions               | **1 AI project/qtr**: ideate→build→deploy→reflect; video demo + README           |
| `strategic_transformation`     | Parallel streams, capability ladders, signaling routines              | **Become CTO**: capability track, visibility track, transition milestones        |

---

# Schedule: the time-bound layer (after Roadmap)

Once the Roadmap is concrete, we generate a **Schedule** (dates, durations, recurrences), respecting dependencies and the user’s availability (and later, calendar sync).

* **Daily Walk**: 18:30 every day (flex 15m), weekly check-in Sun 19:30.
* **AI Project/qtr**: Q1–Q4 cycles with internal phase windows.
* **Massages**: 2× monthly spaced ≥10 days, reflections immediately after each session.

---

# How the AI adapts (dynamic, strategy-aware)

The Planning Node (and later the Reflection/Adaptation flow) is **alive**: it learns and reshapes plans based on **progress, constraints, and feedback**.

### What can change dynamically

* **Depth**: add/remove levels (e.g., add L5 “per-session reflection” under each massage session).
* **Breadth**: split or merge **streams** (e.g., add a “visibility” stream in CTO).
* **Reschedule**: compress/extend dates, add **catch-ups**, or lighten cadence.
* **Resync**: rebalance across **other goals** using the Multi-Goal Balancer.
* **Refactor**: merge redundant tasks, insert micro-goals, lift a cycle out into its own stream.

### How strategy shapes adaptations

* **Push (achievement-driven)**: catch-ups, compressed phases, temporary extra sessions.
* **Relax (sustainability-driven)**: skip/extend, lighten weekly load, accept slips.
* **Hybrid**: push when capacity is high; relax during overload.
* **Manual**: always ask the user before structural/time changes.

**Examples**

* **Massages (missed both in Feb)**:

  * Push → 3 sessions in March (catch-up), possibly shorten other goals that week.
  * Relax → accept skipped cycle; return to normal cadence in March.
* **Daily Walk (missed today)**:

  * Push → add a short make-up tomorrow morning; keep evening light walk.
  * Relax → no make-up; if misses pile up, auto-reduce to 20 min for a week.
* **Learn Python (behind in Week 5)**:

  * Push → extend daily study to 90m; keep project on schedule.
  * Relax → delay mini-project by a week.

All changes are recorded in **PlanAdaptationLog** with `origin` (user_feedback / ai_adaptation) and `strategy_applied`.



---

# Quick end-to-end picture with our examples

1. **User**: “I want to build one AI project every 3 months.”
2. **Pattern**: `hybrid_project_cycle`.
3. **Outline**: `cycle (quarterly)` → internal `phases (ideate→build→deploy→reflect)` → `tasks`.
4. **Roadmap**: tech stack, portfolio rules, demo requirement, buffer week.
5. **Schedule**: Q1–Q4 with phase windows; sprints slotted to nights/weekends.
6. **Adaptation**: If behind, **Push** adds a weekend sprint and trims reading that week; **Relax** extends cycle to 4 months.

---

# What Planning Actually Requires

Let’s recall what happens inside the Planning Node:

* It receives an intent (e.g., “Plan a new goal: Learn Python”).

* It must reason structurally (pattern selection, grammar composition).

* It must query user context (available time, preferences, constraints).

* It must iterate and adjust (back-and-forth refinement).

* It must finally produce an approved structure (PlanOutline + Roadmap).

* It must hand it off to the confirmation node cleanly.

That’s a loop, not a one-shot generation.

***Hence, the Planning Node is an autonomous agentic subsystem, not a single LLM prompt.***


## TL;DR

* The **dual-axis** view lets us think **down** (detail) and **across** (parallel streams) at once.
* The **hierarchy** (L1…L5) runs from **goal → phase/cycle → sub_goal → task → sub_task/micro_goal**.
* The AI is **dynamic**: it decides how many levels to use, which building blocks fit, and it can **merge/extend/reschedule/resync** based on progress, constraints, and **strategy** (push/relax/hybrid/manual).
* The **Roadmap** is always explicit: it’s the **real-world, non-temporal** layer (context and options) before we generate a **Schedule**.

