# TL-0023: Self-Organization Theory

**Citation:** Camazine, S., et al., 'Self-Organization in Biological Systems', 2003

**Domain:** complex systems theory

**Prediction:** The theory predicts that under certain conditions, decentralized interactions among agents can lead to the emergence of organized structures, including robust populations that stabilize around a carrying capacity.

**Discovered:** 2026-07-06T00:33:52.503038+00:00

## Write-up

Self-Organization Theory describes how decentralized systems can display organized behavior that arises from local interactions among components, without any centralized control. Notably, in biological systems, this principle explains phenomena such as flocking behavior in birds and the formation of complex social structures. The hypothesis suggests that under specific conditions, populations can stabilize and thrive rather than collapse, even in challenging environments.

In the context of the simulation, the results indicate a complete failure of population maintenance, with all lineages resulting in extinction before any successful peak population is achieved. Given the observed fluctuating metrics—such as human interactions and resource availability—self-organization could be a plausible explanation for why populations did not adapt or stabilize as might have been expected under local social and ecological pressures. A population that is able to self-organize would be expected to show emergent stability at some peak level rather than a consistent descent towards extinction.

A confirming observation would involve a population demonstrating a trajectory of increasing or stable numbers over time with varying births and deaths, showcasing that interactions among individuals lead to resilience and structure. Conversely, a persistent collapse regardless of resource availability or social bonds would indicate a failure of this emergent mechanism, thus affirming the need for a deeper analysis of self-organization dynamics in such systems.

## Implementation

```python
def _self_organization_compare(history, state):
    if len(history) < 2:
        return None

    initial_pop = history[0]['pop']
    final_pop = state['residents']
    final_population = len(final_pop)

    avg_total_births = mean([h['total_births'] for h in history])
    avg_total_deaths = mean([h['total_deaths'] for h in history])

    # Self-organization predicts populations should stabilize rather than collapse
    if final_population == 0 and (avg_total_births > avg_total_deaths):
        return TheoryFinding(
            population_dynamics='self_organization',
            evidence={
                'initial_population': initial_pop,
                'final_population': final_population,
                'avg_total_births': avg_total_births,
                'avg_total_deaths': avg_total_deaths
            },
            prediction='Population should have established a stable structure rather than collapsing to extinction.'
        )

    return None
```
