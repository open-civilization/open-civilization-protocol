# RFC-0006 Knowledge System

## Status

Draft

## Summary

This RFC defines how knowledge is acquired, represented, stored, transmitted, distorted, and lost in OCP.

Knowledge in OCP is not a tech tree. It is not a global unlock. It is a distributed, lossy, perspective-bound substance that lives inside individual memories, oral traditions, artifacts, and institutions — and that can die with the last person who remembers it.

## Motivation

Most civilization simulations treat knowledge as a global resource: once "agriculture" is researched, everyone benefits. This collapses the most interesting dynamics of real civilizations:

- independent invention in isolated populations
- knowledge loss after collapse (dark ages)
- transmission distortion creating cultural divergence
- the cost of education and institutional memory
- the difference between knowing something and being able to teach it

OCP needs a knowledge system where what you know depends on where you are, who you've talked to, and what you've survived — not on a shared tech tree.

## Goals

This RFC defines:

- knowledge representation at individual and collective levels
- acquisition pathways (observation, experiment, imitation, communication, inheritance)
- storage and decay
- transmission mechanics and fidelity loss
- false beliefs and partial knowledge
- the relationship between knowledge and action capability
- knowledge as a civilization variable

## Non-Goals

This RFC does not define:

- the AI reasoning architecture (see RFC-0005)
- specific technologies or discoveries
- a predefined research tree
- the economy of intellectual property

## Architectural Position

Knowledge is not a layer in the world stack. It is a cross-cutting concern that touches:

- `Life` — individual memory and learning
- `AI Decision` — context available for reasoning
- `Civilization` — institutional memory, cultural transmission, accumulated technique
- `Story Engine` — discoverable narrative about what was known and lost

## Normative Language

The key words "MUST", "MUST NOT", "SHOULD", and "MAY" in this document are to be interpreted as binding protocol terms.

## First Principle

Knowledge is local, mortal, costly, and **adaptive**.

No resident knows the whole world. No discovery is permanent. No transmission is free or perfect.

## Second Principle: Knowledge Optimizes Survival

Knowledge is NOT decorative, but it is NOT mandatory for baseline survival either.

**The model:**
- **Base environment is viable** — tropical zone can sustain ~40 people without any knowledge; temperate ~10; cold ~5
- **Winter creates scarcity pressure** — low regrowth in winter means residents face food shortage; without knowledge, winter death rates are high (20-50%)
- **Knowledge provides competitive advantage** — residents with food storage knowledge survive winter better (~5-20% death vs 20-50% without)
- **Survival leads to reproduction** — residents who survive winter reproduce more often; knowledge-holders transmit their knowledge to offspring
- **Natural selection emerges** — after 5-10 years, knowledge-holders form a larger portion of population; after 10-20 years, partially-informed individuals are selected against

This creates **generational knowledge ratchet**: each generation adds slightly better knowledge; knowledge loss is possible but costly (populations revert to higher winter mortality).

## Third Principle: Knowledge Multiplies Capacity, Not Just Survival Odds

Some knowledge does more than improve an individual's odds against a fixed environment — it changes what the environment can support. Domestication (`crop_cultivation`, `animal_husbandry`) is the Phase 1 example: it doesn't gate survival the way winter food storage does, but where it takes hold it raises the land's productivity itself (see RFC-0003), so the population ceiling for a region rises as the knowledge spreads.

**The distinction matters constitutionally:**
- Survival-optimizing knowledge (food storage) changes an individual's odds against a fixed resource base.
- Capacity-multiplying knowledge (domestication) changes the resource base itself, for knowledge-holders and non-holders on the same cultivated land alike.
- Both remain emergent and reversible: capacity gains decay if the knowledge is lost or the land untended (RFC-0001 Law 10), just as survival gains do.

A civilization's growth curve is therefore not a designed progression — it's the sum of which capacity-multiplying and survival-optimizing knowledge happened to be discovered, where, and whether it survived long enough to spread.

## Knowledge Representation

### Individual Knowledge

Each resident carries a personal knowledge store as part of their memory (RFC-0004).

Individual knowledge SHOULD include:

- spatial knowledge (map of visited/known locations, resource awareness)
- social knowledge (known individuals, reputation, trust levels)
- procedural knowledge (techniques, skills, behavioral patterns that improve action outcomes)
- causal knowledge (observed associations: "fire comes from friction," "this plant is poisonous")
- narrative knowledge (stories, explanations, names — received from others, possibly distorted)

### Knowledge Properties

