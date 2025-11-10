"""
Lightweight run-events collector to summarize tool sequence and QC decisions.

Usage:
- Controller calls start_run() before agent invocation and end_run() after.
- Tools optionally call record_event(...) at key points.
- Controller can attach the collected events to GraphState.run_metadata['run_events']
  and optionally echo a compact stream when PLANNING_DEBUG=1.
"""
from __future__ import annotations

from typing import Any, Dict, List
import threading
import time
import os

_tls = threading.local()


def start_run() -> None:
    _tls.events = []  # reset per run


def record_event(event_type: str, **fields: Any) -> None:
    ev = {
        "t": int(time.time() * 1000),
        "type": event_type,
    }
    ev.update(fields)
    events: List[Dict[str, Any]] = getattr(_tls, "events", None) or []
    events.append(ev)
    _tls.events = events

    # Optional live echo for debugging (minimal, single-line)
    if os.getenv("PLANNING_DEBUG") in ("1", "true", "True"):
        label = fields.get("label") or fields.get("name") or fields.get("stage") or event_type
        outcome = fields.get("outcome") or fields.get("qc_action") or fields.get("ok")
        print(f"[events] {label}: {outcome}")


def end_run() -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = getattr(_tls, "events", None) or []
    _tls.events = []
    return events
