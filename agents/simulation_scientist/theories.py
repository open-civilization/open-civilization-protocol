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


def _henrich_demographic_cultural_loss_compare(history, state):
    # Extract skill/knowledge holders per tick
    holders_keys = ['knowledge_holders', 'language_holders', 'writing_holders',
                    'shelter_holders', 'clothing_holders', 'fire_holders']
    # Check maximum holders for each skill across all ticks
    max_holders = {k: 0 for k in holders_keys}
    for row in history:
        for k in holders_keys:
            v = row.get(k, 0)
            if v is not None and v > max_holders[k]:
                max_holders[k] = v
    # Identify skills ever held by fewer than 5 individuals (critical loss risk)
    at_risk_skills = [k for k, v in max_holders.items() if v < 5]
    # Check that at the final tick, for any skill that ever had >=5 holders,
    # it still has >=5 holders
    final = history[-1]
    lost_skills = []
    for k in holders_keys:
        if max_holders.get(k, 0) >= 5:
            final_v = final.get(k, 0)
            if final_v is None or final_v < 5:
                lost_skills.append(k)
    # Also check that number of distinct skills held > 0 is not declining in the tail
    # (we define tail as last 20% of ticks)
    n = len(history)
    tail_start = int(n * 0.8)
    tail_ticks = history[tail_start:]
    first_tail = tail_ticks[0] if tail_ticks else {}
    last_tail = tail_ticks[-1] if tail_ticks else {}
    count_first = sum(1 for k in holders_keys if first_tail.get(k, 0) and first_tail[k] > 0)
    count_last = sum(1 for k in holders_keys if last_tail.get(k, 0) and last_tail[k] > 0)
    # Also check if population ever fell below 40 (critical threshold from Henrich)
    min_pop = min(row.get('pop', 999999) for row in history)
    population_bottleneck = min_pop < 40
    if population_bottleneck and count_last < count_first:
        return TheoryFinding(
            theory="Demographic cultural loss (Tasmanian effect)",
            citation="Henrich, J. (2004). Demography and cultural evolution. American Antiquity, 69(2), 197-214.",
            prediction="Complex skills should be maintained once acquired if population remains above ~40, but may be lost irreversibly after a population bottleneck below that threshold.",
            observed={
                "lost_skills": lost_skills,
                "first_tail_skill_count": count_first,
                "last_tail_skill_count": count_last,
                "minimum_population": min_pop,
                "population_bottleneck_detected": population_bottleneck
            },
            gap=f"Population fell to {min_pop} (below Henrich's ~40 threshold) and {count_last - count_first} skills were lost in the tail, indicating irreversible cultural loss despite later recovery.",
            severity="high",
            suggested_investigation="min_viable_pop_for_skill_transmission, skill_complexity_metrics"
        )
    # Even without a bottleneck, check monotonicity in tail
    if count_last < count_first - 1:  # loss of 2 or more skills
        return TheoryFinding(
            theory="Demographic cultural loss (Tasmanian effect)",
            citation="Henrich, J. (2004). Demography and cultural evolution. American Antiquity, 69(2), 197-214.",
            prediction="Complex skills should be stable or increase over time once acquired, unless population experiences a severe bottleneck.",
            observed={
                "first_tail_skill_count": count_first,
                "last_tail_skill_count": count_last,
                "minimum_population": min_pop,
                "lost_skills": lost_skills
            },
            gap=f"In the last 20% of ticks, the number of maintained skills dropped from {count_first} to {count_last} without a known population crash. This suggests cumulative cultural loss.",
            severity="medium",
            suggested_investigation="skill_loss_event_timing, social_network_connectivity"
        )
    return None


