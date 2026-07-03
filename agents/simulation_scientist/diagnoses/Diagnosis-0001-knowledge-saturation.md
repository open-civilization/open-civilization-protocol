# Diagnosis-0001: Knowledge Saturation and Over-Uniform Civilization

## Status

Confirmed, unaddressed. Root-cause identified. Fix not yet implemented.

## Summary

The simulation reaches a stable, long-running civilizational state, but knowledge — including language and writing — spreads with essentially zero friction: once any technology is discovered anywhere in the population, it eventually reaches ~100% adoption with no lasting regional, generational, or group-level differentiation. The world develops civilization, but not *diverse* civilization. This is a structural gap, not a calibration error: no mechanic in the current model can produce loss, dialectization, or regional divergence of knowledge once it exists.

## Evidence

### Live sandbox snapshot (tick 7183, year 224)

| Metric | Value |
|---|---|
| Population | 1180 |
| Carrying capacity | 751 |
| Pressure | 1.58 |
| Avg energy | 1986 kcal |
| Avg health | 45.3 |
| Max generation | 187 |
| food_storage / farming / herding / shelter / clothing / fire / language / writing holders | 1194 / 1194 (100% each) |

Recent event stream dominated by `forage`, `scavenge`, `reproduce`, `disease`, `death`; recent death causes dominated by `disease` and `old_age` rather than starvation — consistent with a population that has solved acute subsistence risk and is now bottlenecked by density-dependent costs (epidemic, aging) instead.

### Lightweight audit sample (120 ticks, seed 3000)

| Metric | Value |
|---|---|
| Final / peak population | 229 / 250 |
| Pressure | 1.15 |
| knowledge_ratio (food_storage) | 0.751 |
| food_storage / shelter / clothing / fire holders | 172 / 152 / 139 / 132 |
| animal_husbandry holders | 9 |
| cultivated_cells | 30 |
| language / writing holders | 0 / 0 |

This earlier-stage sample confirms the *emergence order* is sound: subsistence technologies (storage, shelter, clothing, fire) precede domestication, which precedes language, which precedes writing. The problem is not sequencing — it's what happens after each technology exists: it converges to universal adoption instead of settling into a patchwork.

## Root Cause

Three compounding facts in the current model:

1. **Knowledge only ever increases.** Every acquisition pathway (discovery, reinforcement, transmission, inheritance) can raise a `known_knowledge` entry's `level`, but nothing ever lowers it. RFC-0006 already specifies decay as required ("Knowledge that is not used, reinforced, or retransmitted SHOULD decay") but no general decay mechanic is implemented — only a few skills get *reinforcement* (which raises level further), never *disuse decay* (which would lower it). A ratchet with no counterweight converges to saturation given enough time, regardless of transmission difficulty.
2. **Transmission has no notion of social or spatial distance.** `_do_interact` requires physical adjacency for a single event, but nothing tracks cumulative "hops from origin," regional isolation, or group membership. A well-mixed, mobile population (which this one is, especially post-domestication when surplus enables more movement) will eventually connect any two individuals through short chains, and each hop's fidelity loss (RFC-0006 channel model) is bounded well above zero specifically *to preserve the cultural ratchet* — so nothing stops total homogenization, only slows it.
3. **Language and writing are monolithic skills, not distinguishable entities.** The model tracks *whether* a resident knows `spoken_language`/`writing`, not *which* language or writing system — so there is no way for two isolated groups to independently develop different, mutually unintelligible conventions, which is what would actually produce regional divergence (dialects, separate scripts) instead of one global skill bar filling up.

## Why This Matters

Per RFC-0006's own stated goals, this directly contradicts several intended properties: "independent invention in isolated populations," "knowledge loss after collapse (dark ages)," and "transmission distortion creating cultural divergence" are all explicitly listed motivations the system is supposed to produce — none of which are currently possible, because nothing in the implemented model can make a subpopulation *lose* what it has, or *diverge* from what another subpopulation has.

## Recommended Priority

1. **Knowledge transmission friction (highest priority — addresses the root cause).** Implement general disuse decay for all `known_knowledge` entries (not just the handful of skills with bespoke reinforcement logic), so unpracticed knowledge fades and must be actively maintained by a population to persist. This alone should partially relieve finding #3 (language/writing lack of differentiation) as a side effect: if an isolated group's language/writing decays before enough transmission events reach it, divergent re-invention becomes possible again.
2. **Language/writing reification.** Once decay exists, consider whether `spoken_language`/`writing` should carry an identity (which language, which script) rather than being a single global skill — this is a larger structural change and should follow, not precede, the decay fix.
3. **Cost of dense societies.** Disease, crowding, upkeep, and institutional fragility already exist as mechanics (epidemic, malnutrition, pressure²-scaling) and appear to be doing real work (avg_health 45.3, disease/old_age as leading death causes in the live snapshot) — lower priority than the other two, worth revisiting after the transmission-friction fix changes the population's technology profile.

## Open Question for Future Diagnoses

Beyond transmission mechanics, the underlying agent model assumes residents cooperate straightforwardly once bonded. Real human groups exhibit a persistent tension between individual self-interest (resource exclusivity, a bounded individual's desire for more being effectively unbounded) and group-level norms — a game-theoretic dynamic (cooperate/defect, in-group trust vs. out-group predation, free-riding) that the current raiding/bond system only partially captures (raiding targets are biased toward non-bonded strangers under moderate pressure, but there is no mechanic for a bonded individual to *defect* from an established cooperative relationship for individual gain). This is a distinct, likely larger investigation and is intentionally out of scope for this diagnosis.
