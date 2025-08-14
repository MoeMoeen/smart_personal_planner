# 🧠 Incremental Decomposition Refactor Plan  
**Date:** 14 August 2025  
**Project:** smart_personal_planner  
**Update:** Now includes real memory integration and global task coordination via World Model.

---

## 🎯 Objective
Refactor the current LangGraph-based plan creation workflow to incrementally decompose the LLM's responsibilities into smaller, validated, observable, memory-aware, and globally consistent steps—improving quality, contextual intelligence, trust, and long-term UX consistency **without introducing technical debt**.

---

## ✅ Updated Step-by-Step Plan

### **1. Define the Decomposed Plan Creation Workflow**

Define the planning flow as a series of modular, memory-enhanced, world-aware nodes:

1. **Strategy Interpretation Node**  
   LLM converts user input into a `GoalSpec`.  
   🧠 Retrieves past goals, preferences, user history.

2. **Plan Structure Outline Node**  
   LLM drafts `PlanOutline` (cycles + occurrences).  
   🧠 Adjusted using preferences and context.

3. **User Confirmation A**  
   Shares strategy + outline for approval.  
   🧠 Feedback is logged to memory.

4. **Detailed Task Generation Node**  
   LLM expands each occurrence into tasks.  
   🧠 Preferences + memory shape task styles.

5. **NEW: World Model Integration Step** 🧩  
   Store and access user’s global task state.  
   Provide:
   - All calendarized tasks across all goals  
   - User-defined availability & blackout windows  
   - Total load constraints (daily, weekly)

6. **Calendarization / Time Allocation Node**  
   Assigns task slots using available time from **World Model**.  
   Ensures plan fits into user's actual schedule.

7. **Validation Node**  
   Rule-based checks for:
   - ⛔ Overlapping tasks across plans  
   - ⚖️ Capacity/availability violations  
   - ❌ Broken preferences or scheduling logic

8. **User Confirmation B**  
   Shows final plan; user can approve or revise.

9. **Persistence Node**  
   Saves plan + logs memory object for future reference.

---

### **2. Design Node Interfaces and Data Schemas**

Define shared contract models and world model inputs:

#### 🧱 Contract Models (in `app/contracts/types.py`):
- `GoalSpec`: core goal metadata and constraints
- `PlanOutline`: high-level structure (cycles, occurrences)
- `OccurrenceTasks`: grouped task list per occurrence
- `CalendarizedPlan`: finalized tasks with datetime placement
- `PlanVerificationReport`: validation results

#### 🧠 Memory Models (in `app/contracts/types.py`):
- `MemoryObject`: episodic, semantic, procedural memory entries
- `MemoryContext`: memory bundle for prompt injection

#### 🌍 World Model Inputs (in `app/world/state.py`):
- `CalendarizedTask[]`: global view of tasks across goals
- `CapacityMap`: hours per day/week
- `AvailabilityMap`: allowed time ranges per day (e.g. 8am–6pm)
- [Optional future] `BlackoutWindow[]`: vacations, busy periods

These schemas enable all LangGraph nodes to communicate cleanly, remain testable, and allow for memory & world-model powered reasoning.

---

### **2.5 Add Semantic Memory with Vector DB (for fuzzy recall)**

**Purpose:**  
Enable memory-based LLM prompting by storing and retrieving **semantic memory** — facts, preferences, and context encoded as embeddings.

**Includes:**
- Set up Chroma, Weaviate, or Qdrant
- Implement:
  - `store_semantic_memory(memory: MemoryObject)`
  - `query_semantic_memory(query: str, filters: dict)`
- Automatically embed and store relevant `MemoryObject` instances when:
  - User provides long-form feedback
  - Plans/goals are finalized
  - Preferences or constraints are updated

**Code Location:**
- `app/memory/semantic.py`

**Integration Points:**
- Retrieval used in `retrieve_memory()` to populate `MemoryContext.semantic[]`
- Semantic memory complements Postgres-based episodic/procedural memory

---

### **3. Refactor LangGraph Workflow**
- Break apart current monolithic planner node
- Each node injects memory + reads from world state
- Use retryable, observable nodes with Pydantic contracts

---

### **4. Implement Error Handling, Repair, and Memory Logging**
- Auto-repair or fallback on validation failure
- Write to memory after each successful LLM step
- Log violations and reasons for all rejected plans

---

### **5. Tests: Unit, Flow, and Memory-Based Scenarios**
- Unit tests for each node's logic
- Flow tests across full pipeline
- Memory recall tests
- World state consistency tests (e.g. no overlaps)

---

### **6. API & User Interaction Layer (Telegram/React)**
- Show per-node memory-based explanations:  
  > "Using your previous preference to skip Friday tasks..."
- Plan preview must reflect **global task reality**

---

### **7. Observability & Logging**
- Structured trace logs per run ID
- Token usage, retries, prompt versions
- Snapshot of world state at calendarization

---

### **8. Deploy Incrementally and Monitor**
- Use feature flag `USE_MEMORY_ENHANCED_PLANNING`
- A/B test with baseline planner
- Track plan success, memory utilization, global consistency

---

### **9. Retrospective & Continuous Improvement**
- Assess user experience and plan harmony
- Add world state visualizer/debugger (future)
- Summarize or compress memory as needed

---

✅ Plan now reflects all aspects of Cognitive AI:  
- 💾 Long-term memory (episodic, semantic, procedural)  
- 🌍 World model for consistent global planning  
- 🧠 LLMs with injected context and smart decomposition  
- 🔁 Validation, repair, retry loops
