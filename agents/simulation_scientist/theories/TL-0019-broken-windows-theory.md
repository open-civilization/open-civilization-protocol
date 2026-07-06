# TL-0019: Broken Windows Theory

**Citation:** Wilson, J. Q., & Kelling, G. L. (1982)

**Domain:** sociology

**Prediction:** In environments characterized by neglect and limited resources, small signs of disorder can lead to increased social decay and diminished social bonds, exacerbating the population's challenges in cohesion and resilience.

**Discovered:** 2026-07-05T21:49:32.002735+00:00

## Write-up

The Broken Windows Theory posits that visible signs of disorder and neglect in a community can lead to a breakdown in social norms and an increase in crime and disorder. Originally applied to urban crime situations, the theory suggests that environments perceived as neglected or chaotic can exacerbate feelings of insecurity and lack of cohesion among community members. This theory is highly relevant for contexts where population pressures and resource scarcity could further stress social dynamics.

In the simulation, the recent findings indicate a low average bond count amidst critical population pressure and dangerously low energy levels. Such conditions can be interpreted as signs of social decay—residents may be struggling with the immediate survival needs that hinder their ability to form and maintain social bonds. In this context, the Broken Windows Theory provides a lens to understand how social cohesion is being eroded and its implications for the society's ability to respond to external pressures.

A confirming observation would show a continuous decline in bond formation alongside rising pressures and low energy levels, indicating that residents feel increasingly isolated and unable to cooperate through social structures. Conversely, if population pressure decreases or energy levels rise while maintaining or improving bond counts, it would suggest a more stable environment, challenging the predictions made by the Broken Windows Theory in this scenario.

## Implementation

```python
def _broken_windows_theory_compare(history, state):
    avg_bonds = mean(resident['bonds'] for resident in state['residents'])
    avg_pressure = mean(record['pressure'] for record in history)
    avg_energy = mean(record['avg_energy'] for record in history)
    
    # Establish a threshold for bond count related to pressure levels
    bonding_threshold = 0.1
    pressure_threshold = 1.2
    energy_threshold = 2000.0
    
    if avg_bonds < bonding_threshold and avg_pressure > pressure_threshold and avg_energy < energy_threshold:
        return TheoryFinding(
            theory='Broken Windows Theory',
            citation='Wilson, J. Q., & Kelling, G. L. (1982)',
            prediction='In conditions of neglect and resource scarcity, diminished social bonds and increased pressure may further destabilize social cohesion.',
            observed={
                'avg_bonds': avg_bonds,
                'avg_pressure': avg_pressure,
                'avg_energy': avg_energy
            },
            gap='Low average bond count, high population pressure, and low average energy suggest the presence of social disorder and decay, indicating that norms supporting cohesion are failing.',
            severity='critical'
        )
    return None
```
