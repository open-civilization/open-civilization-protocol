# RFC-0007 Civilization Emergence

## Status

Draft

## Summary

This RFC defines how OCP detects, labels, and reasons about civilization-level phenomena without designing them in advance.

Civilization in OCP is not a game mechanic. It is not a blueprint. It is a name we give to patterns that emerge when enough life, energy, knowledge, and organization accumulate in a region over time.

The engine's job is to create the conditions under which civilization can arise, and to observe what actually happens — not to ensure that any particular form of civilization appears.

## Motivation

If civilization structures are hardcoded (nations, governments, economies, armies), the project stops being a search system and becomes a disguised historical simulator with adjustable parameters. That is the single most important failure mode OCP must avoid.

But the opposite extreme is also a failure: if the engine has no vocabulary for recognizing emergent structure, then interesting phenomena happen and nobody notices. The simulation produces data without insight.

OCP needs a middle path: conditions that make organization possible, detectors that notice when it appears, and zero templates that predetermine its form.

## Goals

This RFC defines:

- what "civilization" means in OCP (not a preset, but a detectable pattern)
- the conditions that enable emergence
- the scaling pressures that drive organization
- how emergent structures are detected and labeled
- collapse, regression, and legacy
- activity radius as a primary civilization variable
- what the engine must never do (design civilization from above)

## Non-Goals

This RFC does not define:

- specific government types
- diplomacy mechanics
- military systems
- religious doctrine templates
- cultural content
- trade route algorithms

If any of these appear in OCP, they must emerge from lower-level interactions, not from this RFC.

## Architectural Position

```text
Universe
    ↓
Physics
    ↓
Life
    ↓
Civilization    ← this RFC
    ↓
Player
```

Civilization sits between Life and Player. It is not a layer that is "turned on" — it is a pattern-recognition layer that observes what Life produces under Physics constraints and provides vocabulary for what it finds.

## Normative Language

The key words "MUST", "MUST NOT", "SHOULD", and "MAY" in this document are to be interpreted as binding protocol terms.

## First Principle

Civilization is not designed. It emerges.

Developers design world laws. Civilizations arise — or don't — from the interaction of survival pressure, energy surplus, knowledge accumulation, spatial constraint, and individual variation.

If a simulation never produces anything resembling civilization, that is a valid experimental result, not a bug.

## What Civilization Means in OCP

Civilization in OCP is operationally defined as the sustained presence of several emergent properties in a population:

- energy surplus beyond individual survival
- persistent organization above the family/band level
- knowledge accumulation across generations (ratchet effect)
- division of labor or role specialization
- shared infrastructure or constructed environment
- activity radius exceeding individual movement range

No single property is sufficient. The engine SHOULD track these properties as continuous variables rather than binary thresholds.

## Conditions for Emergence

The following conditions, defined in earlier RFCs, create the possibility space for civilization:

### From Physics (RFC-0003)

- spatial heterogeneity (resource gradients, terrain variation)
- movement cost (distance matters)
- resource depletion and regeneration (carrying capacity is real)
- seasonal variation (storage becomes valuable)

### From Energy (RFC-0002)

- surplus possibility (capture can exceed maintenance)
- storage capability (surplus can persist)
- transport cost (energy is local unless moved)
- efficiency variation (some methods work better than others)

### From Life (RFC-0004)

- individual variation (heterogeneous traits)
- social interaction (communication, sharing, conflict)
- reproduction with drift (populations explore trait space)
- memory and learning (experience accumulates)

### From Knowledge (RFC-0006)

- transmission channels (imitation, communication)
- ratchet effect (net-positive intergenerational retention)
- procedural knowledge affecting capability
- knowledge decay creating maintenance pressure

### From AI Decision (RFC-0005)

- novel situation handling (responses to unprecedented events)
- social decision-making (trust, alliance, negotiation)
- cultural generativity (naming, ritual, explanation)

