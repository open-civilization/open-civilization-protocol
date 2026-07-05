"""Poll loop that drives the Simulation Scientist Agent from this machine.

The sandbox (simulation/ocp/server.py + agent_control.py) only holds a small
config/trigger the dashboard can edit — it never executes anything itself and
never calls out to this machine. This module polls that config on an interval
and, when a run is due, does all the actual work: deploy test code to the
sandbox, run experiments, ask the LLM, apply accepted edits to the local repo,
push them to GitHub, and do one final deploy so the sandbox ends up actually
running the accepted code (mid-loop deploys only ever test the *previous*
iteration's edit, never the last one accepted).
"""

from __future__ import annotations

import subprocess
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .control_client import ControlClient
from .loop import run_autonomous_loop
from .remote import DeployTarget, deploy_files, restart_server


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _git(repo_root: Path, *args: str, timeout: float = 60.0) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(repo_root), capture_output=True, text=True, timeout=timeout)


def _commit_and_push(repo_root: Path, engine_path: Path, ai_path: Optional[Path]) -> dict[str, Any]:
    theories_path = repo_root / "agents" / "simulation_scientist" / "theories.py"
    theories_dir = repo_root / "agents" / "simulation_scientist" / "theories"

    paths = [p for p in [engine_path, ai_path, theories_path] if p and p.exists()]
    if theories_dir.exists():
        paths.extend(theories_dir.glob("*.md"))
    rel_paths = [str(p.relative_to(repo_root)) for p in paths]
    if not rel_paths:
        return {"pushed": False, "message": "Nothing to push."}

    status = _git(repo_root, "status", "--porcelain", "--", *rel_paths)
    if not status.stdout.strip():
        return {"pushed": False, "message": "No changes to push (working tree already matches)."}

    add = _git(repo_root, "add", "--", *rel_paths)
    if add.returncode != 0:
        return {"pushed": False, "message": f"git add failed: {add.stderr[-500:]}"}

    commit = _git(repo_root, "commit", "-m", "auto: Simulation Scientist Agent — autonomous rule adjustment")
    if commit.returncode != 0:
        return {"pushed": False, "message": f"git commit failed: {commit.stderr[-500:]}"}

    push = _git(repo_root, "push", "origin", "main", timeout=60.0)
    if push.returncode != 0:
        return {"pushed": False, "message": f"git push failed: {push.stderr[-500:]}"}
    return {"pushed": True, "message": f"Committed and pushed: {', '.join(rel_paths)}"}


def _is_due(control: dict[str, Any]) -> bool:
    if control.get("status") == "running":
        return False
    if control.get("run_requested"):
        return True
    if control.get("mode") == "interval" and control.get("next_run_at"):
        return datetime.now(timezone.utc) >= datetime.fromisoformat(control["next_run_at"])
    return False


def _pull_latest(repo_root: Path) -> dict[str, Any]:
    """Fast-forward only — this machine may not be the only one pushing to main
    (another operator's poller, or a human, can land commits between our
    cycles). A plain, unconditional push after editing a stale checkout would
    silently overwrite whatever they landed; refusing to proceed on a failed
    fast-forward is safer than guessing how to reconcile."""
    fetch = _git(repo_root, "fetch", "origin", "main")
    if fetch.returncode != 0:
        return {"ok": False, "message": f"git fetch failed: {fetch.stderr[-500:]}"}
    pull = _git(repo_root, "merge", "--ff-only", "origin/main")
    if pull.returncode != 0:
        return {"ok": False, "message": f"git merge --ff-only failed: {pull.stderr[-500:]}"}
    return {"ok": True, "message": "Up to date with origin/main."}


def run_once(
    client: ControlClient,
    target: DeployTarget,
    repo_root: Path,
    engine_path: Path,
    ai_path: Optional[Path],
) -> bool:
    """Checks whether a run is due; if so, runs it end to end. Returns True if
    a run was actually performed."""
    control = client.get_control()
    if not _is_due(control):
        return False

    claimed, state = client.claim_run()
    if not claimed:
        return False

    started_at = _now_iso()

    sync = _pull_latest(repo_root)
    if not sync["ok"]:
        client.report_run({
            "started_at": started_at,
            "finished_at": _now_iso(),
            "iterations": 0,
            "applied_any_change": False,
            "summary": f"Aborted before running: could not sync with origin/main — {sync['message']}",
            "push": {"pushed": False, "message": "Skipped — sync failed."},
            "deploy": {"deployed": False, "message": "Skipped — sync failed."},
        })
        return True

    agent_settings = client.get_settings()

    report = run_autonomous_loop(
        target=target,
        engine_path=engine_path,
        ai_path=ai_path,
        max_iterations=int(state.get("max_iterations", 3)),
        ticks_per_iteration=int(state.get("ticks_per_iteration", 500)),
        agent_settings=agent_settings,
        should_stop=client.is_stop_requested,
        research_note=state.get("research_note") or None,
    )

    applied_any = any((it.apply_result or {}).get("applied") for it in report.iterations)

    push_result: dict[str, Any] = {"pushed": False, "message": "No change applied this run."}
    deploy_result: dict[str, Any] = {"deployed": False, "message": "No change applied this run."}
    if applied_any:
        push_result = _commit_and_push(repo_root, engine_path, ai_path)
        if not push_result["pushed"]:
            # Don't publish code to the sandbox that isn't actually reflected in git —
            # that defeats the point of git being the source of truth, and a failed
            # push here usually means another operator landed a conflicting commit
            # since our pull above (a real, if narrow, race).
            deploy_result = {"deployed": False, "message": f"Skipped — push failed: {push_result['message']}"}
        else:
            files = {str(engine_path): "ocp/engine.py"}
            if ai_path is not None and ai_path.exists():
                files[str(ai_path)] = "ocp/ai.py"
            try:
                deploy_files(target, files)
                restart_result = restart_server(target)
                deploy_result = {
                    "deployed": restart_result.started,
                    "message": restart_result.startup_errors or "Deployed and restarted successfully.",
                }
            except Exception as exc:  # noqa: BLE001 - surface, never crash the poller over a deploy hiccup
                deploy_result = {"deployed": False, "message": f"Final deploy failed: {exc!r}"}

    client.report_run({
        "started_at": started_at,
        "finished_at": _now_iso(),
        "iterations": len(report.iterations),
        "applied_any_change": applied_any,
        "summary": report.to_markdown(),
        "push": push_result,
        "deploy": deploy_result,
    })
    return True


def run_forever(
    client: ControlClient,
    target: DeployTarget,
    repo_root: Path,
    engine_path: Path,
    ai_path: Optional[Path],
    poll_interval: float = 5.0,
) -> None:
    print(f"[poller] watching {client.base} every {poll_interval}s ...", flush=True)
    while True:
        try:
            if run_once(client, target, repo_root, engine_path, ai_path):
                print(f"[poller] {_now_iso()} run completed", flush=True)
        except Exception:  # noqa: BLE001 - a bad cycle should log and retry, not kill the poller
            print(f"[poller] {_now_iso()} cycle raised an exception:", flush=True)
            traceback.print_exc()
        time.sleep(poll_interval)
