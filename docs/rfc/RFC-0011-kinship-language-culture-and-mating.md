# RFC-0011 Kinship, Language Drift, Cultural Divergence, and Mating Competition

## Status

Draft

## Summary

This RFC defines how OCP should separate and connect:

- genetics
- kinship
- language
- writing
- culture
- mating competition

These systems are deeply related, but they are not the same thing.

If OCP collapses them into one layer, the simulation will produce a false world where:

- language behaves like blood
- culture behaves like genes
- writing appears as an automatic upgrade
- marriage norms are hardcoded instead of emergent
- "tribes" are only friend lists with children

This RFC exists to prevent that failure mode.

## Motivation

Real human populations do not differentiate along a single axis.

A population may:

- share ancestry but not language
- share language but not writing
- share writing but not culture
- share territory but not marriage norms
- exchange genes without merging identities
- exchange culture without much intermarriage

OCP needs these dimensions to remain separable if it wants to search for possible civilizations rather than replaying a flattened historical stereotype.

## Goals

This RFC defines:

- the distinction between genetics, kinship, culture, language, and writing
- how lineage and family structure should be represented
- how group isolation can generate cultural and linguistic divergence
- how mating competition should work without hardcoding a fixed marriage system
- how reproductive exclusion can create migration, splinter groups, and new populations
- what the engine must detect, and what it must never directly author

## Non-Goals

This RFC does not define:

- modern ethnicity categories
- race as a fixed or essential type
- nation-state identity
- theology or doctrine systems
- detailed child-rearing simulation
- a predefined marriage law table

If these appear in OCP, they must emerge from lower-level processes.

## Architectural Position

This RFC is cross-cutting.

It touches:

- `Life` — reproduction, inheritance, family structure, social bonds
- `Knowledge` — oral transmission, writing systems, cultural memory
- `Civilization` — group boundary formation, divergence, alliance, assimilation
- `Story Engine` — genealogies, houses, splinter groups, language families

## Normative Language

The key words "MUST", "MUST NOT", "SHOULD", and "MAY" in this document are to be interpreted as binding protocol terms.

## First Principle

Kinship is not culture.

Culture is not language.

Language is not writing.

Writing is not civilization.

Genetic mixing does not automatically imply cultural assimilation.

Cultural assimilation does not automatically imply genetic mixing.

These systems interact, but the engine must keep them distinct.

## Conceptual Layers

### 1. Genetics

Genetics represents inherited biological variation.

Examples:

- strength
- endurance
- disease resistance
- perception
- fertility-related traits
- developmental tendencies

Genetics SHOULD affect fitness, survival, and reproductive outcomes.

Genetics MUST NOT directly determine:

- language
- writing system
- ritual system
- group membership
- loyalty

### 2. Kinship

Kinship represents genealogical relation.

Examples:

- parent-child
- full sibling
- half sibling
- grandparent
- cousin
- lineage branch

Kinship is about descent structure, not identity by itself.

### 3. Culture

Culture represents repeated socially transmitted behavior.

Examples:

- marriage norms
- food-sharing expectations
- mourning rules
- inheritance customs
- gendered division of labor
- elder authority
- initiation rites
- vengeance norms

Culture is learned, enforced, and changed through social life.

### 4. Language

Language represents a spoken symbol system used for coordination, memory compression, naming, and social distinction.

Different groups may speak:

- mutually intelligible dialects
- partially intelligible sister languages
- fully distinct languages

Language drift is expected under partial isolation.

### 5. Writing

Writing is an external memory and inscription system.

Writing SHOULD emerge later than speech in most trajectories.

Writing is not guaranteed even if language is complex.

A group may have:

- spoken language without writing
- language plus mnemonic notation
- multiple languages using one script
- one language using multiple scripts

## Kinship Model

### Minimum Requirements

OCP residents SHOULD eventually carry at least:

- `parent_ids`
- birth generation
- sibling relations derivable from shared parentage
- household or caregiving ties distinct from raw biology

The current single-parent lineage model is insufficient for long-term civilization research.

