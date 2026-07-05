# TL-0014: Theory of Moral Economy

**Citation:** E.P. Thompson, 'The Making of the English Working Class', 1963

**Domain:** sociology

**Prediction:** In contexts of acute resource scarcity, communities will adhere to norms around fairness and mutual aid, preventing the emergence of exploitative behaviors despite high competition for resources.

**Discovered:** 2026-07-05T07:39:15.384998+00:00

## Write-up

The Theory of Moral Economy, articulated by E.P. Thompson, posits that communities in resource-constrained environments will prioritize fairness and mutual assistance, thereby preventing exploitation and conflict. Thompson argues that historical instances of resource scarcity reveal a strong adherence to communal norms that transcend individualistic or opportunistic behaviors. These norms ensure that resource distribution is conducted equitably, providing a buffer against social fragmentation and unrest.

In the context of the simulation, despite the observed high population pressure and low average bond count, the lack of adherence to communal norms raises a significant gap in the operation of the emerging civilization. The theory predicts that in the face of scarcity, we should see enhanced solidarity and bonding behaviors as residents aim to maintain social stability through mutual support. A confirming observation would show a higher average bond count alongside a decline in resource competition, effectively strengthening social ties and cooperation. Conversely, in a disconfirming scenario, we find a community where bonds diminish amidst rising pressure and inequality, which is what the current data suggests.

These findings invite exploration into the narratives around resource allocation and how they shape behavioral outcomes within the community. By examining stockpiling behaviors, cultural norms regarding sharing, and the willingness to enforce social bonds, researchers can better understand the mechanisms at play in these emergent systems. This avenue of inquiry is critical for comprehending why a civilization under pressure may not mobilize the cooperative spirit predicted by moral economy theory.

## Implementation

```python
def _moral_economy_compare(history, state):
    total_bonds = sum(resident['bonds'] for resident in state['residents'])
    avg_bonds = total_bonds / len(state['residents']) if state['residents'] else 0
    avg_pressure = mean(h['pressure'] for h in history)
    gini = mean(h['gini'] for h in history)

    # Evaluate if community norms of fairness are eroding
    if avg_bonds < 1 and avg_pressure > 1 and gini > 0.3:
        return TheoryFinding(
            theory='Theory of Moral Economy',
            citation='E.P. Thompson, The Making of the English Working Class, 1963',
            prediction='In contexts of acute resource scarcity, communities will adhere to norms around fairness and mutual aid, preventing the emergence of exploitative behaviors despite high competition for resources.',
            observed={'avg_bonds': avg_bonds, 'avg_pressure': avg_pressure, 'avg_gini': gini},
            gap='The observed bond count is low, indicating a failure of communal obligation and fair resource distribution despite high resource pressure and inequality, contrary to the prediction of the Theory of Moral Economy.',
            severity='high',
            suggested_investigation='assess_resource_distribution_narratives_and_norms'
        )
    return None
```
