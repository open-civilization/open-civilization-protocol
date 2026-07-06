# TL-0025: Group Cohesion Theory

**Citation:** Leonard B. Borkowski, 'Group Cohesion: Theoretical and Practical Perspectives', 1983

**Domain:** sociology

**Prediction:** Greater cohesion among residents would lead to more successful survival outcomes, while lack of cohesion correlates with higher extinction rates.

**Discovered:** 2026-07-06T01:34:57.700567+00:00

## Write-up

Group Cohesion Theory posits that the strength of interpersonal bonds within a group significantly influences its overall stability and success. When individuals feel a sense of belonging and commitment to one another, they are more likely to cooperate, share resources, and support one another in times of crisis. Borkowski's work emphasizes that cohesive groups can better navigate challenges such as resource scarcity, conflict, and external threats.

In the context of the simulation, the observed data showing a peak and final population of zero suggests that any attempts to establish social structures or bonds between residents were insufficient to prevent extinction. A crucial aspect to investigate would be the average bond count among residents—low levels may indicate disunity, leading to increased vulnerability and failure to act collectively during critical periods. If residents were found to have higher bond counts, this would contradict the observed extinction.

A confirming observation would show a higher average bond count correlating with increased population stability, while a disconfirming one would exemplify significant fatalities despite strong bonds. Thus, the cohesion among residents plays a vital role in determining their long-term survival prospects within the sandbox environment.

## Implementation

```python
def _group_cohesion_compare(history, state):
    if not history or state['residents'] == []:
        return None
    cohort_count = len(state['residents'])
    bond_counts = [resident['bonds'] for resident in state['residents']]
    avg_bond_count = mean(bond_counts) if bond_counts else 0
    cohesion_score = avg_bond_count / cohort_count if cohort_count > 0 else 0
    if cohesion_score < 0.5:
        return TheoryFinding(
            theory='Group Cohesion Theory',
            description='Low average bond count indicates poor group cohesion, leading to increased risks of extinction.',
            evidence={'avg_cohesion_score': cohesion_score},
            gap_behavior='The observed population collapsed to extinction with insufficient social bonds, contradicting predictions of higher survival with greater cohesion.'
        )
    return None
```
