# TL-0006: Social Network Theory

**Citation:** Borgatti, S. P., & Halgin, D. S. (2011). Analyzing Affiliation Networks. In The Sage Handbook of Social Network Analysis.

**Domain:** sociology

**Prediction:** Tightly connected social networks should maintain stability and resilience in resource-challenged environments, leading to lower volatility in population dynamics despite high carrying capacity pressure.

**Discovered:** 2026-07-05T02:44:20.767357+00:00

## Write-up

Social Network Theory is primarily concerned with how the connections between individuals in a community impact their collective behavior and resilience. In environments with limited resources, theories suggest that tightly knit social networks can buffer communities against the shocks of resource scarcity. Well-established bonds can facilitate resource sharing, mutual aid, and the transmission of survival knowledge crucial in times of crisis. This theory is particularly relevant to the observed high population pressure, as it raises questions about the resilience of social structures in the face of external challenges.

In the context of the simulation, the presence of significant resource pressure alongside low volatility in population dynamics could indicate a failure of communities to leverage their social networks effectively. If the residents maintain close bonds but still experience high fluctuations in population metrics, it suggests that their networks may not be functioning optimally. Perhaps individuals are connected but do not share resources effectively, or there may be barriers to collaboration that are not visible through aggregate bond counts alone.

A confirming observation would be a stable population with minimal fluctuations despite high carrying capacity pressure, indicating effective social network functioning. A disconfirming observation would be high volatility in population metrics, suggesting that social connections are weak or ineffective in resource-sharing, thus undermining the theoretical predictions of Social Network Theory.

## Implementation

```python
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
```