None of these alone produces civilization. Civilization is what happens when they interact at sufficient density, for sufficient time, under sufficient pressure.

## Scaling Pressures

Organizations do not form because they are designed. They form because individual survival strategies become insufficient at certain scales.

### Population Density

- As local populations grow, resource competition intensifies.
- Coordination reduces conflict cost and improves collective foraging/defense.
- Without coordination mechanisms, dense populations are unstable.

### Resource Scarcity

- Scarcity in one zone creates migration pressure toward other zones.
- Groups that control productive territory gain survival advantage.
- Defense of territory requires sustained coordination.

### Knowledge Complexity

- As accumulated knowledge grows, no individual can hold it all.
- Specialization becomes advantageous: some individuals focus on food production, others on tool-making, others on teaching.
- Specialization creates interdependence, which requires organization.

### Activity Radius

- The further a group can effectively reach (for foraging, trade, communication, defense), the more complex its coordination challenges become.
- Activity radius is not technology level. It is the real measure of a civilization's operational scale.
- As activity radius grows, the need for information infrastructure, logistics, and governance grows with it.

## Emergent Structures

The engine SHOULD be able to detect (but MUST NOT create) the following structural patterns:

### Bands and Groups

- persistent spatial co-location of cooperating residents
- shared resource access
- mutual defense behavior

### Settlements

- persistent occupation of a location
- constructed infrastructure (shelters, storage)
- population above the band level

### Trade Networks

- repeated resource exchange between spatially separated groups
- emergence of preferred exchange routes
- specialization creating mutual dependency between groups

### Hierarchies

- some residents consistently influencing others' behavior
- resource flow from periphery to center
- decision-making patterns where few residents' choices affect many

### Cultural Groups

- behavioral or knowledge divergence between geographically separated populations
- shared practices, names, or beliefs within a group that differ from neighboring groups
- transmission of group-specific knowledge to newcomers

## Detection vs. Design

### Detection (Permitted)

The engine MAY:

- compute metrics over populations (surplus levels, cooperation frequency, knowledge distribution)
- label detected patterns (a cluster of cooperating residents near persistent structures MAY be labeled "settlement")
- track pattern persistence, growth, and decline over time
- surface detected patterns to observation, story, and analysis layers

### Design (Forbidden)

The engine MUST NOT:

- create organizational templates (tribes, kingdoms, democracies)
- grant bonuses or capabilities to detected groups that their members do not individually possess
- force residents into organizational structures
- define governance mechanics from above
- create diplomatic relationships as engine objects
- design economies with predefined market structures
- script wars, alliances, or treaties

If a "kingdom" appears in OCP, it is because a pattern of resource control, information flow, and behavioral influence emerged that looks like a kingdom to an observer. The engine never created a Kingdom object.

## Group Competition and Selection

Groups SHOULD face competitive pressure from other groups.

### Requirements

- Groups competing for overlapping resources MUST resolve competition through the same physics-layer mechanics as individuals (energy cost, conflict risk, outcome uncertainty).
- Groups that coordinate more effectively SHOULD have aggregate survival advantages over less coordinated groups.
- Group-level selection MUST NOT be implemented as a separate evolutionary algorithm. It is an emergent consequence of individual-level interactions.
- Failing groups SHOULD experience member departure, resource loss, and eventual dissolution — not instant deletion.

### Importance

Group competition is one of the strongest drivers of organizational complexity. Without inter-group pressure, there is little incentive for groups to develop more sophisticated coordination, defense, or information infrastructure.

## Collapse and Regression

Civilization structures MUST be able to collapse.

### Collapse Triggers

- energy deficit (inflow drops below maintenance cost)
- coordination failure (key organizers die or leave)
- knowledge loss (institutional memory degrades)
- resource exhaustion (local environment depleted beyond recovery)
- conflict (internal or external)
- overextension (activity radius exceeds coordination capacity)

### Collapse Behavior

