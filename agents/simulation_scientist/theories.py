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

import random
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
    # `parent_id` is exposed in get_state(), so this can now be a genuine dynamic check
    # rather than a static structural assertion: if kin-aware behavior exists anywhere in
    # the model, close relatives (siblings sharing a parent_id, or parent-child pairs)
    # should cluster spatially more than chance would predict, since conflict/competition
    # would otherwise disperse them the same as any unrelated pair. This is an indirect
    # proxy (raid events themselves and specific attacker/victim identity aren't exposed
    # in the metrics/state schema), not a direct measurement of raid targeting.
    by_parent: dict[Any, list[dict[str, Any]]] = {}
    for r in residents:
        pid = r.get("parent_id")
        if pid is not None:
            by_parent.setdefault(pid, []).append(r)
    sibling_pairs = []
    for siblings in by_parent.values():
        for i in range(len(siblings)):
            for j in range(i + 1, len(siblings)):
                sibling_pairs.append((siblings[i], siblings[j]))
    if len(sibling_pairs) < 5:
        return None  # not enough sibling pairs yet to say anything meaningful

    def _dist(a, b):
        return abs(a.get("x", 0) - b.get("x", 0)) + abs(a.get("y", 0) - b.get("y", 0))

    sibling_dist = mean(_dist(a, b) for a, b in sibling_pairs)
    # Random-pair baseline: sample the same number of arbitrary pairs from the population
    n = len(residents)
    random_pairs = [(residents[random.randrange(n)], residents[random.randrange(n)]) for _ in range(len(sibling_pairs))]
    random_dist = mean(_dist(a, b) for a, b in random_pairs if a is not b) or 1.0

    if sibling_dist >= random_dist * 0.9:
        return TheoryFinding(
            theory="Kin selection / inclusive fitness",
            citation="Hamilton, The Genetical Evolution of Social Behaviour (1964)",
            prediction="Exploitative behavior (raiding another resident for resources) should be measurably rarer "
                       "between close genetic relatives than between unrelated strangers, which should manifest "
                       "indirectly as siblings/parent-child pairs clustering more closely than random pairs.",
            observed={
                "avg_sibling_pair_distance": round(sibling_dist, 2),
                "avg_random_pair_distance": round(random_dist, 2),
                "sibling_pairs_sampled": len(sibling_pairs),
            },
            gap="Sibling/parent-child pairs are no closer together than random pairs of residents — no "
                "detectable kin-clustering signal. Raid targeting (engine.py decide()) selects among adjacent "
                "residents using bond quality and population pressure only; genetic relatedness (available via "
                "Resident.parent_id) may still not be consulted at the actual decision point, or if it is, its "
                "effect isn't yet strong enough to produce a measurable spatial signature.",
            severity="medium",
            suggested_investigation="raid_target_selection, relatedness_coefficient, kin_clustering_strength",
        )
    return None


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
def _risky_knowledge_drift_compare(history, state):
    # extract the full list of knowledge_holder counts per tick
    kh_list = [row['knowledge_holders'] for row in history]
    if len(kh_list) < 10:
        return None  # not enough data

    # how many distinct skills are tracked? (approximate via max possible knowledge holders if all had all skills)
    # from schema: knowledge_holders is count of residents holding at least one knowledge item?
    # But we need a more precise: we want to see if a skill (any single skill) vanishes over time.
    # Use farm_holders as a proxy for a specific, beneficial skill.
    fh_list = [row.get('farmer_holders', 0) for row in history]
    if max(fh_list) < 2:
        return None  # too few holders to measure drift

    # compute linear trend in farmer_holders over last half of history
    n = len(fh_list)
    half = n // 2
    recent = fh_list[half:]
    x = list(range(len(recent)))
    # simple linear regression slope
    mean_x = mean(x)
    mean_y = mean(recent)
    numerator = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, recent))
    denominator = sum((xi - mean_x)**2 for xi in x)
    if denominator == 0:
        return None
    slope = numerator / denominator
    # also compute volatility as coefficient of variation
    cv = pstdev(recent) / mean_y if mean_y > 0 else 0

    # test: if the skill is held by few (e.g., <10% of population latest) and slope is negative & significant
    latest_pop = history[-1]['pop']
    latest_fh = fh_list[-1]
    if latest_pop <= 0:
        return None
    ratio = latest_fh / latest_pop
    if ratio < 0.1 and slope < -0.01 and cv > 0.2:
        # gap: cultural drift is eroding a beneficial skill
        return TheoryFinding(
            theory="Risky knowledge / extinction of beneficial traits",
            citation="Henrich, The Secret of Our Success (2015); Boyd & Richerson, Culture and the Evolutionary Process (1985)",
            prediction="A beneficial skill held by few should be vulnerable to stochastic loss, causing negative drift in holder count.",
            observed={
                'farmer_holder_slope': round(slope, 4),
                'latest_farmer_holder_ratio': round(ratio, 4),
                'cv_of_farmer_holders': round(cv, 3)
            },
            gap=f"Farmer-holders are a small fraction of the population (ratio={ratio:.3f}) but their count is drifting downward (slope={slope:.4f}) with high volatility (CV={cv:.3f}), consistent with stochastic extinction of a valuable skill. The model lacks a mechanism for high-fidelity social learning or memory that would preserve such traits when their bearers die.",
            severity="medium",
            suggested_investigation="knowledge_holder_mortality_rate, skill_transmission_fidelity, active_teaching_mechanics"
        )
    return None


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
        TheoryLens("Risky knowledge / extinction of beneficial traits (cultural drift & forgetting)", "Henrich, The Secret of Our Success (2015); Boyd & Richerson, Culture and the Evolutionary Process (1985)",
               "When a beneficial skill (e.g., farming, herding, writing) is held by few individuals (low 'knowledge_ratio'), random death events should cause stochastic loss of that skill in the population, leading to a downward drift in the count of knowledge holders over time — especially at low population sizes.",
               _risky_knowledge_drift_compare),
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
