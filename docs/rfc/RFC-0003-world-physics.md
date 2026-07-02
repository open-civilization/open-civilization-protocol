# RFC-0003 World Physics

## Status

Draft

## Summary

This RFC defines the objective world substrate that sits below life and civilization in OCP.

`World Physics` is not a full scientific simulator. It is the minimum physically grounded reality layer required to make emergence honest.

Its purpose is to answer:

- what exists in the world
- where it exists
- how it changes over time
- what limits movement, access, extraction, and construction
- how higher layers interact with reality without bypassing it

## Motivation

Without a physics layer, the project risks becoming a disguised scripting system.

That failure mode usually appears in forms such as:

- life directly mutating resources with no spatial constraint
- civilizations treating distance as flavor text instead of cost
- AI succeeding because the engine wants a story, not because the world allows it
- energy, matter, and access being resolved by convenience

OCP needs a reality layer strong enough to constrain life, shape civilization, and preserve causal integrity, but small enough to implement in Phase 1.

## Goals

This RFC defines:

- the minimal physical world model for OCP
- the relationship between space, terrain, resources, environment, and time
- movement and reachability constraints
- the interaction boundary between `Life` and `Physics`
- the abstraction policy for Phase 1

## Non-Goals

This RFC does not attempt to define:

- a high-fidelity scientific simulation
- continuous fluid dynamics
- molecular chemistry
- advanced structural engineering
- full weather realism
- a complete ecology simulator

OCP physics exists to support emergence-relevant constraints, not to simulate everything in nature.

## Architectural Position

The OCP world stack is:

```text
Universe
    ↓
Physics
    ↓
Life
    ↓
Civilization
    ↓
Player
```

`Universe` defines constitutional law.

`Physics` defines objective reality under that law.

`Life` perceives and acts within physics.

`Civilization` organizes action within physical limits.

`Player` may influence outcomes only through protocol-approved surfaces and MUST NOT bypass physics directly.

## Normative Intent

The key words "MUST", "MUST NOT", "SHOULD", and "MAY" in this document are to be interpreted as binding protocol terms.

## Design Principles

The physics layer SHOULD prefer:

- explicit constraints over invisible convenience
- space over placeless state
- cost over teleportation
- depletion over infinite supply
- abstraction with consequence over fake realism

## World Primitives

Phase 1 world physics SHOULD be built from a small set of primitives.

### Required Primitive Categories

- `space`
- `time`
- `terrain`
- `water`
- `resource`
- `biomass`
- `temperature`

### Optional or Later Primitives

- `artifact`
- `soil fertility`
- `weather fronts`
- `animal populations`
- `material layers`

The first implementation SHOULD resist adding many specialized primitives too early.

## Spatial Model

The world MUST be spatially explicit.

Entities do not exist only in abstract tables. They exist somewhere.

### Phase 1 Recommendation

Phase 1 SHOULD use a discrete map model such as:

- square grid
- hex grid

The exact topology is not constitutional, but explicit locality is required.

### Minimum Cell Properties

Each spatial cell SHOULD expose at least:

- terrain type
- relative height or elevation class
- water access status
- biomass level
- temperature band
- movement cost
- local resource inventory

### Consequences

- Nearby and distant are materially different states.
- Location affects survival, access, and coordination.
- Discovery and reachability become real mechanics rather than metadata.

## Time Model

Physics MUST advance through ordered simulation time.

### Requirements

- The world MUST have monotonic time progression.
- Physical changes MUST occur at identifiable times or ticks.
- Environmental regeneration and decay MUST be time-dependent.

### Phase 1 Guidance

The engine MAY use abstract ticks, but tick semantics SHOULD be clear enough to support:

- movement cost
- resource regeneration
- energy consumption
- environmental change

## Terrain Model

Terrain defines basic movement and habitation constraints.

### Minimum Terrain Expectations

Terrain SHOULD affect:

- movement difficulty
- water access
- shelter potential
- resource availability
- habitability

### Examples

Useful early terrain classes MAY include:

- plains
- forest
- river
- lake
- coast
- mountain
- desert