- Collapse SHOULD be gradual, not instantaneous (except in extreme violence).
- Collapsing organizations SHOULD shed members, lose infrastructure, and lose knowledge progressively.
- Collapse MUST NOT delete the organization's historical record or physical legacy.
- Post-collapse populations SHOULD be able to rebuild, potentially differently, from whatever knowledge and infrastructure survives.

### Dark Ages

If a collapse destroys enough institutional memory, the surviving population may lose capabilities that took generations to accumulate. This is a feature, not a bug. It demonstrates that knowledge maintenance is a real civilizational cost.

## Activity Radius

Activity radius deserves special emphasis because it is OCP's primary civilization scaling variable.

### Definition

Activity radius is the effective distance over which a group can forage, trade, communicate, defend, and project influence.

### Progression

Activity radius grows through:

- better energy efficiency (less cost per unit distance)
- better transport (paths, boats, animal domestication)
- better communication (message runners, signal systems)
- better storage (ability to sustain remote operations)

### Consequences

As activity radius grows:

- more resources become accessible
- more groups enter interaction range
- coordination complexity increases
- information infrastructure becomes critical
- cultural contact and conflict increase
- civilization propagation speed rises sharply

Activity radius is what connects the intimate scale of individual life to the macro scale of civilizational interaction.

## Observation Metrics

The engine SHOULD track emergence-relevant metrics for research and analysis:

### Recommended Metrics

- energy surplus distribution (Gini coefficient or equivalent)
- population clustering index
- cooperation frequency between non-kin
- knowledge diversity across populations
- behavioral divergence between isolated groups
- infrastructure persistence (structures surviving beyond their builders)
- activity radius estimates per detected group
- organizational complexity indicators (role differentiation, resource flow patterns)

These metrics are for observation, not for game scoring. They tell the researcher whether emergence is happening and where.

## Constitutional Compliance

This RFC is subordinate to RFC-0001 Universe Constitution.

### Law 0: Persistence

- civilization collapse does not end the world

### Law 1: Legacy Persists

- collapsed civilizations leave infrastructure, knowledge traces, and cultural artifacts

### Law 2: Time Is Irreversible

- civilizational history cannot be rewritten

### Law 3: Causality

- every organizational pattern has traceable origin in individual actions

### Law 10: Entropy

- organizations decay without maintenance, creating ongoing coordination cost

## Phase 1 Implementation Guidance

Phase 1 is pre-civilization. The goal is not to produce kingdoms but to produce the conditions from which proto-civilization can emerge.

A good Phase 1 would include:

- detection of persistent spatial clustering
- detection of repeated cooperative interactions
- surplus tracking at individual and group levels
- behavioral divergence measurement between geographically separated populations
- basic infrastructure persistence tracking
- no civilization templates, no organization objects, no governance mechanics

If Phase 1 produces stable cooperating groups with surplus, knowledge accumulation, and behavioral differentiation, the preconditions for civilization exist.

## Open Questions

- What is the minimum population density required before emergent organization becomes likely?
- Should the engine actively label detected patterns (risking reification) or only compute metrics (risking invisibility)?
- How should the boundary between "group" and "civilization" be drawn for observation purposes, if at all?
- What observation metrics best predict the transition from band-level to settlement-level organization?
- How long (in simulated time) should Phase 1 run before concluding that emergence conditions are insufficient?

## Future Dependencies

The following RFCs depend on or interact with this one:

- `RFC-0008 Story Engine`
- `RFC-0009 Player Protocol`
- `RFC-0010 Economy Protocol`

## Conclusion

The hardest discipline in OCP is not building complex systems. It is resisting the urge to build them.

Civilization emergence means watching, measuring, and adjusting conditions — never reaching in and placing the pieces. If the laws are right and the conditions are sufficient, something will organize. If nothing organizes, the laws or conditions need adjustment, not a civilization template.

The search is the point.
