# TL-0022: Weak Ties Theory

**Citation:** Granovetter, M. S. (1973). The Strength of Weak Ties.

**Domain:** sociology

**Prediction:** The theory predicts that a society with a high number of weak social ties will exhibit greater resilience and adaptability, which can prevent extinction even in the face of adverse conditions.

**Discovered:** 2026-07-05T23:49:38.819589+00:00

## Write-up

# Weak Ties Theory

Weak Ties Theory, proposed by sociologist Mark Granovetter in 1973, posits that social connections not only facilitate information flow but that weak ties—those less robust connections between individuals—are crucial for wider information networks. They connect disparate social groups, enabling the exchange of novel ideas and resources that might not occur within tightly-knit groups where strong ties dominate. In contexts where collective survival and adaptability are paramount, the presence of weak ties can significantly bolster resilience against external pressures and facilitate cultural evolution.

In the context of the simulation, the observations indicate a complete extinction of the population, suggesting that the social connections within the society are inadequate for sustainable cohesion and survival. If the average number of bonds per resident is low, it signifies a lack of weak ties that could potentially provide critical adaptive responses to changing conditions. The absence of these ties may result in a failure to share resources, information, and support, ultimately leading to extinction.

A confirming observation would present a society that maintains a minimum average of weak ties per resident, facilitating the population's persistence despite resource challenges or shifting environmental factors. Conversely, should the simulation reveal evidence of strong social cohesion but a lack of weak ties, it would contradict the expectations of Weak Ties Theory, pointing to an oversimplified understanding of social dynamics within the simulated civilization.

## Implementation

```python
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
```
