# TL-0001: Risky knowledge / extinction of beneficial traits (cultural drift & forgetting)

**Citation:** Henrich, The Secret of Our Success (2015); Boyd & Richerson, Culture and the Evolutionary Process (1985)

**Domain:** anthropology / cultural evolution

**Prediction:** When a beneficial skill (e.g., farming, herding, writing) is held by few individuals (low 'knowledge_ratio'), random death events should cause stochastic loss of that skill in the population, leading to a downward drift in the count of knowledge holders over time — especially at low population sizes.

**Discovered:** 2026-07-03T14:03:22.974894+00:00

## Write-up

**Theory: Risky knowledge / extinction of beneficial traits (cultural drift).**

Anthropologists Robert Boyd, Peter Richerson, and Joseph Henrich have shown that in small populations, beneficial cultural knowledge (e.g., how to farm, build shelters, or use fire) is vulnerable to stochastic loss simply because the few individuals who carry it may die before transmitting it. This is analogous to genetic drift but far more rapid because culture can be lost in one generation if no learner replaces a deceased expert. The theory predicts that any skill held by a small fraction of the population (typically <10%) will exhibit negative drift in holder count over time, unless high-fidelity social learning mechanisms (teaching, imitation, language) buffer against loss.

**Why this applies to the simulation.**

The provided run data shows `knowledge_holders`, `farmer_holders`, `herder_holders`, and other skill counts. These skills are clearly beneficial (they increase food production or survival), yet the mechanics of transmission are not described in the data schema as having explicit copying error rates or active teaching. If the population remains small and a skill like farming is held by only a handful of residents (say, <10% of the population), random deaths of those holders should cause the count to fluctuate and eventually drift toward zero. The ad hoc findings and Malthusian lens already note stable overshoot, but they do not examine whether knowledge is being faithfully retained across generations.

**Confirming vs. disconfirming observation.**

A confirming observation would be: for a skill with low holder ratio (e.g., <5% of the population over many ticks), the holder count shows a persistent negative linear trend with high variance, and occasionally the skill disappears entirely (holder count goes to zero and never recovers). A disconfirming observation would be: even with very few holders, the count remains stable or increases over time, implying that either transmission is perfect or the skill is somehow protected from the death of its bearers (e.g., stored in artifacts or writing). The current run shows `farmer_holders` at a low ratio with a negative slope, suggesting the model may lack a robust cultural inheritance mechanism, allowing valuable knowledge to be lost — a classic case of the 'extinction of beneficial traits' described by Henrich.

## Implementation

```python
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
```