### Why Single-Parent Lineage Is Not Enough

A one-parent graph cannot reliably support:

- exogamy and endogamy analysis
- cousin marriage avoidance
- half-sibling recognition
- descent-group formation
- inheritance disputes
- ancestry mixing analysis

The engine therefore SHOULD move toward explicit dual-parent or multi-parent ancestry recording.

### Kinship vs. Social Parenthood

Biological parentage and caregiving do not need to be identical.

The engine MAY later distinguish:

- biological parent
- household parent
- adoptive or ritual parent

But genealogy itself must remain traceable.

## Inbreeding and Mate Exclusion

### Incest Avoidance

The engine SHOULD include reproductive friction or prohibition for very close kin.

At minimum, reproduction SHOULD be strongly constrained for:

- parent-child
- full siblings
- half siblings

The model MAY later include:

- cousin taboo variation by culture
- inbreeding depression
- prestige exceptions under elite concentration

The point is not to encode one universal morality.

The point is to ensure that mating structure has real biological and social consequences.

### Implementation Note: Bounding Cumulative Load

The engine's `inbreeding_load` (child load = average of both parents' own accumulated load, plus an increment scaled by their relatedness) is a compounding, multi-generation quantity, not a one-off penalty — this is what lets a genuine outcross with a low-load partner dilute/improve on a high-load lineage (heterosis) rather than every pairing resetting to the same fixed cost.

That accumulation formula MUST be bounded. Live data caught the failure mode directly: a population that bottlenecked down to one small, closed group (no unrelated partner ever reachable) saw `avg_inbreeding_load` climb to 3.5-3.8 — several times past every dependent penalty's own documented worst-case assumption of load=1.0 — during a slow extinction where food pressure stayed near zero and average energy stayed healthy the entire time. It was a purely genetic death spiral, not a resource one, and it was possible only because nothing capped the value. A hard ceiling (matching the existing worst-case documentation each dependent penalty already assumed) closes this without changing any of the per-generation math above it.

### Reproductive Exclusion

Not every adult must reproduce.

This is crucial.

Real populations often show strong reproductive skew.

Some individuals:

- secure mates repeatedly
- monopolize resources
- build alliances
- gain prestige
- outcompete rivals

Others:

- fail to attract partners
- lose status contests
- are expelled
- migrate
- raid
- form splinter groups

This asymmetry is not a bug.

It is one of the engines of divergence.

## Mating Competition

### First Principle

OCP SHOULD model a mating market, not a fixed marriage system.

The engine should not begin by declaring:

- monogamy
- polygyny
- polyandry
- serial pairing

Instead, it should simulate the pressures from which these patterns can emerge.

### Relevant Pressures

The following pressures SHOULD affect reproductive access:

- adult operational sex ratio
- resource control
- health and survivability
- prestige and coalition support
- violence risk
- parental investment cost
- child survival payoff
- jealousy and conflict cost
- household maintenance cost
- local cultural norms

### Resulting Patterns

Depending on ecology and culture, the same world rules MAY produce:

- mostly pair-bonded reproduction
- high-status male reproductive concentration
- female mate choice under resource scarcity
- late male reproduction after status competition
- large numbers of low-status unmated males
- splinter migration by excluded males
- reproductive monopolies that later destabilize a group

The engine should model the incentives, not the institution name.

## Group Isolation and Divergence

### Isolation Mechanisms

Group differentiation usually requires some combination of:

- geographic separation
- migration barriers
- marriage boundaries
- repeated internal interaction
- unequal external conflict
- information bottlenecks
- ritual or prestige boundaries

The engine SHOULD not require total isolation.

Partial, porous isolation is enough to produce divergence over time.

### Divergence Targets

Under sustained partial isolation, groups SHOULD be able to diverge in:

- spoken vocabulary
- pronunciation patterns
- kinship terminology
- taboos
- sharing norms
- mating preferences
- prestige markers
- ritual practices
- memory forms
- writing conventions

The important point is that divergence must be gradual, local, and path-dependent.

