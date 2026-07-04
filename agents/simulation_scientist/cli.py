from __future__ import annotations

import argparse
import os
from pathlib import Path

from .audit import run_audit


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="OCP Simulation Scientist Agent."
    )
    subparsers = parser.add_subparsers(dest="mode", required=False)

    audit_parser = subparsers.add_parser(
        "audit", help="One-shot in-process audit across N runs (default mode)."
    )
    audit_parser.add_argument("--runs", type=int, default=5, help="Number of simulation runs.")
    audit_parser.add_argument("--ticks", type=int, default=400, help="Ticks to execute per run.")
    audit_parser.add_argument(
        "--seed-base", type=int, default=1000,
        help="Base seed; each run uses seed_base + run_index.",
    )
    audit_parser.add_argument(
        "--format", choices=("json", "markdown"), default="markdown", help="Output format.",
    )
    audit_parser.add_argument(
        "--out", type=Path, help="Optional path to write the report. Defaults to stdout only.",
    )
    audit_parser.add_argument(
        "--include-raw-data", action="store_true",
        help="Include the full per-tick history and final state in JSON output (large payload; "
             "used by the in-process agent loop to feed further theory discovery, not needed "
             "for routine audit use).",
    )

    auto_parser = subparsers.add_parser(
        "autonomous",
        help="Deploy to a live sandbox, run, get LLM-proposed next experiment, apply it "
             "locally, repeat. Never commits or pushes — review the resulting diff yourself.",
    )
    auto_parser.add_argument("--ssh-key", default=os.environ.get("OCP_SSH_KEY", ""), required=not os.environ.get("OCP_SSH_KEY"))
    auto_parser.add_argument("--host", default=os.environ.get("OCP_HOST", ""), required=not os.environ.get("OCP_HOST"),
                              help="e.g. ubuntu@1.2.3.4")
    auto_parser.add_argument("--remote-root", default=os.environ.get("OCP_REMOTE_ROOT", "/home/ubuntu/ocp-simulation"))
    auto_parser.add_argument("--api-port", type=int, default=8420)
    auto_parser.add_argument("--engine-path", type=Path, default=Path("simulation/ocp/engine.py"))
    auto_parser.add_argument("--ai-path", type=Path, default=Path("simulation/ocp/ai.py"))
    auto_parser.add_argument("--max-iterations", type=int, default=5)
    auto_parser.add_argument("--ticks-per-iteration", type=int, default=400)
    auto_parser.add_argument("--poll-interval", type=float, default=3.0)
    auto_parser.add_argument("--experiment-timeout", type=float, default=600.0)
    auto_parser.add_argument("--seed-base", type=int, default=1000)
    auto_parser.add_argument("--stop-on-extinction", action="store_true")
    auto_parser.add_argument(
        "--no-theory-discovery", action="store_true",
        help="Disable autonomous theory-lens discovery for this run (still uses whatever "
             "lenses are already registered in theories.py).",
    )
    auto_parser.add_argument("--out", type=Path, help="Optional path to write the loop report markdown.")

    poll_parser = subparsers.add_parser(
        "poll",
        help="Poll a sandbox's agent-control config (set via its dashboard) and, when a run "
             "is due (manual 'run now' or a reached interval), drive the full loop against "
             "that sandbox: deploy, run, ask the LLM, apply, commit+push, redeploy, report.",
    )
    poll_parser.add_argument("--server-url", default=os.environ.get("OCP_SERVER_URL", "http://95.40.7.77/ocp"),
                              help="Base URL of the sandbox's dashboard/API, e.g. http://95.40.7.77/ocp")
    poll_parser.add_argument("--ssh-key", default=os.environ.get("OCP_SSH_KEY", ""), required=not os.environ.get("OCP_SSH_KEY"))
    poll_parser.add_argument("--host", default=os.environ.get("OCP_HOST", ""), required=not os.environ.get("OCP_HOST"),
                              help="e.g. ubuntu@1.2.3.4")
    poll_parser.add_argument("--remote-root", default=os.environ.get("OCP_REMOTE_ROOT", "/home/ubuntu/ocp-simulation"))
    poll_parser.add_argument("--api-port", type=int, default=8420)
    poll_parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    poll_parser.add_argument("--engine-path", type=Path, default=Path("simulation/ocp/engine.py"))
    poll_parser.add_argument("--ai-path", type=Path, default=Path("simulation/ocp/ai.py"))
    poll_parser.add_argument("--poll-interval", type=float, default=5.0)
    poll_parser.add_argument("--once", action="store_true",
                              help="Run a single check-and-maybe-run cycle then exit, instead of polling forever.")

    return parser


def _run_audit_mode(args: argparse.Namespace) -> int:
    report = run_audit(
        runs=args.runs, ticks_per_run=args.ticks, seed_base=args.seed_base,
        include_raw_data=getattr(args, "include_raw_data", False),
    )
    rendered = report.to_json() if args.format == "json" else report.to_markdown()
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered, encoding="utf-8")
    print(rendered)
    return 0


def _run_autonomous_mode(args: argparse.Namespace) -> int:
    # Local imports so `audit`-only usage never needs the remote/advisor dependencies.
    from .loop import run_autonomous_loop
    from .remote import DeployTarget

    target = DeployTarget(
        ssh_key=args.ssh_key,
        host=args.host,
        remote_root=args.remote_root,
        api_port=args.api_port,
    )
    report = run_autonomous_loop(
        target=target,
        engine_path=args.engine_path,
        ai_path=args.ai_path,
        max_iterations=args.max_iterations,
        ticks_per_iteration=args.ticks_per_iteration,
        poll_interval=args.poll_interval,
        experiment_timeout=args.experiment_timeout,
        seed_base=args.seed_base,
        stop_on_extinction=args.stop_on_extinction,
        enable_theory_discovery=not args.no_theory_discovery,
    )
    rendered = report.to_markdown()
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered, encoding="utf-8")
    print(rendered)
    print(
        "\nNo git operations were performed. Review `git diff` on the engine/ai files "
        "above and commit only what you want to keep."
    )
    return 0


def _run_poll_mode(args: argparse.Namespace) -> int:
    from .control_client import ControlClient
    from .orchestrator import run_forever, run_once
    from .remote import DeployTarget

    client = ControlClient(args.server_url)
    target = DeployTarget(
        ssh_key=args.ssh_key,
        host=args.host,
        remote_root=args.remote_root,
        api_port=args.api_port,
    )
    repo_root = args.repo_root
    engine_path = args.engine_path if args.engine_path.is_absolute() else repo_root / args.engine_path
    ai_path = args.ai_path if args.ai_path.is_absolute() else repo_root / args.ai_path

    if args.once:
        ran = run_once(client, target, repo_root, engine_path, ai_path)
        print(f"Run performed: {ran}")
        return 0

    run_forever(client, target, repo_root, engine_path, ai_path, poll_interval=args.poll_interval)
    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.mode == "poll":
        return _run_poll_mode(args)
    if args.mode == "autonomous":
        return _run_autonomous_mode(args)
    # Default to audit mode if no subcommand given, preserving the original CLI's behavior.
    if args.mode is None:
        args.runs, args.ticks, args.seed_base = 5, 400, 1000
        args.format, args.out, args.include_raw_data = "markdown", None, False
    return _run_audit_mode(args)


if __name__ == "__main__":
    raise SystemExit(main())
