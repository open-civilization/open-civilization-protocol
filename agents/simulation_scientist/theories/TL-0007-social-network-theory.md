# TL-0007: Social Network Theory

**Citation:** Granovetter, M. S. (1973). The Strength of Weak Ties.

**Domain:** sociology

**Prediction:** Communities should show enhanced resilience and resource access through diverse and interconnected social networks, impacting their survival and reproduction rates.

**Discovered:** 2026-07-05T02:45:24.453723+00:00

## Write-up

Social Network Theory, particularly as articulated by Granovetter in "The Strength of Weak Ties" (1973), posits that social networks significantly influence individual and group behaviors, including survival, resource access, and innovation. In essence, individuals connected to a broader network experience advantages in accessing resources, information, and opportunities. Strong ties, however, tend to exist within closely-knit groups, while weak ties can bridge disparate groups and provide access to novel resources and perspectives.

In the context of the emergent-civilization sandbox, the observation of a low average bond count per resident could signal a potential issue of social coherence and collaboration. If residents are not forming sufficient social connections, this may limit their ability to share knowledge, pool resources, and support one another in survival and collective action, thus leading to vulnerabilities within the population. Conversely, a high number of bonds would suggest a robust social network that could enhance resilience against challenges such as resource scarcity or external threats.

A confirming observation would show a high average bond count reflecting diverse social networks among residents, and this could further correlate with better outcomes in health, reproduction, and innovation. On the other hand, a significant gap, as indicated by an average bond count far below the threshold, emphasizes the need for further investigation into how social relationships and configurations may be affecting the community's overall dynamics and sustainability.

## Implementation

```python
def _social_network_theory_compare(history, state):
    num_residents = len(state['residents'])
    total_bonds = sum(resident['bonds'] for resident in state['residents'])
    avg_bonds_per_resident = total_bonds / num_residents if num_residents > 0 else 0
    threshold = 0.6  # Hypothetical threshold for social network resilience
    if avg_bonds_per_resident < threshold:
        return TheoryFinding(
            run=None,
            theory="Social Network Theory",
            citation="Granovetter, M. S. (1973). The Strength of Weak Ties.",
            prediction="Communities should show enhanced resilience and resource access through diverse and interconnected social networks.",
            observed={
                "avg_bonds_per_resident": avg_bonds_per_resident
            },
            gap="Total social bonds per resident indicate a limited social network, reducing resilience and resource access potential.",
            severity="medium",
            suggested_investigation="analyze_social_bond_structure"
        )
    return None
```