def _linguistic_niche_compare(history, state):
    if len(history) < 20:
        return None
    # get language_holders near beginning and end
    early = history[min(19, len(history)//4)]
    mid = history[len(history)//2]
    late = history[-1]
    early_pop = early.get('pop', 0)
    late_pop = late.get('pop', 0)
    early_lang = early.get('language_holders', 0)
    late_lang = late.get('language_holders', 0)
    # if population changed significantly, language should not simply track pop linearily
    if early_pop * 0.8 > late_pop or late_pop > early_pop * 1.2:
        return None  # pop changed significantly, check ratio change
    # compute language holder proportion change
    early_ratio = early_lang / max(early_pop, 1)
    late_ratio = late_lang / max(late_pop, 1)
    change = abs(early_ratio - late_ratio)
    # If the ratio is very stable despite theory predicting simplification (decline in specialist holders), that's a gap
    if change < 0.05 and early_ratio > 0.5 and late_ratio > 0.5:
        # also check if writing is present - that is a complexity indicator
        early_write = early.get('writing_holders', 0) / max(early_pop, 1)
        late_write = late.get('writing_holders', 0) / max(late_pop, 1)
        if late_write >= early_write * 0.8:  # writing is not being lost
            return TheoryFinding(
                theory='Linguistic niche hypothesis',
                citation='Lupyan, G., & Dale, R. (2010). PLoS ONE, 5(1), e8559.',
                prediction='Under stable high population, language complexity (specialist holders like writing) should decrease proportionally due to adult learning pressures.',
                gap=f'Language proportions remain very stable (early {early_ratio:.2f}, late {late_ratio:.2f}) and writing is not declining ({early_write:.2f} -> {late_write:.2f}), contrary to the expected simplification in a large community with many adult learners.',
                severity='medium'
            )
    return None


def _social_disorganization_compare(history, state):
    # Check average bond count from last 10 ticks of history
    if len(history) < 10:
        return None
    recent = history[-10:]
    # Estimate bond count from resident data in state (we can compute mean bonds from state.residents)
    bond_counts = [r['bonds'] for r in state['residents']]
    avg_bonds = mean(bond_counts) if bond_counts else 0.0
    # check if bond count is moderately high (say > 2) and variance is low
    if avg_bonds < 2:
        # insufficient social ties to test theory
        return None
    # compute stdev to see if bonds are homogeneous
    std_bonds = pstdev(bond_counts) if len(bond_counts) > 1 else 0.0
    # now check population stability: volatility in pop over recent ticks
    pop_vals = [h['pop'] for h in recent]
    pop_volatility = pstdev(pop_vals) / mean(pop_vals) if mean(pop_vals) > 0 else 0.0
    # also check if there is any trend of extreme inequality in bonds? maybe a proxy for disorganization
    # Gini of bond counts? Use already available gini from latest history (but that's overall wealth/energy not bonds)
    gini_latest = history[-1].get('gini', 0.5)
    # If bond count is high (>2) and homogeneous (std < 1) but population volatility is also moderate (>0.02) or gini is high >0.6, then social disorganization predicted to produce conflict
    # We'll just flag if bond avg > 2 and pop_volatility > 0.03: suggests social bonds aren't preventing disorder
    # The theory says high social organization (many bonds, low inequality) = low crime, stable pop. If bonds are high but volatility still present => disorganization gap.
    if avg_bonds > 2.0 and std_bonds < 2.0 and pop_volatility > 0.03:
        return TheoryFinding(
            theory="Social Disorganization Theory (collective efficacy / social capital)",
            citation="Shaw & McKay 1942; Sampson, Raudenbush & Earls 1997",
            prediction="High average bond count and low bond inequality should reduce internal predation, producing low population volatility; observed: bonds are dense but population still fluctuates.",
            gap=f"avg_bonds={avg_bonds:.2f}, sd_bonds={std_bonds:.2f}, pop_volatility={pop_volatility:.3f} - social capital appears high but does not stabilize population as predicted.",
            severity="medium"
        )
    return None


def _risk_pooling_and_mutual_aid_compare(history, state):
    if len(history) < 20:
        return None
    # Focus on the last 20% of ticks (chronic pressure region)
    tail = history[-max(20, len(history)//5):]
    # Compute average pressure and average per-capita energy in tail
    pressures = [t['pressure'] for t in tail]
    energies = [t['avg_energy'] for t in tail]
    avg_pressure = mean(pressures)
    avg_energy = mean(energies)
    # If pressure is not sustainably above 1.0, theory doesn't apply
    if avg_pressure < 1.1:
        return None
    # Theory: if bonds enable risk pooling, average energy should stay above a simple
    # individual‑foraging baseline. We approximate baseline as: if each agent only forages
    # on their own (no sharing), the average energy would drop to near the minimum viable
    # intake per tick. Let's use erosion_threshold_kcal (2000) as a proxy for that floor.
    erosion_threshold = 2000.0
    # Check if observed average energy is significantly above that floor
    if avg_energy < erosion_threshold * 0.9:  # within 10% of floor — no buffering
        return None
    # Now check if the pressure plateau is unusually flat (low volatility) suggesting
    # a social buffer, not raw Malthusian oscillation
    pressure_volatility = pstdev(pressures) / avg_pressure if avg_pressure > 0 else 0
    # If volatility is very low AND energy is above floor, that's a sign of risk pooling
    if pressure_volatility < 0.15:
        # Count bonds per resident in final snapshot
        residents = state['residents']
        if len(residents) == 0:
            return None
        avg_bonds = mean([r['bonds'] for r in residents])
        # If average bonds > 1, there's enough network structure to enable mutual aid
        if avg_bonds > 1.0:
            return TheoryFinding(
                theory="Risk Pooling and Mutual Aid (Solidarity Hypothesis)",
                citation="Polanyi, Karl. The Great Transformation (1944); Scott, James C. The Moral Economy of the Peasant (1976)",
                prediction="Under chronic resource pressure, agents with low individual calorie reserves will sustain higher average energy than individual foraging alone would allow, because redistribution via social bonds (gifts, sharing) buffers against stochastic shortfalls.",
                gap=f"Observed: avg_tail_pressure={avg_pressure:.3f}, avg_energy={avg_energy:.1f} kcal, pressure_volatility={pressure_volatility:.3f}, avg_bonds={avg_bonds:.2f}. The plateau is flat and elevated above the individual-foraging floor, consistent with mutual aid but not explained by Malthusian dynamics or storage alone.",
                severity="medium",
                suggested_investigation="bond_redistribution_effect_on_energy_floor, gift_economy_parameters, inequality_gini_and_risk_pooling_efficiency"
            )
    return None


def _social_network_stability_compare(history, state):
    # Extract recent metrics to analyze social network impact
    recent_pop = [h['pop'] for h in history[-10:]]  # last 10 ticks
    recent_avg_energy = [h['avg_energy'] for h in history[-10:]]
    avg_pop = mean(recent_pop)
    avg_energy = mean(recent_avg_energy)
    avg_pressure = mean([h['pressure'] for h in history[-10:]])

    # Define expected effect of strong social networks
    if avg_pressure > 1:  # indicates chronic resource pressure
        # Ideal scenario under network theory: lower fluctuation in population despite pressure
        expected_stability = True
    else:
        expected_stability = False

    # Calculate observed stability based on avg population fluctuations
    population_fluctuation = pstdev(recent_pop)
    energy_fluctuation = pstdev(recent_avg_energy)

    # Criteria for gap: if population fluctuation is high but pressure is also high
    if population_fluctuation > 10 and expected_stability:
        return TheoryFinding(
            theory='Social Network Theory',
            citation='Borgatti, S. P., & Halgin, D. S. (2011). Analyzing Affiliation Networks. In The Sage Handbook of Social Network Analysis.',
            prediction='Tightly connected social networks should maintain stability and resilience in resource-challenged environments, leading to lower volatility in population dynamics despite high carrying capacity pressure.',
            observed={
                'population_fluctuation': population_fluctuation,
                'avg_pressure': avg_pressure,
                'avg_pop': avg_pop,
                'avg_energy': avg_energy
            },
            severity='high',
            gap='Observed population fluctuation is high despite expected stability from social networks, indicating potential disconnection or ineffective bonding rather than cohesive community resilience.'
        )
    return None


def _social_network_theory_compare(history, state):
    num_residents = len(state['residents'])
    total_bonds = sum(resident['bonds'] for resident in state['residents'])
    avg_bonds_per_resident = total_bonds / num_residents if num_residents > 0 else 0
    threshold = 0.6  # Hypothetical threshold for social network resilience
    if avg_bonds_per_resident < threshold:
        return TheoryFinding(
            run=None,
            theory="Social Network Theory",
            citation="Granovetter, M. S. (1973). The Strength of Weak Ties.",
            prediction="Communities should show enhanced resilience and resource access through diverse and interconnected social networks.",
            observed={
                "avg_bonds_per_resident": avg_bonds_per_resident
            },
            gap="Total social bonds per resident indicate a limited social network, reducing resilience and resource access potential.",
            severity="medium",
            suggested_investigation="analyze_social_bond_structure"
        )
    return None


def _social_construction_compare(history, state):
    population = state['residents']
    avg_bonds = mean([resident['bonds'] for resident in population])
    pressure = mean([entry['pressure'] for entry in history])

    # If social bonds are high and population pressure is high, a gap in social resilience may exist
    if avg_bonds > 200 and pressure > 1.2:
        return TheoryFinding(
            theory='Social Construction of Reality',
            citation='Berger, P. L., & Luckmann, T. The Social Construction of Reality: A Treatise in the Sociology of Knowledge (1966)',
            prediction='High collective understanding of environmental challenges should lead to adaptive practices rather than persistent overshoot.',
            observed={'avg_bonds': avg_bonds, 'pressure': pressure},
            gap='Despite high bonding, the population is experiencing sustained resource pressure without anticipated adaptive social behaviors, indicating a failure in perceived reality leading to maladaptive strategies.',
            severity='high'
        )
    return None


def _social_conflict_theory_compare(history, state):
    pressure_threshold = 1.1
    avg_pressure = mean([h['pressure'] for h in history])
    if avg_pressure < pressure_threshold:
        return None
    total_bonds = sum(resident['bonds'] for resident in state['residents'])
    insufficient_bonds = total_bonds < (len(state['residents']) * 0.5)
    if insufficient_bonds:
        return TheoryFinding(
            theory_name='Social Conflict Theory',
            description='Community cohesion is breaking down under resource pressure.',
            supporting_evidence={'avg_pressure': avg_pressure, 'total_bonds': total_bonds},
            predicted_outcome='Increased conflict and instability due to insufficient social bonds.',
        )
    return None


def _social_identity_theory_compare(history, state):
    avg_bonds = mean(resident['bonds'] for resident in state['residents'])
    max_bonds = max(resident['bonds'] for resident in state['residents'])
    avg_pressures = mean(h['pressure'] for h in history)

    # Identifying the bonding behavior under pressure
    # If bond counts are low or volatile while pressure is high, it indicates a gap
    if avg_bonds < 2 or avg_pressures > 1.5:
        return TheoryFinding(
            theory='Social Identity Theory',
            citation='Tajfel, H., & Turner, J. C. (1979)',
            prediction='In contexts of resource scarcity and population pressure, residents will favor in-group cooperation and bonding over inter-group conflict, thereby stabilizing social structures despite carrying capacity challenges.',
            observed={'avg_bonds': avg_bonds, 'max_bonds': max_bonds, 'avg_pressure': avg_pressures},
            gap='The average bond count is low while pressure is high, suggesting a potential deficiency in social cohesion and identity reinforcement, contrary to predictions.',
            severity='high',
            suggested_investigation='explore_in_group_vs_out_group_bonding_patterns'
        )
    return None


def _social_bond_theory_compare(history, state):
    bond_counts = [resident['bonds'] for resident in state['residents']]
    avg_bonds = mean(bond_counts)
    total_population = len(state['residents'])
    avg_health = mean([resident['health'] for resident in state['residents']])
    avg_energy = mean([resident['energy'] for resident in state['residents']])
    avg_storage_skill = mean([resident['skills'].get('storage', 0) for resident in state['residents']])

    if avg_bonds < total_population * 0.1 and (avg_health < 0.5 or avg_energy < 100):
        return TheoryFinding(
            theory='Social Bond Theory',
            prediction='Weak social bonds will reduce cooperative behavior when population pressures are high, leading to higher mortality rates and lower vitality of the population.',
            severity='high',
            observed={'avg_bonds': avg_bonds, 'avg_health': avg_health, 'avg_energy': avg_energy},
            gap='The observed average number of bonds per resident is very low, while average health and energy levels also suggest insufficient social cooperation to buffer against resource pressures.'
        )
    return None


def _social_coordination_compare(history, state):
    avg_bonds = mean([resident['bonds'] for resident in state['residents']])
    pressure = median([h['pressure'] for h in history])
    avg_pressure = mean([h['pressure'] for h in history])
    bond_threshold = 5  # Hypothetical threshold for effective coordination
    if avg_bonds < bond_threshold and avg_pressure > 1.2:
        return TheoryFinding(
            theory='Social Coordination Theory',
            citation='Coleman, James S., Foundations of Social Theory, 1990',
            prediction='Lower levels of social bonds relative to high resource pressure should lead to decreased cooperation and higher instability.',
            observed={
                'avg_bonds': avg_bonds,
                'avg_pressure': avg_pressure,
            },
            gap='The residents exhibit low levels of social bonding which are insufficient to mitigate the negative impacts of high resource pressure, leading to an equilibrium without oscillation in the population dynamics.',
            severity='high',
            suggested_investigation='social_bonding_effect_on_population_stability'
        )
    return None


def _social_cohesion_compare(history, state):
    # Calculate average bonds per resident
    total_bonds = sum(resident['bonds'] for resident in state['residents'])
    avg_bonds = total_bonds / len(state['residents']) if state['residents'] else 0
    
    # Calculate average pressure
    avg_pressure = mean(entry['pressure'] for entry in history)
    
    # Prediction check: high pressure should correlate with higher bonds
    if avg_pressure > 1.25 and avg_bonds < 1:
        return TheoryFinding(
            theory='Social Cohesion Theory',
            citation='Durkheim, E. (1893), The Division of Labor in Society',
            prediction='In conditions of high resource pressure, individuals will establish and strengthen social ties to promote group survival, leading to increased cooperation and reduced tension within the population.',
            observed={
                'avg_bonds': avg_bonds,
                'avg_pressure': avg_pressure
            },
            gap='Despite high resource pressure, the average bond count is low, indicating insufficient social cohesion expected during such stress.',
            severity='high',
            suggested_investigation='factors_affecting_social_cohesion_under_pressure'
        )
    return None


def _moral_economy_compare(history, state):
    total_bonds = sum(resident['bonds'] for resident in state['residents'])
    avg_bonds = total_bonds / len(state['residents']) if state['residents'] else 0
    avg_pressure = mean(h['pressure'] for h in history)
    gini = mean(h['gini'] for h in history)

    # Evaluate if community norms of fairness are eroding
    if avg_bonds < 1 and avg_pressure > 1 and gini > 0.3:
        return TheoryFinding(
            theory='Theory of Moral Economy',
            citation='E.P. Thompson, The Making of the English Working Class, 1963',
            prediction='In contexts of acute resource scarcity, communities will adhere to norms around fairness and mutual aid, preventing the emergence of exploitative behaviors despite high competition for resources.',
            observed={'avg_bonds': avg_bonds, 'avg_pressure': avg_pressure, 'avg_gini': gini},
            gap='The observed bond count is low, indicating a failure of communal obligation and fair resource distribution despite high resource pressure and inequality, contrary to the prediction of the Theory of Moral Economy.',
            severity='high',
            suggested_investigation='assess_resource_distribution_narratives_and_norms'
        )
    return None


def _collective_efficacy_compare(history, state):
    # Initialize variables to track the metrics
    total_population = 0
    total_bonds = 0
    tick_count = 0

    for tick in history:
        total_population += tick['pop']
        total_bonds += sum(resident['bonds'] for resident in state['residents'])
        tick_count += 1

    if tick_count == 0:
        return None  # No data to analyze

    avg_population = total_population / tick_count if tick_count > 0 else 0
    avg_bonds = total_bonds / len(state['residents']) if len(state['residents']) > 0 else 0

    # If the average bonds are low relative to population, it indicates low collective efficacy
    if avg_bonds < 1:
        return TheoryFinding(
            theory='Collective Efficacy',
            observation='Average bonds per resident are below 1, indicating weak social cohesion.',
            prediction='This suggests a lack of collective efficacy contributing to extinction rates in the simulation.'
        )
    return None


def _self_determination_theory_compare(history, state):
    # Check the last tick for population data
    last_tick = history[-1] if history else None
    if last_tick:
        total_population = last_tick['pop']
        avg_health = last_tick['avg_health']
        avg_energy = last_tick['avg_energy']
        bonds_count = sum(resident['bonds'] for resident in state['residents'])
        # Determine the relative health and energy states
        if (total_population == 0) or (avg_health < 0.5 and avg_energy < 0.5):
            return TheoryFinding(
                name='Self-Determination Theory Gap',
                finding='A significant gap exists as the population failed to thrive, indicating potential unmet psychological needs among residents.',
                evidence={
                    'total_population': total_population,
                    'avg_health': avg_health,
                    'avg_energy': avg_energy,
                    'bonds_count': bonds_count
                }
            )
    return None


def _cognitive_load_theory_compare(history, state):
    avg_pressure = mean(metric['pressure'] for metric in history)
    avg_bonds = mean(resident['bonds'] for resident in state['residents'])
    # Check if high pressure correlates with low bonding
    if avg_pressure > 0.5 and avg_bonds < 1:
        return TheoryFinding(
            theory='Cognitive Load Theory',
            citation='Sweller, J. (1988)',
            gap='The average bonding is very low under high pressure, suggesting that cognitive overload restricts social bonding efforts.',
            severity='high',
            observed={'avg_bonds': avg_bonds, 'avg_pressure': avg_pressure}
        )
    return None


def _ostrom_1990_compare(history, state):
    max_bonds = max(resident['bonds'] for resident in state['residents'])
    avg_pressure = mean(metric['pressure'] for metric in history)
    effectiveness_criterion = 5  # Threshold for effective social cohesion
    # Observation of resilience in governance systems under collective pressure
    if max_bonds < effectiveness_criterion and avg_pressure > 1.2:
        return TheoryFinding(
            theory='Communal Resource Management Theory',
            citation='Ostrom, E. (1990), Governing the Commons: The Evolution of Institutions for Collective Action',
            prediction='Durable groups should develop norms promoting cooperation when under resource pressure.',
            observed={
                'max_bonds': max_bonds,
                'avg_pressure': avg_pressure
            },
            gap='The maximum bond count is insufficient for effective collective action and cooperation despite high resource pressure.',
            severity='high',
            suggested_investigation='examine_social_norms_and_organizational_effectiveness'
        )
    return None


def _broken_windows_theory_compare(history, state):
    avg_bonds = mean(resident['bonds'] for resident in state['residents'])
    avg_pressure = mean(record['pressure'] for record in history)
    avg_energy = mean(record['avg_energy'] for record in history)
    
    # Establish a threshold for bond count related to pressure levels
    bonding_threshold = 0.1
    pressure_threshold = 1.2
    energy_threshold = 2000.0
    
    if avg_bonds < bonding_threshold and avg_pressure > pressure_threshold and avg_energy < energy_threshold:
        return TheoryFinding(
            theory='Broken Windows Theory',
            citation='Wilson, J. Q., & Kelling, G. L. (1982)',
            prediction='In conditions of neglect and resource scarcity, diminished social bonds and increased pressure may further destabilize social cohesion.',
            observed={
                'avg_bonds': avg_bonds,
                'avg_pressure': avg_pressure,
                'avg_energy': avg_energy
            },
            gap='Low average bond count, high population pressure, and low average energy suggest the presence of social disorder and decay, indicating that norms supporting cohesion are failing.',
            severity='critical'
        )
    return None


def _role_theory_compare(history, state):
    role_disruptions = 0
    total_residents = len(state['residents'])
    avg_bonds = mean([resident['bonds'] for resident in state['residents']])

    # Check role fulfillment based on expected bond counts
    expected_bond_threshold = 3  # assuming 3 is an expected practical bond count
    if avg_bonds < expected_bond_threshold:
        role_disruptions = expected_bond_threshold - avg_bonds

    if role_disruptions > 0:
        return TheoryFinding(
            theory='Role Theory',
            citation='Biddle, B. J. (1986)',
            prediction='In contexts of resource scarcity, individuals will struggle to fulfill their social roles, leading to a breakdown in expected behaviors and weakening social cohesion.',
            observed={'avg_bonds': avg_bonds, 'role_disruptions': role_disruptions},
            gap='The average bond count falls below expected thresholds, indicating a potential failure in fulfilling social roles as predicted by Role Theory.',
            severity='high',
            suggested_investigation='examine role expectations vs. actual bonding behavior'
        )
    return None


def _bystander_effect_compare(history, state):
    avg_bond_count = mean([resident['bonds'] for resident in state['residents']])
    avg_pressure = mean([tick['pressure'] for tick in history])

    if avg_bond_count > 1 or avg_pressure < 1:
        return None  # No meaningful gap

    # If high social pressure is present but bonding remains low
    gap = 1 - avg_bond_count  # A measure of how far the observed bonds are from potential maximum
    severity = 'high' if gap > 0.5 else 'moderate'
    return TheoryFinding(
        theory='Bystander Effect',
        citation='Latane, B., & Darley, J. M. (1970)',
        prediction='In situations of acute social pressure and resource scarcity, individuals may hesitate to cooperate, leading to low in-group bonding.',
        observed={'avg_bonds': avg_bond_count, 'avg_pressure': avg_pressure},
        gap=gap,
        severity=severity,
        suggested_investigation='examine social interactions and decision-making under pressure'
    )


def _weak_ties_compare(history, state):
    if not history:
        return None

    total_population = 0
    total_bonds = 0
    total_residents = len(state['residents'])

    for tick in history:
        total_population += tick['pop']
        total_bonds += sum(res['bonds'] for res in state['residents'])

    avg_population = total_population / len(history)
    avg_bonds_per_resident = total_bonds / total_residents if total_residents > 0 else 0

    if avg_bonds_per_resident < 1:
        return TheoryFinding(
            id="weak_ties_insufficient",
            severity="critical",
            title="Insufficient Weak Ties",
            summary="The average number of weak ties in the population is below the threshold needed for resilience against extinction.",
            evidence={
                "avg_bonds_per_resident": avg_bonds_per_resident,
                "avg_population": avg_population
            },
            theory_tags=["social_networking", "weak_ties"]
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
    TheoryLens("Cumulative cultural evolution bottleneck / Tasmanian effect", "Henrich, J. (2004). Demography and cultural evolution: why adaptive cultural systems can be maladaptive. American Antiquity, 69(2), 197-214.",
               "When population size falls below a critical threshold (typically ~250–300 individuals), the pool of knowledgeable individuals becomes too small to maintain complex, multi-step skills, leading to a net loss of adaptive cultural traits over time, even if the population later recovers.",
               _henrich_demographic_cultural_loss_compare),
    TheoryLens("Linguistic niche hypothesis (specifically: population size and language complexity)", "Lupyan, G., & Dale, R. (2010). Language structure is partly determined by social structure. PLoS ONE, 5(1), e8559.",
               "As a population grows and becomes more connected, language should become simpler (less morphological complexity) due to increased proportion of adult learners; here, language_holders should plateau or decline as pop stabilizes high, but instead it may remain constant or track population.",
               _linguistic_niche_compare),
    TheoryLens("Social Disorganization Theory (collective efficacy / social capital)", "Shaw & McKay, Juvenile Delinquency and Urban Areas (1942); Sampson, Raudenbush & Earls, Neighborhoods and Violent Crime (Science, 1997)",
               "In a community where bonds are strong and numerous, collective efficacy (trust + willingness to intervene for the common good) should reduce internal predation and stabilize the population; a high average bond count but no visible raid/predation data suggests latent social capital that could be failing to function as a braking mechanism against deviance.",
               _social_disorganization_compare),
    TheoryLens("Risk Pooling and Mutual Aid (Solidarity Hypothesis)", "Polanyi, Karl. The Great Transformation (1944); Scott, James C. The Moral Economy of the Peasant (1976)",
               "Under chronic resource pressure, agents with low individual calorie reserves will sustain higher average energy than individual foraging alone would allow, because redistribution via social bonds (gifts, sharing) buffers against stochastic shortfalls, producing a flatter, elevated population plateau than pure carrying capacity would enforce.",
               _risk_pooling_and_mutual_aid_compare),
    TheoryLens("Social Network Theory", "Borgatti, S. P., & Halgin, D. S. (2011). Analyzing Affiliation Networks. In The Sage Handbook of Social Network Analysis.",
               "Tightly connected social networks should maintain stability and resilience in resource-challenged environments, leading to lower volatility in population dynamics despite high carrying capacity pressure.",
               _social_network_stability_compare),
    TheoryLens("Social Network Theory", "Granovetter, M. S. (1973). The Strength of Weak Ties.",
               "Communities should show enhanced resilience and resource access through diverse and interconnected social networks, impacting their survival and reproduction rates.",
               _social_network_theory_compare),
    TheoryLens("Social Construction of Reality", "Berger, P. L., & Luckmann, T. The Social Construction of Reality: A Treatise in the Sociology of Knowledge (1966)",
               "The way that populations perceive, interpret, and collectively understand their environment will shape their social practices and population dynamics, potentially stabilizing behaviors even in the face of resource shortages.",
               _social_construction_compare),
    TheoryLens("Social Conflict Theory", "Karl Marx, 'The Communist Manifesto', 1848",
               "The theory predicts that competition over limited resources will create social conflicts, leading to fissures in community cohesion and a potential for societal collapse.",
               _social_conflict_theory_compare),
    TheoryLens("Social Identity Theory", "Tajfel, H., & Turner, J. C. (1979)",
               "In contexts of resource scarcity and population pressure, residents will favor in-group cooperation and bonding over inter-group conflict, thereby stabilizing social structures despite carrying capacity challenges.",
               _social_identity_theory_compare),
    TheoryLens("Social Bond Theory", "Bowlby, J. (1969). Attachment and Loss: Volume I. Attachment.",
               "The strength of social bonds within a population will significantly influence cooperative behavior, resource sharing, and survival rates, leading to stability or instability in the face of resource scarcity.",
               _social_bond_theory_compare),
    TheoryLens("Social Coordination Theory", "Coleman, James S., 'Foundations of Social Theory', 1990",
               "Sustained cooperation among residents can increase overall resilience and adaptability in the face of resource pressures instead of leading to oscillatory population dynamics.",
               _social_coordination_compare),
    TheoryLens("Social Cohesion Theory", "Durkheim, E. (1893), The Division of Labor in Society",
               "In conditions of high resource pressure, individuals will establish and strengthen social ties to promote group survival, leading to increased cooperation and reduced tension within the population.",
               _social_cohesion_compare),
    TheoryLens("Theory of Moral Economy", "E.P. Thompson, 'The Making of the English Working Class', 1963",
               "In contexts of acute resource scarcity, communities will adhere to norms around fairness and mutual aid, preventing the emergence of exploitative behaviors despite high competition for resources.",
               _moral_economy_compare),
    TheoryLens("Collective Efficacy", "Robert J. Sampson, et al., 'Neighborhoods and Violent Crime: A Multilevel Study of Collective Efficacy', 1997",
               "Higher levels of collective efficacy within the community will correspond to increased survivability and population stability, while a lack of collective efficacy will result in collapse and extinction.",
               _collective_efficacy_compare),
    TheoryLens("Self-Determination Theory", "Deci, E. L., & Ryan, R. M. (1985). Intrinsic Motivation and Self-Determination in Human Behavior.",
               "Residents will thrive and reproduce effectively when their innate psychological needs for autonomy, competence, and relatedness are met.",
               _self_determination_theory_compare),
    TheoryLens("Cognitive Load Theory", "Sweller, J. (1988)",
               "As cognitive load increases due to resource scarcity or environmental challenges, social bonding becomes less likely, resulting in fewer social structures and weaker community ties.",
               _cognitive_load_theory_compare),
    TheoryLens("Communal Resource Management Theory", "Ostrom, E. (1990), Governing the Commons: The Evolution of Institutions for Collective Action",
               "In situations of shared resource management, durable groups should develop social norms and organizational strategies that promote cooperation and resource sustainability, particularly in the face of collective stressors.",
               _ostrom_1990_compare),
    TheoryLens("Broken Windows Theory", "Wilson, J. Q., & Kelling, G. L. (1982)",
               "In environments characterized by neglect and limited resources, small signs of disorder can lead to increased social decay and diminished social bonds, exacerbating the population's challenges in cohesion and resilience.",
               _broken_windows_theory_compare),
    TheoryLens("Role Theory", "Biddle, B. J. (1986). Role Theory: Expectations, Identities, and Behaviors.",
               "In contexts of resource scarcity, individuals will struggle to fulfill their social roles, leading to a breakdown in expected behaviors and weakening social cohesion.",
               _role_theory_compare),
    TheoryLens("Bystander Effect", "Latane, B., & Darley, J. M. (1970)",
               "In situations of acute social pressure and resource scarcity, individuals may hesitate to cooperate or bond with others, leading to lower rates of in-group cooperation even when group survival is at stake.",
               _bystander_effect_compare),
    TheoryLens("Weak Ties Theory", "Granovetter, M. S. (1973). The Strength of Weak Ties.",
               "The theory predicts that a society with a high number of weak social ties will exhibit greater resilience and adaptability, which can prevent extinction even in the face of adverse conditions.",
               _weak_ties_compare),
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