The protocol does not require these exact labels, but it does require meaningful spatial differentiation.

## Resource Model

Resources MUST be embedded in space and subject to access, depletion, and transformation.

### Resource Categories

Phase 1 SHOULD distinguish at least three broad categories:

- energy-source resources
- material resources
- ecological resources

### Examples

- solar exposure
- biomass
- wood
- stone
- water
- edible plants
- fish
- prey animals

### Resource Requirements

- Resources MUST exist at locations or in transportable inventories.
- Resources MUST be obtainable only through physically valid interactions.
- Resources MUST be consumable, transferable, transformable, recoverable, or exhaustible as appropriate.
- Resource abundance MUST NOT be globally implicit if local scarcity matters.
- The world MUST contain simultaneous zones of relative abundance and relative scarcity. Uniform resource distribution across all reachable space is not permitted.
- Resource abundance SHOULD vary over time, such as seasonally or cyclically, so that storage, migration, and trade remain ongoing strategic concerns rather than one-time optimizations.

### Scarcity Gradient Rationale

A world that is uniformly abundant removes any incentive for coordination, storage, or exchange. A world that is uniformly scarce collapses populations before organization can form. The gradient between abundant and scarce zones, and its variation over time, is what gives migration, trade, and surplus-driven behavior a reason to exist.

## Carrying Capacity and Malthusian Equilibrium

The world MUST have a finite carrying capacity determined by total resource regeneration relative to population energy demand.

### Carrying Capacity Definition

Carrying capacity is computed from the annual average of total biomass regeneration across all passable cells, divided by the effective per-resident energy cost:

```text
avg_season_mult = mean(spring, summer, autumn, winter multipliers)
total_regrow = sum(cell_regrow * avg_season_mult) for all passable cells
carrying_cap = total_regrow / (baseline_energy_cost * extraction_inefficiency)
```

### Population Pressure

Population pressure is the ratio of current living population to carrying capacity:

```text
pressure = population / carrying_capacity
```

- When pressure < 0.8: population can grow, surplus is possible, reproduction succeeds regularly.
- When pressure ≈ 1.0: equilibrium zone. Deaths roughly match births. Surplus is marginal.
- When pressure > 1.0: Malthusian crisis. Food per capita drops below survival needs.

### Malthusian Amplification

When pressure exceeds 1.0, the following effects MUST intensify proportionally to pressure²:

- Disease probability increases (malnutrition weakens immunity).
- Conflict and raiding probability increases (desperate individuals attack others for food).
- Starvation rate accelerates (less food per person per tick).

Additionally, two dedicated Malthusian mechanisms activate:

- **Malnutrition**: when pressure > 1.0, ALL residents lose health at a rate of `2.0 × (pressure − 1.0)²` per tick, representing chronic food shortage affecting the entire population.
- **Fertility suppression**: when pressure > 0.8, reproduction probability drops as `1.0 / (1.0 + (pressure − 0.8) × 3)`. At pressure 1.3, fertility is ~40% of baseline. This models reduced fecundity under nutritional stress.

This creates a natural population ceiling: growth overshoots carrying capacity → malnutrition and fertility suppression → population stabilizes or crashes back to sustainable levels.

### Carrying Capacity Advancement

The carrying capacity ceiling is NOT fixed forever. It can only be raised by emergent changes that alter the terms of the equation:

- Agricultural techniques (if they emerge) increase effective regrow rates.
- Food storage (if it emerges) smooths seasonal variation.
- Tool use (if it emerges) increases foraging efficiency.
- Trade (if it emerges) redistributes surplus from abundant to scarce zones.

None of these are designed. They must arise from the interaction of life, knowledge, and environment. Until they do, the Malthusian ceiling holds.

### Phase 1 Calibration

Phase 1 uses a 60×80 map with carrying capacity ≈ 170 residents (extraction inefficiency multiplier = 8.0). Initial population is 120, scattered across all three climate zones.

