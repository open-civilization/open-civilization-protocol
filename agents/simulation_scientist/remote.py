"""Remote sandbox control for the Simulation Scientist Agent.

Wraps the exact SSH/scp/curl workflow used to deploy and observe the OCP
simulation on a real running server: copy source files over, restart the
process, poll the HTTP API for state, and accumulate metrics/events across
polls (the server only ever returns a bounded recent window).
"""

from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class DeployTarget:
    """Connection details for a remote sandbox. Defaults match this project's
    working test deployment; override via CLI flags or environment for others."""

    ssh_key: str
    host: str  # e.g. "ubuntu@95.40.7.77"
    remote_root: str  # e.g. "/home/ubuntu/ocp-simulation"
    api_port: int = 8420
    run_cmd: str = "python3 run.py"
    log_file: str = "ocp.log"

    def ssh(self, remote_cmd: str, timeout: int = 30) -> subprocess.CompletedProcess:
        cmd = ["ssh", "-i", self.ssh_key, "-o", "StrictHostKeyChecking=no", self.host, remote_cmd]
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

    def scp(self, local_path: str, remote_path: str, timeout: int = 30) -> subprocess.CompletedProcess:
        cmd = ["scp", "-i", self.ssh_key, "-o", "StrictHostKeyChecking=no", local_path, f"{self.host}:{remote_path}"]
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


@dataclass
class DeployResult:
    started: bool
    startup_errors: Optional[str] = None
    stderr: str = ""


def deploy_files(target: DeployTarget, files: dict[str, str]) -> None:
    """files: {local_path: remote_relative_path (relative to remote_root)}"""
    for local_path, remote_rel in files.items():
        result = target.scp(local_path, f"{target.remote_root}/{remote_rel}")
        if result.returncode != 0:
            raise RuntimeError(f"scp failed for {local_path} -> {remote_rel}: {result.stderr}")


def restart_server(target: DeployTarget, settle_seconds: float = 6.0, respawn_timeout: float = 20.0) -> DeployResult:
    """Kill the running instance and wait for the sandbox's own crash-resilient
    supervisor (run_forever.sh: `while true; do python3 run.py; sleep 2; done`)
    to bring a fresh one back up.

    This deliberately does NOT launch a replacement process itself — an earlier
    version did (`setsid nohup ... &`), which raced the supervisor's own
    respawn: both could end up trying to bind the API port at nearly the same
    time. Since every deployment now runs under that supervisor, killing the
    old process and waiting for a new pid to appear is the only step needed.
    """
    before = target.ssh(f"pgrep -f \"{target.run_cmd}\"", timeout=10)
    before_pids = set(before.stdout.split())

    target.ssh(f"pkill -9 -f \"{target.run_cmd}\"", timeout=15)

    deadline = time.time() + respawn_timeout
    started = False
    while time.time() < deadline:
        time.sleep(1.0)
        check = target.ssh(f"pgrep -f \"{target.run_cmd}\"", timeout=10)
        after_pids = set(check.stdout.split())
        if after_pids and after_pids != before_pids:
            started = True
            break
    time.sleep(settle_seconds)

    errors = None
    if started:
        err_check = target.ssh(
            f"grep -i 'error\\|traceback' {target.remote_root}/{target.log_file} | tail -30",
            timeout=15,
        )
        errors = err_check.stdout.strip() or None
        if errors:
            started = False  # a process can be running but have crashed on the first tick

    return DeployResult(started=started, startup_errors=errors)


def api_get(target: DeployTarget, path: str, timeout: int = 20) -> dict[str, Any]:
    result = target.ssh(f"curl -s http://localhost:{target.api_port}{path}", timeout=timeout)
    text = result.stdout.strip()
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"raw": text}


def api_post(target: DeployTarget, path: str, timeout: int = 20) -> dict[str, Any]:
    result = target.ssh(f"curl -s -X POST http://localhost:{target.api_port}{path}", timeout=timeout)
    text = result.stdout.strip()
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"raw": text}


def start_simulation(target: DeployTarget) -> dict[str, Any]:
    return api_post(target, "/api/start")


def set_speed(target: DeployTarget, speed: int) -> dict[str, Any]:
    return api_post(target, f"/api/speed/{speed}")


def fetch_state(target: DeployTarget) -> dict[str, Any]:
    return api_get(target, "/api/state")


@dataclass
class ExperimentResult:
    start_tick: int
    end_tick: int
    history: list[dict[str, Any]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    final_state: dict[str, Any] = field(default_factory=dict)
    timed_out: bool = False
    went_extinct: bool = False


def run_sandbox_experiment(
    target: DeployTarget,
    ticks: int,
    poll_interval: float = 3.0,
    timeout: float = 600.0,
    speed: Optional[int] = 30,
) -> ExperimentResult:
    """Run the currently-deployed code for roughly `ticks` simulation ticks, polling
    the live HTTP API and accumulating metrics/events across polls (the server itself
    only ever exposes a bounded recent window, so single-poll snapshots would silently
    drop most of a long run)."""
    if speed is not None:
        set_speed(target, speed)
    start_simulation(target)

    state = fetch_state(target)
    start_tick = int((state.get("metrics") or {}).get("tick", 0) or 0)
    target_tick = start_tick + ticks
    deadline = time.time() + timeout

    history_by_tick: dict[int, dict[str, Any]] = {}
    events_seen: dict[tuple, dict[str, Any]] = {}

    def _absorb(s: dict[str, Any]) -> None:
        for row in s.get("history", []) or []:
            t = row.get("tick")
            if t is not None:
                history_by_tick[int(t)] = row
        for evt in s.get("events", []) or []:
            key = (evt.get("tick"), evt.get("type"), evt.get("text"), evt.get("x"), evt.get("y"))
            events_seen[key] = evt

    _absorb(state)
    last_state = state
    timed_out = False
    while True:
        cur_tick = int((last_state.get("metrics") or {}).get("tick", 0) or 0)
        pop = int((last_state.get("metrics") or {}).get("pop", 0) or 0)
        if cur_tick >= target_tick or pop == 0:
            break
        if time.time() > deadline:
            timed_out = True
            break
        time.sleep(poll_interval)
        last_state = fetch_state(target)
        _absorb(last_state)

    full_history = [history_by_tick[t] for t in sorted(history_by_tick)]
    full_events = [events_seen[k] for k in sorted(events_seen, key=lambda k: (k[0] or 0))]
    final_pop = int((last_state.get("metrics") or {}).get("pop", 0) or 0)

    return ExperimentResult(
        start_tick=start_tick,
        end_tick=int((last_state.get("metrics") or {}).get("tick", start_tick) or start_tick),
        history=full_history,
        events=full_events,
        final_state=last_state,
        timed_out=timed_out,
        went_extinct=(final_pop == 0),
    )
