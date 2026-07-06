# TL-0020: Role Theory

**Citation:** Biddle, B. J. (1986). Role Theory: Expectations, Identities, and Behaviors.

**Domain:** sociology

**Prediction:** In contexts of resource scarcity, individuals will struggle to fulfill their social roles, leading to a breakdown in expected behaviors and weakening social cohesion.

**Discovered:** 2026-07-05T23:40:17.260960+00:00

## Write-up

Role Theory is a sociological perspective that examines how individuals function within social structures and roles. It posits that individuals have certain expectations and behaviors associated with their social roles, which can significantly impact their interactions and relationships within a society. When resources are scarce, as suggested in this simulation, individuals may find it difficult to fulfill their roles effectively. This can lead to disruptions in expected social behaviors, which could compromise social cohesion and stability.

In the present case, the observed low average bond count amidst high population pressure indicates that residents are not fulfilling their expected roles as social beings. If the theory holds true, it would suggest that with more social stress (from resource scarcity), the ability of residents to forge and maintain bonds diminishes, which exacerbates social divisions rather than reinforcing cooperation. This would be contrary to the predictions of other bonding theories, such as Social Identity Theory, which might suggest that in-group bonding should increase under pressure.

A confirming observation regarding Role Theory would be a further decrease in average bonds as resource conditions worsen or as population pressure increases, indicating a growing inability of individuals to effectively interact or fulfill their roles. Conversely, if average bonds were to increase despite high pressure, it would suggest that residents are finding ways to adapt, thus challenging the predictions of this theory.

## Implementation

```python
def _role_theory_compare(history, state):
    role_disruptions = 0
    total_residents = len(state['residents'])
    avg_bonds = mean([resident['bonds'] for resident in state['residents']])

    # Check role fulfillment based on expected bond counts
    expected_bond_threshold = 3  # assuming 3 is an expected practical bond count
    if avg_bonds < expected_bond_threshold:
        role_disruptions = expected_bond_threshold - avg_bonds

    if role_disruptions > 0:
        return TheoryFinding(
            theory='Role Theory',
            citation='Biddle, B. J. (1986)',
            prediction='In contexts of resource scarcity, individuals will struggle to fulfill their social roles, leading to a breakdown in expected behaviors and weakening social cohesion.',
            observed={'avg_bonds': avg_bonds, 'role_disruptions': role_disruptions},
            gap='The average bond count falls below expected thresholds, indicating a potential failure in fulfilling social roles as predicted by Role Theory.',
            severity='high',
            suggested_investigation='examine role expectations vs. actual bonding behavior'
        )
    return None
```
