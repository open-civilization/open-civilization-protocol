# TL-0015: Collective Efficacy

**Citation:** Robert J. Sampson, et al., 'Neighborhoods and Violent Crime: A Multilevel Study of Collective Efficacy', 1997

**Domain:** sociology

**Prediction:** Higher levels of collective efficacy within the community will correspond to increased survivability and population stability, while a lack of collective efficacy will result in collapse and extinction.

**Discovered:** 2026-07-05T10:28:09.762179+00:00

## Write-up

# Collective Efficacy Theory

Collective efficacy refers to the social cohesion among neighbors combined with their willingness to intervene on behalf of the common good. Sampson and colleagues proposed that communities characterized by high collective efficacy experience lower levels of violence and higher overall social stability. In this model, a community's ability to maintain internal order and support each other's welfare is crucial for its long-term survival.

In the context of the observed simulation behavior, the extinction rate of 1.0 and a peak population of 0 suggest a significant lack of social cohesion. The absence of interpersonal bonds among residents indicates that the community is unable to mobilize collective action to stave off collapse. This relates to the idea that without such social structures, members are less likely to assist each other in critical situations, leading to a higher likelihood of extinction.

Confirming this theory's applicability would entail finding instances where increased social bonds corresponded with population growth or stability in later runs. Conversely, data showcasing consistent low bond counts accompanied by drastic population declines supports the theory's prediction about the importance of collective efficacy in the simulation's social dynamics.

## Implementation

```python
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
```
