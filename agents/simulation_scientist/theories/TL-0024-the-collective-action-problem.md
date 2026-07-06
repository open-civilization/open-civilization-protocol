# TL-0024: The Collective Action Problem

**Citation:** Olson, M. (1965). The Logic of Collective Action.

**Domain:** sociology

**Prediction:** The theory predicts that individuals within a group will struggle to coordinate and cooperate in a way that maximizes the collective benefit due to competing individual interests, leading to resource depletion and possibly extinction.

**Discovered:** 2026-07-06T01:33:50.079417+00:00

## Write-up

The Collective Action Problem, as articulated by Mancur Olson in 1965, addresses the challenges that groups face when attempting to achieve shared goals. It posits that individuals often prioritize their own immediate needs over the collective good, particularly when the benefits of cooperation cannot be assured. This can lead to scenarios where attempts at communal resource management fail, potentially resulting in resource depletion and the collapse of social groups.

In the context of the simulation, the observed extinction events suggest a possible failure in coordination among the residents. If the average number of bonds is low, it indicates a lack of strong collaborative ties among individuals, which is crucial for successful group survival and resource use. Essentially, while population size may initially appear stable, without effective cooperation, the collective can diminish rapidly.

Confirming evidence for this theory would include signs of diminishing populations alongside low social bond metrics, indicating that individual interests were overpowering communal efforts. Conversely, if strong social bonds develop and the population stabilizes, it could suggest that coordination efforts are indeed succeeding, contradicting Olson's predictions.

## Implementation

```python
def _collective_action_problem_compare(history, state):
    if not history:
        return None

    total_population = sum(h['pop'] for h in history)
    last_population = history[-1]['pop']
    avg_bonds = sum(r['bonds'] for r in state['residents']) / len(state['residents']) if state['residents'] else 0

    # Check for signs of coordination failure
    if last_population < total_population and avg_bonds < 1:
        return TheoryFinding(
            domain='sociology',
            theory_name='The Collective Action Problem',
            citation='Olson, M. (1965). The Logic of Collective Action.',
            prediction='The theory predicts that individuals within a group will struggle to coordinate and cooperate in a way that maximizes the collective benefit due to competing individual interests, leading to resource depletion and possibly extinction.',
            function_name='_collective_action_problem_compare',
            function_code=_collective_action_problem_compare.__code__.
            co_code
        )

    return None
```
