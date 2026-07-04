"""Autonomous, unattended scheduling for the Simulation Scientist Agent.

Runs LocalAgentRunner on a timer with no human trigger. This is a distinct,
opt-in layer on top of local_loop.py's manual start/stop — the manual path
stays exactly as it was (a human clicks Start in the Agent tab); this module
is what makes the agent run entirely on its own when explicitly enabled.

After each scheduled run, if any iteration actually applied a change:
1. the changed files are synced into a separate git working copy
   (a real git clone, kept apart from the live flat-layout deployment) and
   pushed to origin/main — see _sync_and_push, and
2. this process exits, relying on the crash-resilient respawn wrapper
   (run_forever.sh) to bring the server back up running the freshly-applied
   code — Python doesn't hot-swap an already-imported module, so an actual
   process restart is the only reliable way to adopt the change.

If no git mirror is configured (e.g. in local development), git push is
silently skipped — the schedule and self-restart behavior still work.
"""

from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from . import github_app_auth
from .local_loop import LocalAgentRunner

GIT_MIRROR_ROOT = Path("/home/ubuntu/ocp-git-mirror")
GIT_REPO_SLUG = "open-civilization/open-civilization-protocol"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _iso_in(seconds: float) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat()


def _mirror_relpath(repo_root: Path, abs_path: Path) -> str:
    rel = abs_path.relative_to(repo_root).as_posix()
    if rel.startswith("ocp/") or rel.startswith("static/"):
        rel = "simulation/" + rel
    return rel


def _sync_and_push(repo_root: Path, engine_path: Path) -> dict[str, Any]:
    if not GIT_MIRROR_ROOT.exists():
        return {"pushed": False, "message": "No git mirror configured on this deployment — skipping push."}

    theories_path = repo_root / "agents" / "simulation_scientist" / "theories.py"
    theories_dir = repo_root / "agents" / "simulation_scientist" / "theories"

    candidates = [p for p in [engine_path, theories_path] if p.exists()]
    if theories_dir.exists():
        candidates.extend(theories_dir.glob("*.md"))

    copied = []
    for src in candidates:
        dst = GIT_MIRROR_ROOT / _mirror_relpath(repo_root, src)
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        copied.append(str(dst.relative_to(GIT_MIRROR_ROOT)))

    try:
        status = subprocess.run(
            ["git", "status", "--porcelain"], cwd=str(GIT_MIRROR_ROOT),
            capture_output=True, text=True, timeout=30,
        )
        if not status.stdout.strip():
            return {"pushed": False, "message": "No changes to push (files matched git mirror already)."}

        subprocess.run(["git", "add", "-A"], cwd=str(GIT_MIRROR_ROOT), timeout=30, check=True)
        commit = subprocess.run(
            ["git", "commit", "-m", "auto: Simulation Scientist Agent — autonomous rule adjustment"],
            cwd=str(GIT_MIRROR_ROOT), capture_output=True, text=True, timeout=30,
        )
        if commit.returncode != 0:
            return {"pushed": False, "message": f"git commit failed: {commit.stderr[-500:]}"}

        token, token_message = github_app_auth.get_installation_token()
        if not token:
            return {"pushed": False, "message": f"Committed locally but could not push — {token_message}"}

        push_url = f"https://x-access-token:{token}@github.com/{GIT_REPO_SLUG}.git"
        push = subprocess.run(
            ["git", "push", push_url, "main"], cwd=str(GIT_MIRROR_ROOT),
            capture_output=True, text=True, timeout=60,
        )
        if push.returncode != 0:
            # Never let a token leak into a log/status message via a stderr echo of the URL.
            sanitized = push.stderr.replace(token, "***").strip()[-500:]
            return {"pushed": False, "message": f"git push failed: {sanitized}"}
        return {"pushed": True, "message": f"Committed and pushed: {', '.join(copied)}"}
    except Exception as exc:  # noqa: BLE001 - never let a git hiccup crash the scheduler
        return {"pushed": False, "message": f"git operation raised: {exc!r}"}


@dataclass
class AutoRunLog:
    started_at: str
    finished_at: str
    applied_any_change: bool
    restarting: bool
    git_push: dict[str, Any]


class AutonomousScheduler:
    """Owns a background thread that periodically drives a LocalAgentRunner with
    no human trigger, only active once explicitly enabled via enable()."""

    def __init__(self, runner: LocalAgentRunner, repo_root: Path):
        self.runner = runner
        self.repo_root = repo_root
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self.status: dict[str, Any] = {
            "enabled": False,
            "interval_hours": 0,
            "max_iterations": 3,
            "ticks_per_iteration": 500,
            "next_run_at": None,
            "history": [],
        }

    def get_status(self) -> dict[str, Any]:
        with self._lock:
            return json.loads(json.dumps(self.status, default=str))

    def enable(self, interval_hours: float, max_iterations: int, ticks_per_iteration: int) -> tuple[bool, str]:
        with self._lock:
            if self.status["enabled"]:
                return False, "Autonomous scheduling is already enabled."
            self.status["enabled"] = True
            self.status["interval_hours"] = interval_hours
            self.status["max_iterations"] = max_iterations
            self.status["ticks_per_iteration"] = ticks_per_iteration
            self.status["next_run_at"] = _iso_in(interval_hours * 3600)
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return True, "Autonomous scheduling enabled."

    def disable(self) -> tuple[bool, str]:
        with self._lock:
            self.status["enabled"] = False
            self.status["next_run_at"] = None
        return True, "Autonomous scheduling disabled (a run already in progress will finish)."

    def _loop(self) -> None:
        while True:
            with self._lock:
                if not self.status["enabled"]:
                    return
                interval_hours = self.status["interval_hours"]
                max_iter = self.status["max_iterations"]
                ticks = self.status["ticks_per_iteration"]

            total_seconds = interval_hours * 3600
            slept = 0.0
            while slept < total_seconds:
                time.sleep(min(30, total_seconds - slept))
                slept += 30
                with self._lock:
                    if not self.status["enabled"]:
                        return

            self._run_once(max_iter, ticks)

    def _run_once(self, max_iterations: int, ticks_per_iteration: int) -> None:
        started = _now_iso()
        started_ok, _ = self.runner.start(max_iterations, ticks_per_iteration)
        if not started_ok:
            return  # a manual run is already in progress -- skip this tick, try again next interval

        while self.runner.get_status()["running"]:
            time.sleep(2)

        final_status = self.runner.get_status()
        applied_any = any(
            (it.get("apply_result") or {}).get("applied") for it in final_status.get("iterations", [])
        )

        push_result: dict[str, Any] = {"pushed": False, "message": "No change applied this run."}
        if applied_any:
            push_result = _sync_and_push(self.repo_root, self.runner.engine_path)

        log = AutoRunLog(
            started_at=started, finished_at=_now_iso(),
            applied_any_change=applied_any, restarting=applied_any,
            git_push=push_result,
        )
        with self._lock:
            self.status["history"].append(asdict(log))
            self.status["history"] = self.status["history"][-20:]
            if self.status["enabled"]:
                self.status["next_run_at"] = _iso_in(self.status["interval_hours"] * 3600)

        if applied_any:
            # Let the status write (and any in-flight HTTP response) flush, then hand off
            # to the crash-resilient respawn wrapper to bring the server back up running
            # the freshly-applied code.
            threading.Timer(2.0, lambda: os._exit(0)).start()
