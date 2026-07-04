"""Config/trigger store for the Simulation Scientist Agent.

The sandbox no longer executes the agent itself — it only holds a small piece
of state the dashboard can edit (run manually now, or every N hours) and that
a separate machine polls and drives (see orchestrator.py / control_client.py,
which run on that machine, not here). This module owns that state file only;
it never spawns a thread or does any work itself.

Communication is always initiated by the polling machine: it reads this state
(claim_run), does the actual work elsewhere, and writes the outcome back
(report_run). The sandbox never calls out to the polling machine.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

STATE_PATH = Path(__file__).resolve().parent / "agent_control.json"

DEFAULT_STATE: dict[str, Any] = {
    "mode": "manual",  # "manual" | "interval"
    "interval_hours": 6.0,
    "max_iterations": 3,
    "ticks_per_iteration": 500,
    "run_requested": False,
    "stop_requested": False,
    "status": "idle",  # "idle" | "running"
    "current_started_at": None,
    "next_run_at": None,
    "history": [],
}

_lock = threading.Lock()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _iso_in(seconds: float) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat()


def _load() -> dict[str, Any]:
    if STATE_PATH.exists():
        try:
            saved = json.loads(STATE_PATH.read_text(encoding="utf-8"))
            return {**DEFAULT_STATE, **saved}
        except Exception:
            pass
    return json.loads(json.dumps(DEFAULT_STATE))


def _save(state: dict[str, Any]) -> None:
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def get_status() -> dict[str, Any]:
    with _lock:
        return _load()


def update_config(
    mode: Optional[str] = None,
    interval_hours: Optional[float] = None,
    max_iterations: Optional[int] = None,
    ticks_per_iteration: Optional[int] = None,
) -> dict[str, Any]:
    with _lock:
        state = _load()
        if mode is not None:
            state["mode"] = mode
        if interval_hours is not None:
            state["interval_hours"] = interval_hours
        if max_iterations is not None:
            state["max_iterations"] = max_iterations
        if ticks_per_iteration is not None:
            state["ticks_per_iteration"] = ticks_per_iteration
        if state["mode"] == "interval" and not state.get("next_run_at"):
            state["next_run_at"] = _iso_in(state["interval_hours"] * 3600)
        if state["mode"] == "manual":
            state["next_run_at"] = None
        _save(state)
        return state


def request_run_now() -> dict[str, Any]:
    with _lock:
        state = _load()
        state["run_requested"] = True
        _save(state)
        return state


def request_stop() -> dict[str, Any]:
    with _lock:
        state = _load()
        state["stop_requested"] = True
        _save(state)
        return state


def claim_run() -> tuple[bool, dict[str, Any]]:
    """Atomically flips idle -> running for the polling machine to act on.
    Returns (claimed, config_snapshot). If already running, claimed is False
    and the snapshot is just the current state (nothing to run)."""
    with _lock:
        state = _load()
        if state["status"] == "running":
            return False, state
        state["status"] = "running"
        state["run_requested"] = False
        state["stop_requested"] = False
        state["current_started_at"] = _now_iso()
        if state["mode"] == "interval":
            state["next_run_at"] = _iso_in(state["interval_hours"] * 3600)
        _save(state)
        return True, state


def report_run(payload: dict[str, Any]) -> dict[str, Any]:
    with _lock:
        state = _load()
        state["status"] = "idle"
        state["current_started_at"] = None
        entry = {**payload, "reported_at": _now_iso()}
        state["history"].append(entry)
        state["history"] = state["history"][-20:]
        _save(state)
        return state
