# TL-0021: Bystander Effect

**Citation:** Latane, B., & Darley, J. M. (1970)

**Domain:** sociology

**Prediction:** In situations of acute social pressure and resource scarcity, individuals may hesitate to cooperate or bond with others, leading to lower rates of in-group cooperation even when group survival is at stake.

**Discovered:** 2026-07-05T23:49:04.602695+00:00

## Write-up

The bystander effect is a social psychological phenomenon in which individuals are less likely to offer help in emergency situations when other people are present. In essence, the presence of more individuals leads to a diffusion of responsibility, where individuals feel less compelled to act, wrongly assuming that someone else will intervene. This theory can be relevant in the context of your simulation, where resource scarcity and high population pressure could create situations where individuals are reluctant to form bonds and cooperate out of fear of jeopardizing their own survival.

In the current simulation outcomes, despite predictions from Social Identity Theory suggesting a preference for in-group cooperation under pressure, the aggregated bond count shows significantly low averages when social pressure is high. This contradicts the expectation that populations would rally together in the face of adversity, indicating that individual hesitation influenced by perceptions of social pressure could be a critical factor in this context.

Observations that would confirm the predictions of the bystander effect would include further reductions in in-group bonding rates as average pressure increases. Conversely, if bonding rates were to increase in the face of higher social pressures, it would suggest that either the bystander effect is not a significant consideration, or other factors are outweighing its impact. Understanding these patterns could provide deeper insights into the mechanisms driving social behavior in resource-constrained environments.

## Implementation

```python
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
```
