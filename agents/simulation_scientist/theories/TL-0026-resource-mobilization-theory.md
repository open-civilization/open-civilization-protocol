# TL-0026: Resource Mobilization Theory

**Citation:** Tilly, C. (1978)

**Domain:** sociology

**Prediction:** Under high carrying-capacity pressure, social movements will emerge when residents identify shared grievances and mobilize resources toward collective action to improve their situation.

**Discovered:** 2026-07-06T02:54:43.730101+00:00

## Write-up

Resource Mobilization Theory posits that social movements and collective actions arise from the organization and mobilization of resources in response to grievances faced by a community. It suggests that when individuals perceive a shared problem—especially under conditions of resource scarcity or high pressure—they will coordinate efforts to effect change, thereby improving their social conditions. This theory emphasizes the role of social networks, the availability of resources, and the means to organize rather than just individual motivations or social awareness.

In the context of the simulation, the observed behavior shows high population pressure alongside low rates of bonding and reproduction, which suggests a failure to mobilize collectively despite the clear environmental challenges. According to the theory, one would expect residents to form stronger bonds and potentially mobilize for collective efforts as a reaction to high pressure. Confirming evidence would be an increase in the number of bonds or a higher birth rate despite resource constraints, indicating organizing behavior around shared grievances, while disconfirming observations would be a persistent low level of bonding and births under high pressure.

This gap indicates that, despite facing chronic carrying-capacity pressures, the simulated residents may not be recognizing their common plight or may lack the resources necessary for effective organization and mobilization, which could hinder their ability to adapt to environmental stresses.

## Implementation

```python
def _resource_mobilization_compare(history, state):
    # Extract relevant metrics from the history
    pressures = [tick['pressure'] for tick in history]
    avg_pressure = mean(pressures)
    # Check for mobilization indicators
    born_counts = [tick['births'] for tick in history]
    avg_births = mean(born_counts)
    avg_bonds = state['residents'][0]['bonds'] if state['residents'] else 0
    # There should be a significant number of births and bonds in response to pressure
    if avg_pressure > 1.2 and (avg_births < 5 and avg_bonds < 1):
        return TheoryFinding(
            run=2,
            theory='Resource Mobilization Theory',
            citation='Tilly, C. (1978)',
            prediction='Under high carrying-capacity pressure, social movements will emerge when residents identify shared grievances and mobilize resources toward collective action to improve their situation.',
            observed={'avg_pressure': avg_pressure, 'avg_births': avg_births, 'avg_bonds': avg_bonds},
            gap='Low evidence of social movement mobilization despite high pressure.',
            severity='high',
            suggested_investigation='investigate residents’ grievances and potential collective actions'
        )
    return None
```
