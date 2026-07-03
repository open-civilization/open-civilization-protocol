from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from statistics import mean
from typing import Any

try:
    from simulation.ocp.engine import (
        CALORIE_DEATH_ZONE, CALORIE_EROSION_THRESHOLD, MAX_ENERGY,
        SEASON_LENGTH, SEASONS, Simulation,
    )
except ModuleNotFoundError:
    from ocp.engine import (
        CALORIE_DEATH_ZONE, CALORIE_EROSION_THRESHOLD, MAX_ENERGY,
        SEASON_LENGTH, SEASONS, Simulation,
    )


DEATH_CAUSE_PATTERN = re.compile(r"\(([^,]+), age ")


@dataclass
class Finding:
    id: str
    severity: str
    title: str
    summary: str
    evidence: dict[str, Any] = field(default_factory=dict)
    theory_tags: list[str] = field(default_factory=list)
    suggested_domains: list[str] = field(default_factory=list)


@dataclass
class RunSummary:
    run_id: int
    seed: int
    ticks_requested: int
    ticks_executed: int
    final_population: int
    peak_population: int
    first_language_tick: int | None
    first_writing_tick: int | None
    final_metrics: dict[str, Any]
    death_causes: dict[str, int]
    seasonal_deaths: dict[str, int]
    knowledge_holders: dict[str, int]
    findings: list[Finding] = field(default_factory=list)


