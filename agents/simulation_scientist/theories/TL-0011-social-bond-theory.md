# TL-0011: Social Bond Theory

**Citation:** Bowlby, J. (1969). Attachment and Loss: Volume I. Attachment.

**Domain:** sociology

**Prediction:** The strength of social bonds within a population will significantly influence cooperative behavior, resource sharing, and survival rates, leading to stability or instability in the face of resource scarcity.

**Discovered:** 2026-07-05T04:27:52.369056+00:00

## Write-up

Social Bond Theory, as articulated by John Bowlby in his seminal work on attachment, emphasizes the importance of social bonds and relationships in human behavior. Specifically, this theory posits that the strength and quality of social connections influence cooperative behavior within groups. Communities with strong bonds are more likely to tackle shared challenges collectively, share resources effectively, and provide mutual support in times of scarcity. Conversely, weak social bonds can lead to fragmentation, where individuals prioritize personal survival over communal well-being.

In the context of the simulation, the observed low levels of aggregate social bonds could shed light on why the population remains stable yet under pressure. Despite being above carrying capacity, the lack of substantial bonds may indicate a missed opportunity for collective action that could improve resource management and stabilize population dynamics. A confirming observation would entail a community where average bond counts are high, potentially correlating with better health and energy metrics, suggesting effective cooperation. In contrast, a disconfirming observation would document a strong community yet still beholden to high pressures and low vitality, challenging the utility of bonds in managing scarcity.

By applying Social Bond Theory, we can explore the interplay between resource management and social dynamics, providing crucial insights for improving community resilience in future runs. The resulting predictions could help refine the simulation's mechanics, enhancing the complexity of human interactions and their consequences in emergent civilization scenarios.

## Implementation

```python
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
```
