# TL-0003: Linguistic niche hypothesis (specifically: population size and language complexity)

**Citation:** Lupyan, G., & Dale, R. (2010). Language structure is partly determined by social structure. PLoS ONE, 5(1), e8559.

**Domain:** cultural evolution / language dynamics

**Prediction:** As a population grows and becomes more connected, language should become simpler (less morphological complexity) due to increased proportion of adult learners; here, language_holders should plateau or decline as pop stabilizes high, but instead it may remain constant or track population.

**Discovered:** 2026-07-04T15:00:18.506639+00:00

## Write-up

## Linguistic Niche Hypothesis

The linguistic niche hypothesis, formalized by Lupyan & Dale (2010), proposes that language structure is partly shaped by the social environment of its speakers. In particular, languages spoken by large, diverse populations with many adult learners tend to exhibit simpler morphology (less inflectional complexity), whereas languages spoken by smaller, more insular groups retain greater complexity. This is because adult learners find complex morphology difficult and, over generations, the language evolves toward a simpler, more regular system to facilitate communication across a larger, more heterogeneous community.

In this simulation, we have a population that has stabilized at a high level (around 270-300 individuals) under chronic carrying-capacity pressure. The theory would predict that as the population grows and presumably becomes more interconnected (more bonds, more exchange), the language and writing systems should show signs of simplification — for example, a decline in the proportion of language holders (specialized knowledge) or a plateau in writing holders as a fraction of population. Instead, the observed data shows that language_holders and writing_holders tend to track the overall population, maintaining a stable proportion, and writing is not being lost or simplified. This stability in linguistic complexity despite large population size is a gap that calls for explanation: either the simulation's population is not sufficiently diverse (no adult migration), or the cultural transmission mechanics are too conservative, preserving complexity beyond what the niche hypothesis would expect.

A confirming observation for this theory would be a gradual decline in language/writing holders per capita as the population expands beyond some threshold (e.g., 100 individuals), or a stochastic drift toward fewer holders. A disconfirming observation is exactly what we see here: high and stable proportions of specialist language knowledge persisting even as the society reaches carrying capacity. This suggests that the simulation's cultural learning dynamics may be missing the 'simplification pressure' that real-world large societies exhibit, possibly because there is no mechanism for language contact or adult second-language learning.

## Implementation

```python
def _linguistic_niche_compare(history, state):
    if len(history) < 20:
        return None
    # get language_holders near beginning and end
    early = history[min(19, len(history)//4)]
    mid = history[len(history)//2]
    late = history[-1]
    early_pop = early.get('pop', 0)
    late_pop = late.get('pop', 0)
    early_lang = early.get('language_holders', 0)
    late_lang = late.get('language_holders', 0)
    # if population changed significantly, language should not simply track pop linearily
    if early_pop * 0.8 > late_pop or late_pop > early_pop * 1.2:
        return None  # pop changed significantly, check ratio change
    # compute language holder proportion change
    early_ratio = early_lang / max(early_pop, 1)
    late_ratio = late_lang / max(late_pop, 1)
    change = abs(early_ratio - late_ratio)
    # If the ratio is very stable despite theory predicting simplification (decline in specialist holders), that's a gap
    if change < 0.05 and early_ratio > 0.5 and late_ratio > 0.5:
        # also check if writing is present - that is a complexity indicator
        early_write = early.get('writing_holders', 0) / max(early_pop, 1)
        late_write = late.get('writing_holders', 0) / max(late_pop, 1)
        if late_write >= early_write * 0.8:  # writing is not being lost
            return TheoryFinding(
                theory='Linguistic niche hypothesis',
                citation='Lupyan, G., & Dale, R. (2010). PLoS ONE, 5(1), e8559.',
                prediction='Under stable high population, language complexity (specialist holders like writing) should decrease proportionally due to adult learning pressures.',
                gap=f'Language proportions remain very stable (early {early_ratio:.2f}, late {late_ratio:.2f}) and writing is not declining ({early_write:.2f} -> {late_write:.2f}), contrary to the expected simplification in a large community with many adult learners.',
                severity='medium'
            )
    return None
```
