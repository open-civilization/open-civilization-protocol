# TL-0009: Social Conflict Theory

**Citation:** Karl Marx, 'The Communist Manifesto', 1848

**Domain:** sociology

**Prediction:** The theory predicts that competition over limited resources will create social conflicts, leading to fissures in community cohesion and a potential for societal collapse.

**Discovered:** 2026-07-05T02:52:39.547851+00:00

## Write-up

Social Conflict Theory, originating from the works of Karl Marx, posits that society is in a state of perpetual conflict due to competition for limited resources. In this context, groups within a society vie for wealth and power, which can lead to tension and breakdowns in community cohesion. Particularly in scenarios where resources are scarce, the theory highlights how social stratification and resource scarcity can exacerbate divisions among community members.

In the simulation data provided, there is an observable chronic pressure on the population related to resource carrying capacity. Given this dynamic, one would expect that as resources become increasingly strained, community bonds could weaken due to competing interests, thus leading to social conflict. If, however, the average number of social bonds among residents at the end of the simulation is above a certain threshold relative to the population, then this would confirm the theory's prediction that cohesive structures can maintain stability even under pressure.

A confirming observation for this theory would show high average social bonds despite high pressure levels, indicating a resilient community structure. Conversely, if the average bonds were low alongside high pressure, it would suggest that social cohesion is breaking down, aligning with the expectations set out by Social Conflict Theory. This divergence between theoretical prediction and observed behavior highlights an important aspect of social dynamics in the simulation framework.

## Implementation

```python
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
```
