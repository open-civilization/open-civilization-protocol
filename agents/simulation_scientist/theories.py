"""Theory lenses for the Simulation Scientist Agent.

Each lens encodes a real-world quantitative theory as a concrete PREDICTION
and a COMPARISON function that checks simulation data against that
prediction. This is what lets the agent discover structural gaps the way a
human researcher would — "here is what the established theory predicts,
here is what we observe, here is the gap" — rather than only checking a
fixed list of ad hoc heuristics (see audit.py).

The five lenses below are a SEED set (population dynamics, information
theory, kin selection, collective action, exchange economics), not a fixed
ceiling. The agent is expected to grow this list itself: when an anomaly
doesn't match any registered lens, `discovery.py` asks the LLM to identify
the most authoritative real-world theory for that specific domain — which
may be economics, political science, philosophy, physics, or anything
else — and appends a new lens function here, plus a citation write-up under
`theories/`. Do not treat this file's current contents as the intended final
scope of what the agent can reason about.

Every lens is intentionally self-contained and numeric: a `TheoryFinding`
always carries the observed value(s), so an LLM advisor (or a human) can
judge severity and propose a specific, testable change rather than a vague
narrative complaint.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from statistics import mean, pstdev
from typing import Any, Callable, Optional


@dataclass
class TheoryFinding:
    theory: str
    citation: str
    prediction: str
    observed: dict[str, Any]
    gap: str
    severity: str  # "none" | "low" | "medium" | "high"
    suggested_investigation: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TheoryLens:
    name: str
    citation: str
    prediction: str
    compare: Callable[[list[dict[str, Any]], dict[str, Any]], Optional[TheoryFinding]]


# ── Lens 1: Malthusian population dynamics ──
# Malthus (1798): population grows geometrically against resources that grow
# arithmetically, so population is checked back toward the subsistence ceiling
# by "positive checks" (famine, disease, conflict) whenever it overshoots.
# Prediction: population should oscillate AROUND carrying capacity, not settle
# durably far above it (chronic overshoot with no correction) or far below it
# (chronic underuse with no growth pressure).

def _malthusian_compare(history: list[dict[str, Any]], state: dict[str, Any]) -> Optional[TheoryFinding]:
    if len(history) < 20:
        return None
    tail = history[-min(100, len(history)):]
    pressures = [float(r.get("pressure", 0.0)) for r in tail]
    avg_pressure = mean(pressures)
    pressure_volatility = pstdev(pressures) if len(pressures) > 1 else 0.0

    if avg_pressure <= 1.15:
        return TheoryFinding(
            theory="Malthusian population dynamics",
            citation="Malthus, An Essay on the Principle of Population (1798)",
            prediction="Population should press against and oscillate around carrying capacity, "
                       "not settle comfortably below it for an extended period.",
            observed={"avg_tail_pressure": round(avg_pressure, 3), "pressure_volatility": round(pressure_volatility, 3)},
            gap="Population is running below the pressure band expected from the growth/checks model — "
                "either checks are too strong (over-suppressing growth) or resource capacity is overestimated.",
            severity="low",
            suggested_investigation="fertility_suppression_curve, carrying_capacity_formula",
        )

    if avg_pressure >= 1.3 and pressure_volatility <= 0.08:
        return TheoryFinding(
            theory="Malthusian population dynamics",
            citation="Malthus, An Essay on the Principle of Population (1798)",
            prediction="Sustained overshoot should trigger positive checks (starvation, disease, conflict) "
                       "strong enough to produce visible oscillation, not a flat, stable overshoot plateau.",
            observed={"avg_tail_pressure": round(avg_pressure, 3), "pressure_volatility": round(pressure_volatility, 3)},
            gap="Population sits durably above carrying capacity with low volatility — the checks are firing "
                "but are calibrated to a stable equilibrium rather than the boom-bust cycle Malthus describes. "
                "This usually means a surplus/storage/scavenging mechanic is propping up an artificially high "
                "effective ceiling instead of true carrying capacity being enforced.",
            severity="medium",
            suggested_investigation="storage_and_scavenging_effect_on_effective_capacity, malnutrition_curve_steepness",
        )
    return None


# ── Lens 2: Information theory / transmission entropy ──
# Shannon (1948): every noisy transmission step loses information; without
# redundancy, fidelity decays with the number of hops from the source.
# Prediction: skill LEVELS for a widely-adopted piece of knowledge should
# retain meaningful variance across the population (closer-to-source /
# more-practiced individuals ahead of newer/further recipients) — if levels
# collapse to near-uniform once adoption is high, transmission is behaving
# as a noiseless broadcast, not a noisy peer-to-peer channel.

def _information_theory_compare(history: list[dict[str, Any]], state: dict[str, Any]) -> Optional[TheoryFinding]:
    residents = state.get("residents", [])
    if len(residents) < 30:
        return None

    for skill_name in ("food_storage", "crop_cultivation", "spoken_language"):
        levels = [r.get("skills", {}).get(skill_name, 0.0) for r in residents if r.get("skills", {}).get(skill_name, 0.0) > 0]
        if len(levels) < 20:
            continue
        adoption_ratio = len(levels) / len(residents)
        if adoption_ratio < 0.8:
            continue  # only meaningful once a skill has actually saturated
        avg_level = mean(levels)
        stdev_level = pstdev(levels)
        coefficient_of_variation = stdev_level / avg_level if avg_level > 0 else 0.0
        if coefficient_of_variation < 0.15:
            return TheoryFinding(
                theory="Information theory / transmission entropy",
                citation="Shannon, A Mathematical Theory of Communication (1948)",
                prediction="A trait propagating through repeated noisy peer-to-peer transmission should retain "
                           "meaningful variance across recipients (some closer to the source or more-practiced, "
                           "some further/newer) — it should not converge to a single near-uniform value.",
                observed={
                    "skill": skill_name,
                    "adoption_ratio": round(adoption_ratio, 3),
                    "avg_level": round(avg_level, 2),
                    "coefficient_of_variation": round(coefficient_of_variation, 3),
                },
                gap=f"'{skill_name}' has saturated adoption ({adoption_ratio:.0%}) with very low variance in skill "
                    "level (CV < 0.15) — the population is converging to a single value as if receiving the "
                    "knowledge from a single broadcast source, not degrading it through a chain of noisy transfers.",
                severity="medium",
                suggested_investigation="transmission_fidelity_hop_tracking, knowledge_decay_absence",
            )
    return None


# ── Lens 3: Kin selection / inclusive fitness ──
# Hamilton (1964): altruism (and its inverse, restraint from harming another)
# is favored by selection when relatedness x benefit exceeds cost (rb > c) —
# organisms should behave more cooperatively, and less exploitatively, toward
# close kin than toward unrelated individuals.
# Prediction: aggressive/exploitative actions (raiding) should be rarer
# between parent-child or sibling pairs than between unrelated residents.

def _kin_selection_compare(history: list[dict[str, Any]], state: dict[str, Any]) -> Optional[TheoryFinding]:
    residents = state.get("residents", [])
    if len(residents) < 10:
        return None
    # The engine does not currently expose kinship (parent_id / sibling structure) in
    # get_state()'s per-resident payload, nor does the raid targeting logic reference
    # relatedness at all (see decide()'s RAID block — it biases by bond quality/pressure,
    # never by parent_id lineage). We can detect the STRUCTURAL absence directly: kinship
    # is invisible to raiding, so no comparison can even be attempted, which is itself the
    # finding — Hamilton's rule cannot be checked because the model has no representation
    # of relatedness at the point where it should matter (the raid decision).
    return TheoryFinding(
        theory="Kin selection / inclusive fitness",
        citation="Hamilton, The Genetical Evolution of Social Behaviour (1964)",
        prediction="Exploitative behavior (raiding another resident for resources) should be measurably rarer "
                   "between close genetic relatives (parent-child, siblings) than between unrelated strangers.",
        observed={"kinship_tracked_in_raid_logic": False},
        gap="Raid targeting (engine.py decide()) selects among adjacent residents using bond quality and "
            "population pressure only. Genetic relatedness (available via Resident.parent_id, which siblings "
            "and parent-child pairs share/link) is never consulted, so a starving resident is exactly as likely "
            "to raid a parent or sibling as a total stranger. Hamilton's rule cannot currently produce any "
            "effect in this model because the decision point has no access to relatedness at all.",
        severity="high",
        suggested_investigation="raid_target_selection, parent_id_lineage_lookup, relatedness_coefficient",
    )


# ── Lens 4: Tragedy of the commons / collective action ──
# Hardin (1968) / Olson (1965): an unowned, unenforced shared resource is
# overexploited relative to the group-optimal harvesting rate, because each
# individual captures the full benefit of their own extraction while bearing
# only a fraction of the shared depletion cost.
# Prediction: biomass on high-traffic (many distinct foragers) cells should be
# driven lower, relative to terrain capacity, than on low-traffic cells of the
# same terrain type — i.e., crowding itself should measurably deplete land
# beyond what terrain alone would predict.

def _commons_compare(history: list[dict[str, Any]], state: dict[str, Any]) -> Optional[TheoryFinding]:
    residents = state.get("residents", [])
    biomass = state.get("biomass", [])
    terrain = state.get("terrain", [])
    if not residents or not biomass or not terrain or len(biomass) != len(terrain):
        return None

    traffic: dict[int, int] = {}
    gw = state.get("gw", 60)
    for r in residents:
        idx = r.get("y", 0) * gw + r.get("x", 0)
        traffic[idx] = traffic.get(idx, 0) + 1

    by_terrain: dict[str, dict[str, list[float]]] = {}
    for idx, terr in enumerate(terrain):
        bucket = "crowded" if traffic.get(idx, 0) >= 2 else "uncrowded"
        by_terrain.setdefault(terr, {"crowded": [], "uncrowded": []}).setdefault(bucket, []).append(biomass[idx])

    ratios = []
    for terr, buckets in by_terrain.items():
        crowded, uncrowded = buckets.get("crowded", []), buckets.get("uncrowded", [])
        if len(crowded) >= 3 and len(uncrowded) >= 3:
            ratios.append(mean(crowded) / max(0.01, mean(uncrowded)))

    if not ratios:
        return None
    avg_ratio = mean(ratios)
    if avg_ratio >= 0.85:
        return TheoryFinding(
            theory="Tragedy of the commons / collective action problem",
            citation="Hardin, The Tragedy of the Commons (1968); Olson, The Logic of Collective Action (1965)",
            prediction="Biomass on cells visited by multiple foragers should sit measurably lower (relative to "
                       "terrain-matched uncrowded cells) than a group-optimal harvesting rate would leave — "
                       "unowned, unenforced land gets overexploited.",
            observed={"crowded_to_uncrowded_biomass_ratio": round(avg_ratio, 3)},
            gap="Crowded cells hold about as much standing biomass as uncrowded cells of the same terrain — "
                "no measurable overexploitation signature from crowding. Either regrowth rates outpace "
                "extraction fast enough to mask any commons effect, or cultivation's land-improvement "
                "mechanic is compensating for it in a way that hides the underlying dynamic.",
            severity="low",
            suggested_investigation="regrow_rate_vs_extraction_rate, cultivation_masking_depletion",
        )
    return None


# ── Lens 5: Exchange economics / absence of a medium of exchange ──
# Basic monetary economics (see e.g. Jevons 1875 on the "double coincidence
# of wants"): without a fungible medium of exchange, surplus in one location
# cannot efficiently reach scarcity in another except through direct transport
# of the individual who holds it (migration) — trade requires either barter
# (rare, needs matching mutual wants) or money.
# Prediction: local food surplus (leftover) and local scarcity (near-zero
# biomass + leftover) should coexist simultaneously in different regions of
# the map, since nothing currently redistributes surplus except a resident
# physically moving.

def _exchange_economics_compare(history: list[dict[str, Any]], state: dict[str, Any]) -> Optional[TheoryFinding]:
    leftover = state.get("leftover", [])
    biomass = state.get("biomass", [])
    if not leftover or not biomass or len(leftover) != len(biomass):
        return None

    surplus_cells = sum(1 for lo in leftover if lo > 10)
    scarce_cells = sum(1 for lo, bm in zip(leftover, biomass) if lo < 1 and bm < 2)
    total_cells = len(leftover)
    if total_cells == 0:
        return None
    surplus_ratio = surplus_cells / total_cells
    scarce_ratio = scarce_cells / total_cells

    if surplus_ratio > 0.02 and scarce_ratio > 0.02:
        return TheoryFinding(
            theory="Exchange economics / medium-of-exchange absence",
            citation="Jevons, Money and the Mechanism of Exchange (1875) — the 'double coincidence of wants' problem",
            prediction="Without a medium of exchange, local surplus and local scarcity should coexist "
                       "simultaneously across the map rather than equalizing, since only physical migration "
                       "(not trade) can move resources between regions.",
            observed={"surplus_cell_ratio": round(surplus_ratio, 4), "scarce_cell_ratio": round(scarce_ratio, 4)},
            gap="Both surplus-heavy and scarcity-heavy cells coexist right now, consistent with the "
                "prediction — this is expected given Phase 1 has no trade mechanic (RFC-0002/RFC-0007 list "
                "trade networks as a future, not-yet-implemented concept). Flagged as confirming evidence, "
                "not a bug: worth tracking whether this gap narrows if/when a trade mechanic is ever added.",
            severity="none",
            suggested_investigation="trade_network_emergence (future work, not a current defect)",
        )
    return None


# SEED_LENSES_END — discovery.py looks for this exact marker and inserts newly
# discovered lenses (function definition + registration) directly above it, so the
# lens library can grow without ever needing to touch the lenses defined above.
LENSES: list[TheoryLens] = [
    TheoryLens("Malthusian population dynamics", "Malthus (1798)",
               "Population oscillates around carrying capacity under growth/check dynamics.",
               _malthusian_compare),
    TheoryLens("Information theory / transmission entropy", "Shannon (1948)",
               "Noisy multi-hop transmission preserves variance; it does not converge to uniformity.",
               _information_theory_compare),
    TheoryLens("Kin selection / inclusive fitness", "Hamilton (1964)",
               "Exploitative behavior is rarer between close kin than between strangers.",
               _kin_selection_compare),
    TheoryLens("Tragedy of the commons / collective action", "Hardin (1968); Olson (1965)",
               "Unowned shared resources are overexploited relative to the group-optimal rate.",
               _commons_compare),
    TheoryLens("Exchange economics / medium-of-exchange absence", "Jevons (1875)",
               "Without trade, local surplus and local scarcity coexist rather than equalizing.",
               _exchange_economics_compare),
    # AUTO-DISCOVERED LENSES REGISTERED BELOW THIS LINE — appended by discovery.py
]


def run_theory_lenses(history: list[dict[str, Any]], state: dict[str, Any]) -> list[TheoryFinding]:
    """Applies every registered theory lens to the given run data, returning only the
    lenses that produced a finding (a lens returning None means no gap worth reporting)."""
    findings = []
    for lens in LENSES:
        try:
            result = lens.compare(history, state)
        except Exception:  # noqa: BLE001 - a broken lens should not crash the whole audit
            continue
        if result is not None:
            findings.append(result)
    return findings