@dataclass
class AuditReport:
    config: dict[str, Any]
    aggregate: dict[str, Any]
    runs: list[RunSummary]

    def to_dict(self) -> dict[str, Any]:
        return {
            "config": self.config,
            "aggregate": self.aggregate,
            "runs": [
                {
                    **asdict(run),
                    "findings": [asdict(finding) for finding in run.findings],
                }
                for run in self.runs
            ],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    def to_markdown(self) -> str:
        lines = [
            "# Simulation Scientist Audit Report",
            "",
            "## Config",
            "",
            f"- runs: {self.config['runs']}",
            f"- ticks_per_run: {self.config['ticks_per_run']}",
            f"- seed_base: {self.config['seed_base']}",
            "",
            "## Aggregate",
            "",
            f"- extinction_rate: {self.aggregate['extinction_rate']:.2%}",
            f"- avg_final_population: {self.aggregate['avg_final_population']:.2f}",
            f"- avg_peak_population: {self.aggregate['avg_peak_population']:.2f}",
            f"- recurring_findings: {len(self.aggregate['recurring_findings'])}",
            "",
        ]

        if self.aggregate["recurring_findings"]:
            lines.extend(["## Recurring Findings", ""])
            for finding in self.aggregate["recurring_findings"]:
                lines.append(
                    f"- `{finding['id']}`: {finding['title']} "
                    f"(severity `{finding['severity']}`, seen in {finding['count']} runs)"
                )
            lines.append("")

        lines.extend(["## Runs", ""])
        for run in self.runs:
            lines.extend(
                [
                    f"### Run {run.run_id} (seed {run.seed})",
                    "",
                    f"- ticks_executed: {run.ticks_executed}",
                    f"- final_population: {run.final_population}",
                    f"- peak_population: {run.peak_population}",
                    f"- first_language_tick: {run.first_language_tick}",
                    f"- first_writing_tick: {run.first_writing_tick}",
                    f"- death_causes: {run.death_causes}",
                    "",
                ]
            )
            if run.findings:
                lines.append("Findings:")
                for finding in run.findings:
                    lines.append(
                        f"- [{finding.severity}] {finding.title}: {finding.summary}"
                    )
                lines.append("")
            else:
                lines.extend(["Findings:", "- none", ""])
        return "\n".join(lines)


def _season_for_tick(tick: int) -> str:
    return SEASONS[(tick // SEASON_LENGTH) % 4]


def _extract_death_cause(event_text: str) -> str | None:
    match = DEATH_CAUSE_PATTERN.search(event_text)
    if not match:
        return None
    return match.group(1)


def _find_first_tick(history: list[dict[str, Any]], metric_name: str) -> int | None:
    for row in history:
        if row.get(metric_name, 0) > 0:
            return int(row["tick"])
    return None


def _knowledge_holders_from_state(state: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for resident in state.get("residents", []):
        for knowledge_name in resident.get("knowledge", {}):
            counts[knowledge_name] = counts.get(knowledge_name, 0) + 1
    return dict(sorted(counts.items()))


def _death_stats(events: list[dict[str, Any]]) -> tuple[dict[str, int], dict[str, int]]:
    causes: dict[str, int] = {}
    seasonal: dict[str, int] = {season: 0 for season in SEASONS}
    for event in events:
        if event.get("type") != "death":
            continue
        seasonal[_season_for_tick(int(event["tick"]))] += 1
        cause = _extract_death_cause(event.get("text", ""))
        if cause:
            causes[cause] = causes.get(cause, 0) + 1
    return dict(sorted(causes.items())), seasonal


def _analyze_run(
    run_id: int,
    seed: int,
    ticks_requested: int,
    history: list[dict[str, Any]],
    state: dict[str, Any],
    death_causes: dict[str, int],
    seasonal_deaths: dict[str, int],
) -> RunSummary:
    final_metrics = history[-1] if history else {}
    final_population = int(final_metrics.get("pop", 0))
    peak_population = max((int(row.get("pop", 0)) for row in history), default=0)
    first_language_tick = _find_first_tick(history, "language_holders")
    first_writing_tick = _find_first_tick(history, "writing_holders")
    knowledge_holders = _knowledge_holders_from_state(state)

    findings: list[Finding] = []

    if final_population == 0:
        findings.append(
            Finding(
                id="extinction",
                severity="critical",
                title="Population collapsed to extinction",
                summary="The lineage terminated completely before the audit horizon.",
                evidence={
                    "ticks_executed": len(history),
                    "peak_population": peak_population,
                    "death_causes": death_causes,
                },
                theory_tags=["population_dynamics", "carrying_capacity", "survival"],
                suggested_domains=["malthus", "disease", "winter_survival"],
            )
        )

    if peak_population > 0 and final_population > 0 and final_population <= peak_population * 0.25:
        findings.append(
            Finding(
                id="severe_population_crash",
                severity="high",
                title="Severe population crash",
                summary="Population survived, but ended at less than a quarter of its observed peak.",
                evidence={
                    "final_population": final_population,
                    "peak_population": peak_population,
                },
                theory_tags=["malthusian_trap", "resource_pressure"],
                suggested_domains=["carrying_capacity", "seasonality", "migration"],
            )
        )

    total_deaths = sum(seasonal_deaths.values())
    winter_deaths = seasonal_deaths.get("winter", 0)
    starvation_deaths = death_causes.get("starvation", 0)
    if total_deaths >= 10 and winter_deaths / max(1, total_deaths) >= 0.55:
        findings.append(
            Finding(
                id="winter_bottleneck",
                severity="medium" if final_population > 0 else "high",
                title="Winter bottleneck dominates mortality",
                summary="More than half of all recorded deaths happened in winter.",
                evidence={
                    "winter_deaths": winter_deaths,
                    "total_deaths": total_deaths,
                    "starvation_deaths": starvation_deaths,
                },
                theory_tags=["seasonality", "malthusian_pressure"],
                suggested_domains=["food_storage", "shelter", "clothing", "migration"],
            )
        )

    if history:
        tail = history[-min(50, len(history)) :]
        avg_pressure = mean(float(row.get("pressure", 0.0)) for row in tail)
        # avg_energy is in kcal (0-MAX_ENERGY); CALORIE_EROSION_THRESHOLD is where health
        # begins to erode, so a tail average anywhere near or below it is a real red flag,
        # not just "somewhat hungry."
        avg_energy = mean(float(row.get("avg_energy", 0.0)) for row in tail)
        if avg_pressure >= 1.05 and avg_energy <= CALORIE_EROSION_THRESHOLD * 0.9:
            findings.append(
                Finding(
                    id="chronic_pressure",
                    severity="high",
                    title="Chronic carrying-capacity pressure",
                    summary="Late-run population pressure remained above carrying capacity while caloric reserves stayed near or below the erosion threshold.",
                    evidence={
                        "avg_tail_pressure": round(avg_pressure, 3),
                        "avg_tail_energy_kcal": round(avg_energy, 1),
                        "erosion_threshold_kcal": CALORIE_EROSION_THRESHOLD,
                    },
                    theory_tags=["carrying_capacity", "malthusian_trap"],
                    suggested_domains=["resource_regrowth", "migration", "storage", "fertility"],
                )
            )

        # Population routinely running below the death-zone threshold is a much sharper
        # signal than generic pressure — it means the caloric economy itself is starving
        # the population, not just crowding effects.
        if avg_energy <= CALORIE_DEATH_ZONE:
            findings.append(
                Finding(
                    id="caloric_death_zone_baseline",
                    severity="critical",
                    title="Population operating inside the caloric death zone by default",
                    summary="Average energy over the tail window sat at or below the death-zone threshold — this should represent acute crisis, not routine operation.",
                    evidence={
                        "avg_tail_energy_kcal": round(avg_energy, 1),
                        "death_zone_kcal": CALORIE_DEATH_ZONE,
                        "max_energy_kcal": MAX_ENERGY,
                    },
                    theory_tags=["caloric_model", "forage_economy"],
                    suggested_domains=["forage_conversion_rate", "upkeep_calibration"],
                )
            )

    final_metrics_tail = history[-1] if history else {}
    fire_holders = int(final_metrics_tail.get("fire_holders", 0))
    shelter_holders = int(final_metrics_tail.get("shelter_holders", 0))
    clothing_holders = int(final_metrics_tail.get("clothing_holders", 0))
    if final_population > 5 and max(fire_holders, shelter_holders, clothing_holders) == 0:
        findings.append(
            Finding(
                id="no_cold_technology_emerged",
                severity="medium",
                title="No cold-mitigation technology emerged despite a surviving population",
                summary="Shelter, clothing, and fire all stayed at zero adopters — either the population never faced real caloric crisis, or discovery odds are too conservative.",
                evidence={
                    "fire_holders": fire_holders,
                    "shelter_holders": shelter_holders,
                    "clothing_holders": clothing_holders,
                    "final_population": final_population,
                },
                theory_tags=["technology_emergence", "caloric_crisis"],
                suggested_domains=["shelter_discovery_chance", "clothing_discovery_chance", "fire_discovery_chance"],
            )
        )

    avg_immunity = float(final_metrics_tail.get("avg_immunity", 0.5))
    if avg_immunity <= 0.35:
        findings.append(
            Finding(
                id="low_population_immunity",
                severity="low",
                title="Population-average immunity trended low",
                summary="Average immunity stayed well below the initial midpoint (0.5), suggesting epidemics aren't selecting for resistance as expected, or the population never faced one.",
                evidence={"avg_immunity": round(avg_immunity, 3)},
                theory_tags=["epidemic", "genetic_selection"],
                suggested_domains=["epidemic_density_threshold", "epidemic_ignition_chance"],
            )
        )

    cultivated_cells = int(final_metrics_tail.get("cultivated_cells", 0))
    farmer_holders = int(final_metrics_tail.get("farmer_holders", 0))
    if farmer_holders > 10 and cultivated_cells == 0:
        findings.append(
            Finding(
                id="farming_knowledge_without_cultivated_land",
                severity="medium",
                title="Farmers exist but no land shows cultivation",
                summary="A meaningful number of residents know crop_cultivation, but no cell has accumulated visible cultivation — the land-improvement mechanic may be too fragile relative to nomadic movement patterns.",
                evidence={"farmer_holders": farmer_holders, "cultivated_cells": cultivated_cells},
                theory_tags=["domestication", "cultivation_accumulation"],
                suggested_domains=["cultivation_gain_rate", "cultivation_decay"],
            )
        )

    if first_language_tick is not None and first_writing_tick is not None:
        writing_lag = first_writing_tick - first_language_tick
        if writing_lag < SEASON_LENGTH:
            findings.append(
                Finding(
                    id="rapid_writing_emergence",
                    severity="medium",
                    title="Writing emerged very quickly after language",
                    summary="Symbolic record appeared within less than one season after the first language signal.",
                    evidence={
                        "first_language_tick": first_language_tick,
                        "first_writing_tick": first_writing_tick,
                        "writing_lag_ticks": writing_lag,
                    },
                    theory_tags=["information_theory", "knowledge_externalization"],
                    suggested_domains=["language_modeling", "writing_artifacts", "knowledge_system"],
                )
            )

    final_writing_holders = int(final_metrics.get("writing_holders", 0))
    final_language_holders = int(final_metrics.get("language_holders", 0))
    if final_writing_holders > 0 and final_writing_holders >= max(3, final_language_holders):
        findings.append(
            Finding(
                id="writing_outpaces_language",
                severity="medium",
                title="Writing adoption is keeping pace with or exceeding language adoption",
                summary="This may indicate that writing is acting as a generic transmission buff rather than a constrained external-memory system.",
                evidence={
                    "writing_holders": final_writing_holders,
                    "language_holders": final_language_holders,
                },
                theory_tags=["information_theory", "external_memory"],
                suggested_domains=["knowledge_channels", "artifact_modeling", "script_emergence"],
            )
        )

    return RunSummary(
        run_id=run_id,
        seed=seed,
        ticks_requested=ticks_requested,
        ticks_executed=len(history),
        final_population=final_population,
        peak_population=peak_population,
        first_language_tick=first_language_tick,
        first_writing_tick=first_writing_tick,
        final_metrics=final_metrics,
        death_causes=death_causes,
        seasonal_deaths=seasonal_deaths,
        knowledge_holders=knowledge_holders,
        findings=findings,
    )


def _simulate_run(run_id: int, seed: int, ticks: int) -> RunSummary:
    sim = Simulation(seed=seed)
    for _ in range(ticks):
        living = sum(1 for resident in sim.residents if resident.alive)
        if living == 0:
            break
        sim.tick()

    state = sim.get_state()
    history = list(sim.metrics_history)
    death_causes, seasonal_deaths = _death_stats(sim.all_events)
    return _analyze_run(run_id, seed, ticks, history, state, death_causes, seasonal_deaths)


def _aggregate_runs(runs: list[RunSummary]) -> dict[str, Any]:
    extinction_count = sum(1 for run in runs if run.final_population == 0)
    finding_counts: dict[str, dict[str, Any]] = {}
    for run in runs:
        for finding in run.findings:
            current = finding_counts.setdefault(
                finding.id,
                {"id": finding.id, "title": finding.title, "severity": finding.severity, "count": 0},
            )
            current["count"] += 1

    recurring_findings = sorted(
        (item for item in finding_counts.values() if item["count"] >= 2),
        key=lambda item: (-item["count"], item["id"]),
    )

    return {
        "extinction_rate": extinction_count / max(1, len(runs)),
        "avg_final_population": mean(run.final_population for run in runs) if runs else 0.0,
        "avg_peak_population": mean(run.peak_population for run in runs) if runs else 0.0,
        "recurring_findings": recurring_findings,
    }


def run_audit(runs: int = 5, ticks_per_run: int = 400, seed_base: int = 1000) -> AuditReport:
    run_summaries = [
        _simulate_run(run_id=index + 1, seed=seed_base + index, ticks=ticks_per_run)
        for index in range(runs)
    ]
    return AuditReport(
        config={
            "runs": runs,
            "ticks_per_run": ticks_per_run,
            "seed_base": seed_base,
        },
        aggregate=_aggregate_runs(run_summaries),
        runs=run_summaries,
    )


def analyze_live_experiment(
    run_id: int,
    seed: int,
    ticks_requested: int,
    history: list[dict[str, Any]],
    events: list[dict[str, Any]],
    state: dict[str, Any],
) -> RunSummary:
    """Same Finding analysis as an in-process run, applied to data pulled from a live
    HTTP sandbox (see agents.simulation_scientist.remote.run_sandbox_experiment) instead
    of an in-process Simulation instance."""
    death_causes, seasonal_deaths = _death_stats(events)
    return _analyze_run(run_id, seed, ticks_requested, history, state, death_causes, seasonal_deaths)


def build_report_from_live_runs(
    runs: list[RunSummary],
    ticks_per_run: int,
    seed_base: int,
) -> AuditReport:
    return AuditReport(
        config={"runs": len(runs), "ticks_per_run": ticks_per_run, "seed_base": seed_base, "mode": "live_sandbox"},
        aggregate=_aggregate_runs(runs),
        runs=runs,
    )
