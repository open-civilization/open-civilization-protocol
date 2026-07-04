# TL-0004: Social Disorganization Theory (collective efficacy / social capital)

**Citation:** Shaw & McKay, Juvenile Delinquency and Urban Areas (1942); Sampson, Raudenbush & Earls, Neighborhoods and Violent Crime (Science, 1997)

**Domain:** sociology / criminology

**Prediction:** In a community where bonds are strong and numerous, collective efficacy (trust + willingness to intervene for the common good) should reduce internal predation and stabilize the population; a high average bond count but no visible raid/predation data suggests latent social capital that could be failing to function as a braking mechanism against deviance.

**Discovered:** 2026-07-04T15:01:45.495206+00:00

## Write-up

Social Disorganization Theory, originally formulated by Shaw & McKay (1942) in their study of juvenile delinquency in urban areas, posits that neighborhood-level structural factors (poverty, residential instability, ethnic heterogeneity) undermine the ability of a community to exercise informal social control. The theory was refined by Sampson, Raudenbush, and Earls (1997) into the concept of ‘collective efficacy’ — a combination of social cohesion and shared expectations for intervention. In an emergent civilization simulation, the presence of strong interpersonal bonds (measured by average bonds per resident) should theoretically enhance collective efficacy and reduce internal conflict, raiding, or resource predation.

In this simulation run, the average bond count appears moderately high (based on inspection of the per-run data) and shows low inequality across residents. Despite this, the population history may reveal residual volatility (fluctuations beyond what would be expected from resource cycles alone) that social organization should have suppressed. If such volatility exists, it indicates a gap: the bonds are present but are not functioning as effective social control mechanisms — perhaps because the simulation lacks formal mechanisms for shared sanctioning, or because bonds are purely relational without any embedded trust or reputation effects.

A confirming observation would be that high bond density and low bond inequality correlate with very low population variance (stable carrying capacity attainment) and no visible raiding. A disconfirming observation (the gap) would be high bonds with moderate volatility or signs of internal conflict (e.g., high death rates, gini spikes). This would suggest that the simulation's bonding mechanic is insufficiently connected to a ‘collective action’ or ‘policing’ mechanism — calling for a theoretical lens from criminology or social capital theory rather than purely economic or biological explanations.

## Implementation

```python
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
```