- Knowledge entries MUST have a source (self-observed, told by whom, inherited from whom).
- Knowledge entries SHOULD have a confidence or reinforcement level that decays without refreshment.
- Knowledge entries MAY be false, outdated, or partially correct.
- A resident's knowledge store MUST be bounded in size.

## Acquisition Pathways

Knowledge MUST arise through one of the following pathways. No other pathway is constitutionally valid (RFC-0001 Law 6).

### Observation

- A resident perceives something directly within perception range.
- Observation yields high-confidence but narrow knowledge.
- Example: seeing that a river cell contains fish.

### Experiment

- A resident performs an action and observes the outcome.
- Experiment is costlier than observation (energy, time, risk) but can reveal non-obvious relationships.
- Example: trying to eat an unknown plant and observing the health effect.
- Failed experiments SHOULD still produce knowledge (negative results are information).

**Implemented example — domestication.** `crop_cultivation` and `animal_husbandry` are discovered exclusively through repeated Experiment: a resident foraging on terrain physically suited to the activity (see RFC-0003 Domestication and Land Improvement) has a small per-tick chance of discovering the technique. There is no scripted trigger, tick threshold, or population requirement — discovery is a probability roll gated only by physical suitability (terrain × climate zone), so whether and when domestication appears, and whether a population becomes farmers or herders, is a genuine random outcome of repeated environmental interaction. Once discovered, the knowledge deepens further through continued practice (a form of self-reinforcing Experiment) and spreads through the same Imitation, Communication, and Inheritance pathways as any other knowledge — nothing about its acquisition or transmission is special-cased.

### Imitation

- A resident observes another resident performing an action and copies the technique.
- Imitation MUST require proximity and perception.
- Imitation SHOULD introduce fidelity loss — the copy is rarely as good as the original.
- Imitation is the cheapest form of social learning and the foundation of cultural transmission.

### Communication

- A resident tells another resident something.
- Communication MUST require proximity or a modeled transmission channel.
- Communicated knowledge SHOULD be subject to distortion, simplification, or misinterpretation.
- The recipient MAY choose whether to trust or act on communicated knowledge.
- Communication can transmit knowledge that the communicator has never personally verified (rumor, hearsay, tradition).

### Inheritance

- Offspring MAY receive a subset of parental knowledge at birth or during early life.
- Inherited knowledge SHOULD be less detailed or confident than the parent's version.
- Inheritance represents implicit cultural transmission (habits, preferences, basic survival technique) rather than explicit teaching.

## Transmission Fidelity

Per RFC-0001 Law 6 (Transmission Fidelity):

- Transmission MUST be imperfect by default.
- Distortion during transmission MUST be treated as a legitimate source of novelty.
- Net transmission fidelity across generations SHOULD be positive on average (more retained than lost), enabling cumulative culture.

### Fidelity Factors

Transmission fidelity SHOULD depend on:

- the complexity of the knowledge being transmitted
- the cognitive budget of sender and receiver
- the number of transmission steps from the original source
- whether the knowledge is reinforced by direct experience after transmission
- the availability of external memory aids (artifacts, landmarks, rituals)

### Cultural Ratchet

The knowledge system SHOULD support the ratchet effect: each generation should be able to build slightly on what the previous generation transmitted, rather than starting from zero. This requires:

- at least one low-cost, high-frequency transmission channel (oral tradition, imitation)
- lossy but net-positive retention across generations
- the ability for reinforced knowledge to become more durable than unreinforced knowledge

Without the ratchet effect, no civilization can accumulate beyond what a single lifetime discovers.

## Knowledge Decay

Knowledge that is not used, reinforced, or retransmitted SHOULD decay.

### Decay Mechanisms

- time-based decay: old memories fade
- disuse decay: knowledge not applied or recalled loses strength
- interference: new experiences may overwrite or corrupt old knowledge
- death: when a resident dies, all knowledge held only by that resident is lost unless previously transmitted

### Decay Implications

- Institutions that preserve and retransmit knowledge (teaching, apprenticeship, ritual) gain survival value.
- Isolated populations that lose key knowledge may regress in capability.
- Dark ages are not scripted events — they are natural consequences of transmission failure after organizational collapse.

## False Beliefs

The knowledge system MUST allow residents to hold incorrect beliefs.

### Requirements

- A resident MAY believe something that is factually wrong about the world.
- False beliefs SHOULD be able to propagate through communication just like true beliefs.
- False beliefs MAY persist indefinitely if never contradicted by direct experience.
- The engine MUST NOT automatically correct false beliefs. Only direct observation or experimentation that contradicts the belief SHOULD trigger revision.

