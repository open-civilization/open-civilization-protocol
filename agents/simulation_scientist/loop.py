"""Autonomous research loop for the Simulation Scientist Agent.

Each iteration: deploy the current local engine.py/ai.py to a real running
sandbox, run it for N ticks, analyze the outcome against the same Finding
heuristics used by the one-shot audit plus every registered theory lens,
attempt to DISCOVER a new theory lens for whatever those don't already
explain (growing the agent's own theoretical toolkit rather than being
bounded by a fixed list chosen in advance), ask an LLM advisor for one
concrete next experiment, and apply that experiment (a parameter tweak or a
small code edit) to the LOCAL source tree for the next iteration to test.

This agent never commits or pushes anything — every change it makes lands
as a plain uncommitted working-tree diff, exactly like an interactive Edit,
so a human reviews and decides what to keep before any git operation.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

from . import advisor, discovery
from .audit import analyze_live_experiment, build_report_from_live_runs
from .remote import DeployTarget, deploy_files, restart_server, run_sandbox_experiment

THEORIES_PATH = Path(__file__).resolve().parent / "theories.py"
THEORY_DOCS_DIR = Path(__file__).resolve().parent / "theories"


@dataclass
class IterationLog:
    iteration: int
    ticks_requested: int
    deploy_ok: bool
    deploy_error: Optional[str]
    went_extinct: bool
    end_tick: int
    findings: list[dict[str, Any]]
    theory_findings: list[dict[str, Any]]
    discovery_message: str
    discovered_theory: Optional[str]
    proposal: dict[str, Any]
    apply_result: Optional[dict[str, Any]]


@dataclass
class LoopReport:
    iterations: list[IterationLog] = field(default_factory=list)

    def to_markdown(self) -> str:
        lines = ["# Simulation Scientist Autonomous Loop Report", ""]
        for it in self.iterations:
            lines.append(f"## Iteration {it.iteration}")
            lines.append("")
            lines.append(f"- deploy_ok: {it.deploy_ok}" + (f" (error: {it.deploy_error})" if it.deploy_error else ""))
            lines.append(f"- went_extinct: {it.went_extinct}")
            lines.append(f"- end_tick: {it.end_tick}")
            if it.findings:
                lines.append("- findings:")
                for f in it.findings:
                    lines.append(f"  - [{f.get('severity')}] {f.get('title')}: {f.get('summary')}")
            else:
                lines.append("- findings: none")
            if it.theory_findings:
                lines.append("- theory-lens findings:")
                for tf in it.theory_findings:
                    lines.append(f"  - [{tf.get('severity')}] {tf.get('theory')} ({tf.get('citation')}): {tf.get('gap')}")
            lines.append(f"- theory discovery: {it.discovery_message}"
                         + (f" -> registered '{it.discovered_theory}'" if it.discovered_theory else ""))
            lines.append(f"- hypothesis: {it.proposal.get('hypothesis', '')}")
            lines.append(f"- action: {it.proposal.get('action', 'none')} — {it.proposal.get('rationale', '')}")
            if it.apply_result:
                lines.append(f"- applied: {it.apply_result.get('applied')} — {it.apply_result.get('message')}")
            lines.append("")
        return "\n".join(lines)


def run_autonomous_loop(
    target: DeployTarget,
    engine_path: Path,
    ai_path: Optional[Path],
    max_iterations: int = 5,
    ticks_per_iteration: int = 400,
    poll_interval: float = 3.0,
    experiment_timeout: float = 600.0,
    seed_base: int = 1000,
    stop_on_extinction: bool = False,
    enable_theory_discovery: bool = True,
) -> LoopReport:
    report = LoopReport()

    for i in range(1, max_iterations + 1):
        # 1. Deploy current local source to the sandbox
        files = {str(engine_path): "ocp/engine.py"}
        if ai_path is not None:
            files[str(ai_path)] = "ocp/ai.py"

        deploy_error = None
        deploy_ok = True
        try:
            deploy_files(target, files)
            result = restart_server(target)
            deploy_ok = result.started
            deploy_error = result.startup_errors
        except Exception as exc:  # noqa: BLE001 - surface any deploy failure as a finding
            deploy_ok = False
            deploy_error = str(exc)

        if not deploy_ok:
            it_log = IterationLog(
                iteration=i, ticks_requested=ticks_per_iteration,
                deploy_ok=False, deploy_error=deploy_error,
                went_extinct=False, end_tick=0, findings=[], theory_findings=[],
                discovery_message="skipped (deploy failed)", discovered_theory=None,
                proposal={"hypothesis": "", "action": "none",
                          "rationale": f"Deploy failed, cannot run experiment: {deploy_error}"},
                apply_result=None,
            )
            report.iterations.append(it_log)
            break  # a broken deploy means the last code edit was bad — stop and let a human look

        # 2. Run the experiment against the live sandbox
        experiment = run_sandbox_experiment(
            target, ticks=ticks_per_iteration, poll_interval=poll_interval,
            timeout=experiment_timeout,
        )

        # 3. Analyze against the existing Finding heuristics AND every registered theory lens
        run_summary = analyze_live_experiment(
            run_id=i, seed=seed_base + i, ticks_requested=ticks_per_iteration,
            history=experiment.history, events=experiment.events, state=experiment.final_state,
        )
        audit_report = build_report_from_live_runs([run_summary], ticks_per_iteration, seed_base)
        report_dict = audit_report.to_dict()

        # 4. Try to discover a NEW theory lens for whatever isn't already explained —
        # this is what lets the agent's theoretical toolkit grow on its own rather than
        # being bounded by whichever lenses happen to already be registered.
        discovery_message = "disabled"
        discovered_theory = None
        if enable_theory_discovery:
            try:
                disc, discovery_message = discovery.discover_theory(
                    report_dict, experiment.history, experiment.final_state,
                )
            except Exception as exc:  # noqa: BLE001 - discovery is best-effort, never blocks the loop
                disc, discovery_message = None, f"Discovery raised an exception: {exc!r}"
            if disc is not None:
                reg_result = discovery.register_discovered_theory(disc, THEORIES_PATH, THEORY_DOCS_DIR)
                discovery_message = reg_result.message
                if reg_result.registered:
                    discovered_theory = disc.theory_name

        # 5. Ask the LLM advisor for exactly one next experiment
        proposal = advisor.get_advice(report_dict, engine_path)

        # 6. Apply it locally (no git operations — plain working-tree edit)
        apply_result = None
        if proposal.action in ("parameter", "code_edit"):
            apply_result = asdict(advisor.apply_proposal(proposal, engine_path))

        it_log = IterationLog(
            iteration=i,
            ticks_requested=ticks_per_iteration,
            deploy_ok=True,
            deploy_error=None,
            went_extinct=experiment.went_extinct,
            end_tick=experiment.end_tick,
            findings=[asdict(f) for f in run_summary.findings],
            theory_findings=run_summary.theory_findings,
            discovery_message=discovery_message,
            discovered_theory=discovered_theory,
            proposal=proposal.to_dict(),
            apply_result=apply_result,
        )
        report.iterations.append(it_log)

        if experiment.went_extinct and stop_on_extinction:
            break
        if proposal.action == "none" or not apply_result or not apply_result.get("applied"):
            # Nothing further to try, or the proposal couldn't be applied — stop rather
            # than silently looping on the same unchanged code.
            break

    return report
