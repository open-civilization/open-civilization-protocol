# TL-0012: Social Coordination Theory

**Citation:** Coleman, James S., 'Foundations of Social Theory', 1990

**Domain:** sociology

**Prediction:** Sustained cooperation among residents can increase overall resilience and adaptability in the face of resource pressures instead of leading to oscillatory population dynamics.

**Discovered:** 2026-07-05T04:49:57.605417+00:00

## Write-up

Social Coordination Theory, as posited by James S. Coleman, addresses how social structures and networks facilitate cooperation among individuals, thereby affecting collective outcomes. In the context of the emergent-civilization sandbox, this theory applies especially to how residents manage mutual resources under pressure. The absence of effective social bonds amidst high population pressure invites instability, contrary to expected dynamics suggested by Malthusian principles.

In scenarios where social bonds are robust, residents might demonstrate a collective resilience that averts oscillations characteristic of Malthusian dynamics. If the average bonds are low but the pressure remains high, it suggests that residents are not coordinating effectively, potentially leading to an unsustainable equilibrium rather than a healthy population dynamic. Conversely, if residents can maintain high bonds, we would expect to observe coherent resource management and potentially even population flourishing despite pressures.

Thus, observing low average bonds in conjunction with significant resource pressure could describe a critical gap highlighting the need for a new lens. It indicates that rather than oscillatory behaviors in response to resource dynamics, residents are experiencing stability at potentially perilous levels of cooperation failure.

## Implementation

```python
def _social_coordination_compare(history, state):
    avg_bonds = mean([resident['bonds'] for resident in state['residents']])
    pressure = median([h['pressure'] for h in history])
    avg_pressure = mean([h['pressure'] for h in history])
    bond_threshold = 5  # Hypothetical threshold for effective coordination
    if avg_bonds < bond_threshold and avg_pressure > 1.2:
        return TheoryFinding(
            theory='Social Coordination Theory',
            citation='Coleman, James S., Foundations of Social Theory, 1990',
            prediction='Lower levels of social bonds relative to high resource pressure should lead to decreased cooperation and higher instability.',
            observed={
                'avg_bonds': avg_bonds,
                'avg_pressure': avg_pressure,
            },
            gap='The residents exhibit low levels of social bonding which are insufficient to mitigate the negative impacts of high resource pressure, leading to an equilibrium without oscillation in the population dynamics.',
            severity='high',
            suggested_investigation='social_bonding_effect_on_population_stability'
        )
    return None
```