## Language Drift

### Spoken Language Must Be Group-Bound

Spoken language is not just a resident-level toggle.

It must eventually become at least partially group-bound.

That means:

- language should have variants
- variants should spread through social networks
- variants should drift under partial isolation
- contact should enable borrowing, not instant convergence

### Minimum Future Direction

The engine SHOULD evolve toward:

- `language_id` or language cluster identity
- dialect drift from parent language
- intelligibility that decays with drift distance
- vocabulary borrowing through trade, alliance, and intermarriage

Language should behave like a living transmission network, not like a global buff.

## Writing Divergence

Writing must be modeled separately from language.

Writing systems may differ in:

- symbol set
- medium
- fidelity
- learning cost
- storage durability
- administrative usefulness

Writing may emerge for:

- accounting
- genealogy
- storage records
- property marking
- ritual preservation
- political memory

It SHOULD NOT simply appear because a resident already knows spoken language.

## Culture Drift

Culture should be represented as a set of transmissible, mutable norms rather than as a binary label.

Candidate norm domains:

- marriage exclusivity
- acceptable mate rank gap
- elder authority
- retaliation rules
- adoption of outsiders
- inheritance bias
- childcare distribution
- widow or widower reintegration
- acceptable close-kin marriage distance

Different groups can therefore share ancestry while diverging culturally.

## Intermarriage, Assimilation, and Fusion

The engine SHOULD distinguish:

- intermarriage
- genetic mixing
- bilingualism
- script borrowing
- cultural assimilation
- elite domination
- syncretic fusion

These are not identical.

A small number of marriages between groups does not necessarily erase a group boundary.

A script can be borrowed without language replacement.

A prestige language can spread without large population replacement.

This distinction is essential if OCP wants to simulate real civilizational blending rather than simplistic merging.

## Group Boundary Formation

OCP should not begin with fixed tribe objects.

Instead, the engine SHOULD detect emergent group boundaries from signals such as:

- dense internal kinship
- repeated internal bonds
- mating preference concentration
- language similarity
- ritual similarity
- conflict bias against outsiders
- naming or ancestry continuity

Once detected, these boundaries may be labeled by the observer layer, but must not be created by fiat.

## Detection vs. Design

This RFC makes one boundary explicit:

The engine may detect groups.

The engine must not pre-author civilizations.

Allowed:

- increasing mating competition under scarcity
- making lineage traceable
- allowing dialect drift under isolation
- adding cultural norm mutation and transmission
- biasing trust toward known kin and co-speakers

Not allowed:

- creating "Tribe A" and "Tribe B" at tick 0 as authored content
- assigning fixed civilizations to geography by designer choice
- forcing a group into monogamy or polygyny as a hardcoded destiny
- auto-upgrading a language into writing after a time threshold

## Implementation Roadmap

### Phase 1

Stabilize the underlying life model:

- replace single `parent_id` with `parent_ids`
- expose kin degree calculation
- add incest avoidance and close-kin penalties
- reduce direct birth inheritance of high-order culture knowledge

### Phase 2

Separate transmission layers:

- spoken language state
- writing state
- cultural norm state
- household and caregiving structure

### Phase 3

Introduce group drift:

- language variants
- cultural norm mutation
- intergroup marriage rates
- reproductive exclusion and migration consequences

### Phase 4

Add detection:

- lineage clusters
- cultural clusters
- language families
- splinter-population emergence

## Success Criteria

This RFC is successful if OCP can eventually produce worlds where:

- ancestry and culture are correlated but not identical
- isolated groups drift apart without being manually designed
- intermarriage creates mixing without instant homogenization
- reproductive skew produces migration and splinter dynamics
- some populations remain oral while others externalize memory through writing
- group boundaries emerge from repeated structure rather than labels

## Final Principle

Civilizations do not emerge from a single population becoming "more advanced."

They emerge from:

- descent
- divergence
- competition
- exchange
- exclusion
- mixing
- memory

If OCP cannot separate these processes, it cannot truly search for possible civilizations.