### Why False Beliefs Matter

- False beliefs about resource locations cause wasted effort and migration.
- False beliefs about other groups cause conflict or missed cooperation.
- Shared false beliefs can become culture (myths, taboos, superstitions) that may be adaptive, maladaptive, or neutral.
- A world where all beliefs are automatically true is a world without the cost of knowledge — which violates the constitutional requirement that knowledge has acquisition cost.

## Knowledge and Action

Knowledge SHOULD affect action capability.

### Procedural Knowledge Effects

- A resident who has learned a technique (fishing, fire-making, tool use) SHOULD perform the corresponding action more effectively than one who has not.
- Effectiveness gains SHOULD be gradual, not binary unlocks.
- Techniques learned by imitation SHOULD start at lower effectiveness than techniques learned by repeated personal practice.

**Implemented example:** a resident with `crop_cultivation` or `animal_husbandry` foraging on suitable land converts a larger share of harvested biomass into usable energy (gradual, skill-scaled — never exceeding what was physically taken from the land, preserving RFC-0003 matter conservation). This is the immediate, individual-level expression of the knowledge; the slower, land-level expression (raising the cell's own productivity for anyone who forages there) is described in RFC-0003.

### Knowledge as Soft Technology

Knowledge improvements in OCP are not "technologies" that globally upgrade a civilization. They are individual or small-group capabilities that spread through transmission, degrade through neglect, and die with their carriers.

A civilization's aggregate "technology level" is an emergent statistical property of its population's distributed knowledge, not a centrally tracked variable.

## Collective Knowledge

As groups form, knowledge SHOULD be able to exist at collective levels.

### Institutional Memory

- Stable groups MAY develop shared knowledge that persists beyond individual turnover.
- Institutional memory SHOULD require active maintenance (teaching, ritual, practice).
- Institutional memory that is not maintained SHOULD degrade, even if the institution itself persists.

### Specialization

- Within groups, individuals MAY hold different knowledge, creating de facto specialization.
- Specialization creates dependency and coordination value, which is one pathway to emergent organization.

## External Memory

Residents and groups MAY create external memory through artifacts.

### Examples

- landmarks with associated meaning
- marked trails
- storage caches at known locations
- constructed tools that embody procedural knowledge
- later: carvings, monuments, written records

### Requirements

- External memory artifacts MUST exist in physical space and be subject to decay (RFC-0001 Law 10).
- External memory SHOULD be interpretable only by residents who have sufficient contextual knowledge.
- External memory SHOULD improve knowledge retention and transmission fidelity for groups that create and maintain it.

## Constitutional Compliance

This RFC is subordinate to RFC-0001 Universe Constitution.

### Law 3: Causality

- knowledge acquisition MUST have traceable causal origin

### Law 6: Knowledge Cannot Appear from Nothing

- all pathways are constrained to observation, experiment, imitation, communication, inheritance
- transmission fidelity requirements enforced

### Law 7: Bounded Cognition

- individual knowledge is local, partial, and fallible

### Law 9: Information Has Speed

- knowledge transmission requires proximity or channel, not instant broadcast

### Law 10: Entropy

- knowledge decays without maintenance and reinforcement

## Phase 1 Implementation Guidance

A good Phase 1 knowledge system would include:

- per-resident knowledge store with bounded capacity
- spatial and procedural knowledge types
- observation and imitation as primary acquisition pathways
- time-based knowledge decay
- communication-based transmission with fidelity loss
- false beliefs allowed and propagated
- knowledge affecting action effectiveness (gradual, not binary)
- death causing knowledge loss for untransmitted entries

Full institutional memory, external memory artifacts, and complex cultural transmission MAY be deferred to Phase 2.

## Open Questions

- What is the optimal knowledge store capacity per resident for Phase 1?
- How should procedural knowledge effectiveness scale (linear improvement, diminishing returns, step functions)?
- Should the engine track "discovery events" explicitly, or infer them from knowledge-state changes?
- How much transmission noise produces useful cultural divergence without destroying the ratchet effect?
- Should residents be able to deliberately lie (transmit known-false information)?

## Future Dependencies

The following RFCs depend on or interact with this one:

- `RFC-0007 Civilization Emergence`
- `RFC-0008 Story Engine`

## Conclusion

Knowledge in OCP is what makes the difference between a population of foragers and a civilization.

But only if knowledge is hard to get, easy to lose, and never free. The cost of knowing is what gives teaching, memory, and institutions their survival value — and what makes dark ages, cultural divergence, and independent invention possible.
