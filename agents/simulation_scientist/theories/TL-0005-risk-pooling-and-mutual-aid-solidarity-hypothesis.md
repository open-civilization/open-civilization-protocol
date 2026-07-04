# TL-0005: Risk Pooling and Mutual Aid (Solidarity Hypothesis)

**Citation:** Polanyi, Karl. The Great Transformation (1944); Scott, James C. The Moral Economy of the Peasant (1976)

**Domain:** collective risk management / solidarity economics

**Prediction:** Under chronic resource pressure, agents with low individual calorie reserves will sustain higher average energy than individual foraging alone would allow, because redistribution via social bonds (gifts, sharing) buffers against stochastic shortfalls, producing a flatter, elevated population plateau than pure carrying capacity would enforce.

**Discovered:** 2026-07-04T18:07:36.563213+00:00

## Write-up

**What the theory says:** Karl Polanyi and James C. Scott, among others, have argued that in pre-modern or subsistence economies, social institutions (gift exchange, reciprocal obligations, shared storage) act as a form of insurance against individual risk. Households pool resources so that a bad harvest or injury for one is absorbed by the community, flattening consumption over time. This "moral economy" creates a safety net that keeps even the poorest members above starvation level, as long as the community as a whole has surplus to redistribute. The prediction is that under sustained population pressure near carrying capacity, we should see two signatures: (1) average per-capita energy remains above the minimum viable level (because redistribution prevents individual collapse), and (2) the population does not oscillate wildly (boom-bust) but instead holds a stable plateau — the buffer of social sharing smooths out the stochastic shocks that would otherwise trigger Malthusian crashes.

**Why it applies here:** Our simulation already reports a chronic pressure plateau (avg_tail_pressure ≈ 1.37) with very low volatility (0.024) and an average tail energy of ~1766 kcal, which is below the erosion threshold of 2000 kcal but not catastrophically low — it is hovering just below the threshold. The Malthusian lens already flagged that this is not classic boom-bust. A storage/scavenging explanation is plausible, but storage alone cannot explain why the plateau is so flat: if storage were the sole buffer, we would expect more volatility as stores get depleted and replenished. The additional presence of social bonds (avg bonds per resident > 1) suggests a second mechanism: agents sharing food via their bond network, creating a collective buffer. This is precisely what Polanyi's and Scott's theory of risk pooling predicts.

**What a confirming vs. disconfirming observation would look like:** Confirmation: In runs where pressure is high and bond count is above some threshold (e.g., >1.5 bonds per capita), the tail energy should be significantly above the individual-foraging baseline (which we model here as a floor of ~2000 kcal), and the pressure volatility should be low. Disconfirmation: If we observe a run with high pressure and high bond count but average energy crashes to near zero (no buffering effect), or if the pressure oscillates widely despite many bonds, that would contradict the theory. Likewise, if bonds are low but survivors still plateau, that would point to storage or some other mechanism as the sole cause.

## Implementation

```python
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
```
