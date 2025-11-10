#!/usr/bin/env python3
import os
import sys
import time

# Optional dotenv support
try:
    from dotenv import load_dotenv  # type: ignore
except Exception:  # pragma: no cover
    def load_dotenv(*args, **kwargs):
        return False

# Ensure local package resolution
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

def main():
    load_dotenv(override=False)
    os.environ.setdefault("PLANNING_USE_REACT_AGENT", "true")
    os.environ.setdefault("PLANNING_USE_LLM_TOOLS", "true")

    from app.cognitive.agents.planning_controller import PlanningController
    from app.cognitive.state.graph_state import GraphState

    ctrl = PlanningController()

    session_id = f"cli_session_{int(time.time())}"
    user_id = "cli_user"

    print("Smart Planner CLI — High-Autonomy Agent")
    print("Type your goal/request. Type 'exit' to quit.\n")

    while True:
        try:
            user_input = input("You> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            print("Bye.")
            break

        # Prepare fresh state per turn (agent keeps thread via controller)
        state = GraphState(
            user_input=user_input,
            run_metadata={
                "session_id": session_id,
                "user_id": user_id,
                "entrypoint": "agent_cli",
            },
        )

        result = ctrl.run(state)
        print(f"\nAgent> {getattr(result, 'response_text', '') or '[no response]'}\n")

        # Show last few trace entries for observability
        trace = getattr(result, "planning_trace", None) or []
        tail = trace[-3:]
        if tail:
            print("Trace (last 3):")
            for t in tail:
                op = t.get("operation") or t.get("event") or t.get("stage")
                dur = t.get("duration_ms")
                print(f" - {t.get('component','?')}::{op or '?'}" + (f" [{dur}ms]" if dur else ""))
            print()

if __name__ == "__main__":
    main()