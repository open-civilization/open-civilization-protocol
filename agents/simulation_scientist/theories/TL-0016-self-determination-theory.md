# TL-0016: Self-Determination Theory

**Citation:** Deci, E. L., & Ryan, R. M. (1985). Intrinsic Motivation and Self-Determination in Human Behavior.

**Domain:** sociology

**Prediction:** Residents will thrive and reproduce effectively when their innate psychological needs for autonomy, competence, and relatedness are met.

**Discovered:** 2026-07-05T11:28:14.767678+00:00

## Write-up

Self-Determination Theory (SDT) emphasizes the importance of meeting three innate psychological needs: autonomy, competence, and relatedness for optimal functioning and growth. In social and educational contexts, this theory posits that when individuals feel supported in these areas, they demonstrate higher engagement, improved well-being, and enhanced long-term outcomes. Conversely, unmet psychological needs can lead to disconnection, lower morale, and even systematic failure of social structures.

In the context of an emergent civilization simulation, observing a complete collapse to extinction suggests that the residents may not have had their psychological needs met. For instance, conditions where individuals could express autonomy through decisions, achieve competence in their roles, and forge meaningful relationships would foster stronger communities and a more sustainable population. The data indicates zero population and no recorded health or energy levels, reinforcing that whatever potential existed in skills and knowledge was not utilized effectively.

Confirming observations would include a gradually increasing population alongside improvements in health and energy metrics, reflecting thriving conditions. On the contrary, if metrics show persistently low population growth or high mortality rates linked to insufficient social bonding and support systems, this would disconfirm the theory’s core predictions. Effective interventions could later demonstrate an increase in population and vitality if psychological needs are subsequently addressed.

## Implementation

```python
def _self_determination_theory_compare(history, state):
    # Check the last tick for population data
    last_tick = history[-1] if history else None
    if last_tick:
        total_population = last_tick['pop']
        avg_health = last_tick['avg_health']
        avg_energy = last_tick['avg_energy']
        bonds_count = sum(resident['bonds'] for resident in state['residents'])
        # Determine the relative health and energy states
        if (total_population == 0) or (avg_health < 0.5 and avg_energy < 0.5):
            return TheoryFinding(
                name='Self-Determination Theory Gap',
                finding='A significant gap exists as the population failed to thrive, indicating potential unmet psychological needs among residents.',
                evidence={
                    'total_population': total_population,
                    'avg_health': avg_health,
                    'avg_energy': avg_energy,
                    'bonds_count': bonds_count
                }
            )
    return None
```