| Terrain   | Biomass Cap | Regrow Rate |
|-----------|------------|-------------|
| Plains    | 30         | 0.7         |
| Forest    | 45         | 1.0         |
| River     | 25         | 0.6         |
| Lake      | 15         | 0.4         |
| Mountain  | 6          | 0.08        |
| Desert    | 3          | 0.02        |
| Coast     | 28         | 0.6         |

### Climate Zones

The map is divided into three horizontal climate bands (top to bottom):

| Zone      | Rows     | Season Multipliers                          | Winter Upkeep | Cold Threshold | Cold Damage |
|-----------|----------|---------------------------------------------|---------------|----------------|-------------|
| Cold      | 0–26     | spring 1.0, summer 0.7, autumn 0.2, winter 0.005 | 5.0×         | 50 energy      | 30 hp/tick  |
| Temperate | 27–53    | spring 1.5, summer 1.0, autumn 0.5, winter 0.02  | 3.0×         | 35 energy      | 20 hp/tick  |
| Tropical  | 54–79    | spring 1.1, summer 1.0, autumn 0.9, winter 0.05  | 2.0×         | 20 energy      | 8 hp/tick   |

This creates a **survival bottleneck in winter**:

- **Tropical**: reduced food in winter (0.05×). Without food storage knowledge, 70% population dies.
- **Temperate**: severe winter (0.02×). Storage knowledge is critical for survival. Non-storage population: 95%+ death rate.
- **Cold**: uninhabitable (0.005×). Only viable with advanced storage knowledge and technical adaptation.

In Phase 1, the cold zone depopulates within the first few years. The temperate zone supports marginal populations. The tropical zone becomes the population center. Expansion into colder zones requires emergent adaptations (food storage, shelter, clothing) that raise effective winter survival — a key milestone in civilization emergence.

Terrain generation varies by climate zone: cold zones have more mountains and fewer forests; tropical zones have more forests, rivers, and coastline; temperate zones use the baseline distribution.

### Terrain Hazards

Harsh terrain MUST impose injury risk during movement, independent of energy cost:

- Mountain: 8% injury chance per crossing.
- River: 6% injury chance per crossing.
- Desert: 5% injury chance per crossing.
- Coast: 2% injury chance per crossing.

Injury risk is reduced by the resident's endurance trait. Hazard damage ranges from 8–25 health points.

## Water Model

Water is important enough in early civilization search that it SHOULD be treated as a first-class environmental constraint.

### Minimum Water Behaviors

- cells MAY contain water access states
- water access SHOULD influence habitability
- water access SHOULD influence food strategies
- water barriers MAY affect movement and separation

Full hydrology is not required in Phase 1, but water must matter.

## Biomass and Ecological Availability

The physics layer SHOULD provide a simple model for local living productivity.

This may be represented through:

- edible biomass
- regrowth rate
- huntable abundance
- forage potential

### Requirements

- biomass SHOULD regenerate over time where conditions permit
- extraction SHOULD reduce immediate local availability
- local survival capacity SHOULD differ by environment

This allows life to face real carrying constraints before a full ecology system exists.

## Temperature and Environment

The environment MUST be more than decorative background.

### Phase 1 Environmental Factors

At minimum, physics SHOULD expose some combination of:

- temperature band
- seasonal variation
- day-night effects
- regeneration cycles

### Purpose

These variables create adaptation pressure, migration pressure, and non-uniform survival conditions.

## Environmental Dynamics

The world SHOULD change even when no intelligent actor intervenes.

### Expected Dynamic Processes

- resource regrowth
- resource depletion
- temperature shifts
- seasonal shifts
- environmental decay

### Implication

The world is not a frozen board.

Life and civilization must adapt to moving conditions rather than exploit static tables forever.

## Movement and Reachability

Movement MUST incur cost and constraint.

Reachability is a foundational civilization variable, not a cosmetic feature.

### Requirements

- movement MUST depend on spatial adjacency or transport links
- movement MUST incur time cost
- movement SHOULD incur energy or fatigue cost
- terrain SHOULD influence movement feasibility and price
- barriers SHOULD create real separation

### Protocol Importance

