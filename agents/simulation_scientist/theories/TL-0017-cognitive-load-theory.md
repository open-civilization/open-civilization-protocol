# TL-0017: Cognitive Load Theory

**Citation:** Sweller, J. (1988)

**Domain:** cognitive anthropology

**Prediction:** As cognitive load increases due to resource scarcity or environmental challenges, social bonding becomes less likely, resulting in fewer social structures and weaker community ties.

**Discovered:** 2026-07-05T13:36:10.372968+00:00

## Write-up

Cognitive Load Theory, articulated by John Sweller in 1988, posits that the cognitive capacity of individuals is limited and that increased cognitive load can hinder learning and performance outcomes. In contexts of resource scarcity or environmental stress, the cognitive demands on individuals escalate. This theory can be applied to social bonding in simulated communities, where an overloaded cognitive state might detract from residents' ability to establish and maintain social connections.

In this simulation, Cognitive Load Theory suggests that as the pressure on individuals increases—possibly due to scarce resources or survival challenges—cognitive resources become overstretched. Under such conditions, individuals might find themselves too stressed or busy tending to immediate survival needs (like foraging for food) to invest time or energy into forming social bonds. If high pressure results in low average bonds, it would support this theory; conversely, if social bonds were formed despite high resource pressures, it would contradict the predictions of this theory.

A confirming observation would show that during periods of high resource pressure or environmental stress, the average bond count significantly decreases, supporting the idea that overloaded cognitive capacity limits social cohesion. Disconfirming observations might reveal robust social bonding despite high pressures, indicating that other factors could encourage bonding, challenging the application of this theory in such contexts.

## Implementation

```python
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
```
