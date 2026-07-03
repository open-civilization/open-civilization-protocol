"""In-process (no SSH) research loop for the Simulation Scientist Agent.

Designed to run *inside* the same web server process that serves the live
dashboard UI (simulation/ocp/server.py). This is architecturally different
from loop.py's SSH-based autonomous loop, which deploys to and restarts a
remote sandbox — doing that here would restart the very process serving the
UI request that triggered it, killing the user's connection mid-click.

Instead, each iteration:
1. Runs a one-shot audit in a FRESH subprocess (not an in-process call),
   so it always imports the current on-disk engine.py rather than whatever
   was cached in this process's module table at import time — this matters
   because later iterations write new code to disk that this process never
   re-imports itself.
2. Feeds that report to the theory-discovery and advisor modules (pure
   analysis + LLM calls, no simulation state involved, safe to call directly
   in this process).
3. Applies the resulting proposal (parameter or code edit) to engine.py on
   disk.

The live simulation object already running in server.py is never touched,
restarted, or reloaded — it keeps serving the dashboard with whatever code
was loaded when the server started. Picking up agent-authored changes in
the live simulation is a deliberate, separate action (a manual server
restart), not something this loop does automatically.
"""

from __future__ import annotations

import json
import subprocess
import sys
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

from . import advisor, discovery

THEORIES_PATH = Path(__file__).resolve().parent / "theories.py"
THEORY_DOCS_DIR = Path(__file__).resolve().parent / "theories"


@dataclass
class LocalIterationLog:
    iteration: int
    ticks_requested: int
    audit_ok: bool
    audit_error: Optional[str]
    final_population: int
    findings: list[dict[str, Any]]
    theory_findings: list[dict[str, Any]]
    discovery_message: str
    discovered_theory: Optional[str]
    proposal: dict[str, Any]
    apply_result: Optional[dict[str, Any]]


def _run_audit_subprocess(repo_root: Path, ticks: int, seed_base: int, timeout: float) -> tuple[Optional[dict], Optional[str]]:
    """Runs `run_simulation_scientist.py audit` as a fresh subprocess so it always picks
    up whatever is currently on disk, returning the parsed JSON report."""
    cli_script = repo_root / "run_simulation_scientist.py"
    try:
        result = subprocess.run(
            [sys.executable, str(cli_script), "audit",
             "--runs", "1", "--ticks", str(ticks), "--seed-base", str(seed_base), "--format", "json",
             "--include-raw-data"],
            capture_output=True, text=True, cwd=str(repo_root), timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return None, f"Audit subprocess timed out after {timeout}s."
    if result.returncode != 0:
        return None, f"Audit subprocess failed (exit {result.returncode}): {result.stderr[-2000:]}"
    try:
        return json.loads(result.stdout), None
    except json.JSONDecodeError as exc:
        return None, f"Could not parse audit subprocess output as JSON: {exc}"


class LocalAgentRunner:
    """Owns the background thread and shared, lock-protected status the FastAPI
    endpoints poll. One instance is created at server startup and reused across runs
    (a new run resets its state rather than creating a new object each time)."""

    def __init__(self, repo_root: Path, engine_path: Path):
        self.repo_root = repo_root
        self.engine_path = engine_path
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._stop_requested = False
        self.status: dict[str, Any] = {
            "running": False,
            "current_iteration": 0,
            "max_iterations": 0,
            "iterations": [],
            "error": None,
        }

    def get_status(self) -> dict[str, Any]:
        with self._lock:
            return json.loads(json.dumps(self.status, default=str))  # cheap deep copy

    def start(self, max_iterations: int, ticks_per_iteration: int, seed_base: int = 1000) -> tuple[bool, str]:
        with self._lock:
            if self.status["running"]:
                return False, "Agent is already running."
            self.status = {
                "running": True,
                "current_iteration": 0,
                "max_iterations": max_iterations,
                "iterations": [],
                "error": None,
            }
            self._stop_requested = False
        self._thread = threading.Thread(
            target=self._run, args=(max_iterations, ticks_per_iteration, seed_base), daemon=True,
        )
        self._thread.start()
        return True, "Started."

    def request_stop(self) -> None:
        with self._lock:
            self._stop_requested = True

    def _run(self, max_iterations: int, ticks_per_iteration: int, seed_base: int) -> None:
        try:
            for i in range(1, max_iterations + 1):
                with self._lock:
                    if self._stop_requested:
                        break
                    self.status["current_iteration"] = i

                report, audit_error = _run_audit_subprocess(
                    self.repo_root, ticks_per_iteration, seed_base + i, timeout=300,
                )
                if report is None:
                    it_log = LocalIterationLog(
                        iteration=i, ticks_requested=ticks_per_iteration,
                        audit_ok=False, audit_error=audit_error,
                        final_population=0, findings=[], theory_findings=[],
                        discovery_message="skipped (audit failed)", discovered_theory=None,
                        proposal={"hypothesis": "", "action": "none", "rationale": audit_error or "unknown error"},
                        apply_result=None,
                    )
                    with self._lock:
                        self.status["iterations"].append(asdict(it_log))
                    break

                run = report["runs"][0] if report.get("runs") else {}
                final_pop = int(run.get("final_population", 0))
                raw_history = run.get("raw_history") or []
                raw_state = run.get("raw_state") or {}

                discovery_message = "disabled"
                discovered_theory = None
                if not raw_history or not raw_state:
                    discovery_message = "skipped (audit report did not include raw history/state)"
                    disc = None
                else:
                    try:
                        disc, discovery_message = discovery.discover_theory(report, raw_history, raw_state)
                    except Exception as exc:  # noqa: BLE001 - best-effort, never blocks the loop
                        disc, discovery_message = None, f"Discovery raised an exception: {exc!r}"
                if disc is not None:
                    reg_result = discovery.register_discovered_theory(disc, THEORIES_PATH, THEORY_DOCS_DIR)
                    discovery_message = reg_result.message
                    if reg_result.registered:
                        discovered_theory = disc.theory_name

                proposal = advisor.get_advice(report, self.engine_path)
                apply_result = None
                if proposal.action in ("parameter", "code_edit"):
                    apply_result = asdict(advisor.apply_proposal(proposal, self.engine_path))

                it_log = LocalIterationLog(
                    iteration=i,
                    ticks_requested=ticks_per_iteration,
                    audit_ok=True,
                    audit_error=None,
                    final_population=final_pop,
                    findings=run.get("findings", []),
                    theory_findings=run.get("theory_findings", []),
                    discovery_message=discovery_message,
                    discovered_theory=discovered_theory,
                    proposal=proposal.to_dict(),
                    apply_result=apply_result,
                )
                with self._lock:
                    self.status["iterations"].append(asdict(it_log))

                if proposal.action == "none" or not apply_result or not apply_result.get("applied"):
                    break
        except Exception as exc:  # noqa: BLE001 - surface any unexpected failure, don't just hang "running"
            with self._lock:
                self.status["error"] = repr(exc)
        finally:
            with self._lock:
                self.status["running"] = False