If all known locations are instantly reachable, then:

- information speed loses meaning
- trade loses friction
- migration loses structure
- activity radius becomes fake

That outcome is incompatible with OCP goals.

## Physical Interaction Rules

`Life` and other higher layers MUST interact with the world through physics-resolved actions rather than direct state mutation.

### Example Interaction Types

- move
- gather
- drink
- hunt
- fish
- rest
- build
- maintain

### Resolution Model

Higher layers MAY propose intent.

Physics MUST determine whether the world permits that intent, and what it costs.

For example:

- a resident proposes "fish"
- physics checks location, water access, available biomass, time cost, and energy cost
- physics returns success, failure, or partial success with state changes

## Construction and Maintenance

The physics layer SHOULD support the idea that built structures are costly and persistent, not magical flags.

### Requirements

- construction SHOULD require material input, location, and time
- structures SHOULD occupy or affect space
- maintained structures MAY persist or improve
- neglected structures SHOULD decay over time

This section directly supports later legacy and entropy behavior.

## Decay

The physics layer SHOULD expose basic decay behavior even before advanced civilization systems exist.

### Examples

- stored material spoilage
- infrastructure quality loss
- habitat degradation
- abandoned construction decline

Decay is one of the ways physics helps implement `Law 10: Entropy`.

## Abstraction Policy

OCP should be explicit about what is modeled and what is intentionally abstracted.

### Phase 1 Must Be Explicit About

- location
- time progression
- movement cost
- resource distribution
- resource extraction
- basic environmental variation
- decay and regeneration

### Phase 1 May Abstract

- exact fluid mechanics
- exact chemistry
- fine-grained metallurgy
- complex weather systems
- detailed population ecology
- sub-cell material simulation

The correct standard is not realism for its own sake.

The correct standard is whether abstraction preserves emergence-relevant constraints.

## Interfaces Exposed Upward

The physics layer SHOULD expose a clear protocol surface to higher systems.

### Minimum Upward Capabilities

- query local environment
- query nearby reachable cells
- query accessible resources
- submit a physical interaction intent
- receive resolved outcomes and costs
- receive world-change events

### Separation Requirement

Higher layers MUST NOT directly edit physical truth when a physics interface exists for that domain.

## Constitutional Compliance

This RFC is subordinate to `RFC-0001 Universe Constitution`.

Physics implementations MUST comply with the following constitutional laws in particular:

### Law 3: Causality

- physical events MUST have causal antecedents
- extraction, movement, and construction MUST be traceable

### Law 4: Energy Conservation

- physical output MUST depend on upstream energy sources and costs

### Law 5: Matter Conservation

- material stocks MUST deplete, move, transform, or regenerate through modeled processes

### Law 9: Information Has Speed

- spatial separation and movement limits help enforce communication limits

### Law 10: Entropy

- objects, stores, and structures SHOULD decay without maintenance

## Phase 1 Implementation Guidance

Phase 1 SHOULD optimize for a small but honest world.

That suggests:

- discrete map cells
- simple terrain classes
- local resource inventories
- simple regrowth and decay
- explicit movement cost
- small set of physical interaction types

This is enough to produce meaningful scarcity, migration pressure, and settlement pressure without overbuilding the engine.

## Open Questions

- Should Phase 1 use square grid or hex grid?
- Should water be a terrain class, a cell attribute, or a lightweight subsystem?
- How much climate variation is necessary before adaptation becomes meaningful?
- Should biomass be a single abstract quantity or a few separate food-source classes?
- What is the minimum structure model needed to support early legacy effects?

## Future Dependencies

The following RFCs depend directly on this one:

- `RFC-0002 Energy System`
- `RFC-0004 Life Engine`
- `RFC-0005 AI Decision`
- `RFC-0007 Civilization Emergence`
- `RFC-0009 Player Protocol`

## Conclusion

World physics is what makes OCP a place instead of a prompt.

If space, cost, depletion, and reachability are real, then life must negotiate reality.

If life must negotiate reality, civilization can emerge honestly rather than being authored from above.
