# LangGraph Node Plan for Smart Personal Planner (Cognitive AI)

## Overview

This document defines the official LangGraph node architecture for the Smart Personal Planner. Each node maps to one or more layers of the 9-layer Cognitive AI architecture and orchestrates key planning functions using memory, reasoning, and world state.

---

## 🧠 Cognitive Node Plan (9-Node Version)

### 1. Strategy Interpretation Node

* **Purpose**: Convert user input into structured `GoalSpec`
* **Type**: LLM Node
* **Input**: Natural language user request (via chat or API)
* **Output**: `GoalSpec` (structured representation of the user's goal)
* **Layers Activated**: Communication, Perception, Memory
* **Memory Hook**: Injects past goals, user preferences, history

---

### 2. Plan Structure Outline Node

* **Purpose**: Generate `PlanOutline` (occurrences, cycles)
* **Type**: LLM Node
* **Input**: `GoalSpec`
* **Output**: `PlanOutline`
* **Layers Activated**: Planning, Reasoning, Memory
* **Memory Hook**: Suggest cycle logic based on learned structures

---

### 3. User Confirmation A

* **Purpose**: Ask user to confirm goal and outline
* **Type**: User IO Node
* **Input**: `GoalSpec`, `PlanOutline`
* **Output**: Feedback (`approved: bool`, corrections)
* **Layers Activated**: Communication, Reflection
* **Memory Hook**: Store approval/rejection feedback as `Episodic`

---

### 4. Detailed Task Generation Node

* **Purpose**: Expand each occurrence into structured tasks
* **Type**: LLM Node
* **Input**: `PlanOutline`
* **Output**: `OccurrenceTasks[]`
* **Layers Activated**: Planning, Reasoning, Memory
* **Memory Hook**: Influence style/detail of tasks

---

### 5. World Model Integration Step

* **Purpose**: Inject current calendar, blackouts, capacity
* **Type**: Tool Node
* **Input**: `OccurrenceTasks[]`
* **Output**: Context-enriched `OccurrenceTasks[]`
* **Layers Activated**: World Model, Perception
* **Memory Hook**: Read global task reality, no write

---

### 6. Calendarization / Time Allocation Node

* **Purpose**: Assign time slots to each task
* **Type**: LLM + Tool Combo
* **Input**: Tasks + availability
* **Output**: `CalendarizedPlan`
* **Layers Activated**: Planning, Execution, World Model
* **Tool Call**: `WorldQueryEngine.find_available_slots()`

---

### 7. Validation Node

* **Purpose**: Rule-based check for overlaps, violations
* **Type**: Tool Node
* **Input**: `CalendarizedPlan`
* **Output**: `PlanVerificationReport`
* **Layers Activated**: Perception, Reasoning
* **Tool Call**: `WorldValidator.validate_plan()`

---

### 8. User Confirmation B

* **Purpose**: Show final plan to user for approval
* **Type**: User IO Node
* **Input**: `CalendarizedPlan`, `PlanVerificationReport`
* **Output**: Approval or revision notes
* **Layers Activated**: Communication, Reflection
* **Memory Hook**: Logs user final response as episodic

---

### 9. Persistence Node

* **Purpose**: Save plan to DB, log memory object
* **Type**: Tool Node
* **Input**: `CalendarizedPlan`
* **Output**: Confirmation or error
* **Layers Activated**: Memory, Execution
* **Tool Call**: `WorldUpdater.apply_plan()` + `memory.store_semantic()`

---

## 🧠 Summary Table

| Node # | Node Name                | Type     | Core Layer(s)         | Main Output              |
| ------ | ------------------------ | -------- | --------------------- | ------------------------ |
| 1      | Strategy Interpretation  | LLM      | Perception, Memory    | `GoalSpec`               |
| 2      | Plan Structure Outline   | LLM      | Planning, Reasoning   | `PlanOutline`            |
| 3      | User Confirmation A      | User IO  | Communication         | `ApprovalFeedback`       |
| 4      | Detailed Task Generation | LLM      | Planning, Memory      | `OccurrenceTasks[]`      |
| 5      | World Model Integration  | Tool     | World Model           | Context-injected tasks   |
| 6      | Calendarization          | LLM+Tool | Planning, Execution   | `CalendarizedPlan`       |
| 7      | Validation               | Tool     | Reasoning, Perception | `PlanVerificationReport` |
| 8      | User Confirmation B      | User IO  | Reflection            | Final feedback           |
| 9      | Persistence              | Tool     | Execution, Memory     | Save confirmation        |
