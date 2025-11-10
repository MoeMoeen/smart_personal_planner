#!/usr/bin/env python3
import os
import sys
import time
import argparse

# Optional dotenv support (do not hard-crash if missing)
try:
    from dotenv import load_dotenv  # type: ignore
except Exception:  # pragma: no cover
    def load_dotenv(*args, **kwargs):  # fallback no-op
        return False

# Ensure local package resolution
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

def run(goal: str, debug: bool = False):
    # Load environment (.env) and ensure unbuffered output for logs
    load_dotenv(override=False)
    os.environ.setdefault("PYTHONUNBUFFERED", "1")
    os.environ.setdefault("PLANNING_USE_REACT_AGENT", "true")
    os.environ.setdefault("PLANNING_USE_LLM_TOOLS", "true")
    if debug:
        os.environ["PLANNING_DEBUG"] = "1"

    # Friendly check for API key when making real LLM calls
    if not os.getenv("OPENAI_API_KEY"):
        print("[error] OPENAI_API_KEY not set. Export it or add to .env for real LLM calls.")
        print("        Example: export OPENAI_API_KEY=sk-...\n")
        # Continue anyway to allow controller to respond with guidance

    # Import here after sys.path adjustments
    from app.cognitive.agents.planning_controller import PlanningController
    from app.cognitive.state.graph_state import GraphState

    state = GraphState(
        user_input=goal,
        run_metadata={
            "session_id": f"oneshot_{int(time.time())}",
            "user_id": "oneshot_user",
            "entrypoint": "run_one_shot",
        },
    )

    ctrl = PlanningController()
    out = ctrl.run(state)
    print("\n=== RESULT ===")
    print(getattr(out, "response_text", "") or "[no response]")
    print("\n=== TRACE (last 5) ===")
    for t in (out.planning_trace or [])[-5:]:
        print(t)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a single high-autonomy planning turn")
    parser.add_argument("goal", nargs="?", default="Help me learn piano in 6 months and play 3 simple songs.", help="User goal or request")
    parser.add_argument("--debug", action="store_true", help="Enable compact run-event echo (PLANNING_DEBUG=1)")
    args = parser.parse_args()
    run(args.goal, debug=args.debug)