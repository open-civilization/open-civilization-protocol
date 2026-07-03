# RFC-0002 Energy System

## Status

Draft

## Summary

This RFC defines the energy model for OCP.

Energy is treated as the first variable of civilization because survival, mobility, storage, production, organization, and long-range coordination all depend on it.

The purpose of this RFC is not to produce a perfect thermodynamic simulation. Its purpose is to give OCP a shared accounting model for:

- energy capture
- energy storage
- energy transport
- energy conversion
- energy consumption
- energy loss

If physics defines what exists, the energy system defines what can be sustained.

## Motivation

Many simulation projects talk about economy, technology, or social structure before defining how energy actually enters the system.

That creates hidden magic:

- labor with no caloric source
- production with no fuel
- transport with no movement cost
- cities with no maintenance burden
- technology that improves output without upstream input

OCP cannot search honestly for possible civilizations unless it can answer a simple question:

Where does the usable energy come from, and what does it cost to turn that energy into survival or power?

## Goals

This RFC defines:

- the role of energy as a cross-layer variable
- the minimal energy accounting model for Phase 1
- energy states and transitions
- energy behavior at individual, household, group, and civilization scales
- how energy links `Physics`, `Life`, and later `Civilization`

## Non-Goals

This RFC does not define:

- exact real-world units for all future eras
- advanced electricity systems
- industrial thermodynamics
- complete macroeconomics
- all future energy technologies

The Phase 1 requirement is not maximum realism.

It is minimum honest accounting.

## Architectural Position

Energy spans multiple layers:

```text
Universe
    ↓
Physics
    ↓
Energy
    ↓
Life
    ↓
Civilization
```

This RFC is conceptually between `Physics` and `Life`, but it also acts as a shared protocol surface for later civilization mechanics.

### Layer Responsibilities

- `Universe` constrains energy through constitutional conservation
- `Physics` exposes energy-bearing environments and resources
- `Energy` defines accounting and transitions
- `Life` acquires and spends energy to survive and act
- `Civilization` improves capture, storage, transport, conversion, and utilization

## Normative Intent

The key words "MUST", "MUST NOT", "SHOULD", and "MAY" in this document are to be interpreted as binding protocol terms.

## First Principle

Energy is not flavor.

Energy is the substrate of action.

Any system that acts without energy cost, or scales without energy throughput, is either incomplete or constitutionally suspect.

## Design Principles

The energy model SHOULD prefer:

- conservation over convenience
- explicit flows over invisible bonuses
- bottlenecks over magical abundance
- losses over perfect efficiency
- local constraints over global free access

## Energy Roles Across Scales

OCP should model energy as a variable that appears differently at different scales while still obeying one accounting logic.

### Individual Scale

Examples:

- basal maintenance
- calories
- stamina
- temporary reserves

### Household Scale

Examples:

- food storage
- fuel storage
- tools that improve conversion efficiency

### Group Scale

Examples:

- shared granaries
- domesticated biomass
- communal labor capacity

### Civilization Scale

Examples:

- energy capture rate
- storage capacity
- transport efficiency
- conversion efficiency
- utilization efficiency
- energy density access

## Core Energy Flow

Civilization development in OCP can be framed as improvement in this chain:

```text
Capture
    ↓
Store
    ↓
Transport
    ↓
Convert
    ↓
Utilize
```

Every later civilization advantage should be explainable through one or more improvements in this chain.

## Energy Sources

All usable energy MUST trace back to modeled sources.

### Source Categories

Phase 1 SHOULD support or reserve space for categories such as:

- solar
- biological
- chemical
- geothermal
- tidal

Not all categories must be active in Phase 1, but the protocol must assume energy comes from sources, not narrative privilege.

### Phase 1 Practical Focus

Phase 1 will likely concentrate on:

- edible biomass
- fire-capable biomass
- stored food energy
- direct bodily labor

## Energy States

The protocol SHOULD distinguish between different states of usable energy.

### Suggested State Types

- ambient energy
- accessible raw energy
- stored energy
- transportable energy
- convertible energy
- usable work capacity

These are not necessarily separate database tables. They are conceptual distinctions required for honest simulation.

## Energy Capture

Energy capture is the process by which agents or systems make ambient or environmental energy usable.

### Examples

- foraging edible plants
- hunting animals
- fishing
- gathering fuel wood
- harvesting crops in later phases

### Requirements

- capture MUST depend on location and environment
- capture MUST consume time and often effort
- capture SHOULD be uncertain or variable where appropriate
- capture MUST be limited by local availability

## Energy Storage

Storage is the difference between immediate survival and durable civilization.

### Meaning

Without storage, agents are locked to short cycles of acquisition and consumption.

With storage, they can survive scarcity, coordinate labor, and accumulate complexity.

### Requirements

- stored energy MUST be representable
- storage SHOULD have limits
- storage SHOULD be vulnerable to spoilage, theft, decay, or conversion loss
- storage quality SHOULD matter, not just storage quantity

### Examples

- body fat
- dried food
- granaries
- fuel piles

## Energy Transport

Transport moves usable energy through space.

This is a major civilization lever because energy trapped in one place is not fully usable elsewhere.

### Requirements

- transport MUST incur spatial cost
- transport SHOULD incur time cost
- transport MAY incur loss, spoilage, or carrying constraints
- transport capacity SHOULD limit coordination scale

### Examples

- carrying food by hand
- moving wood
- driving livestock
- later, wagon or ship transport

## Energy Conversion

Conversion transforms one energy form into another usable form.

### Examples

- food into labor
- wood into heat
- labor into built structure
- later, animals into traction power

### Requirements

- conversion MUST preserve conservation logic
- conversion SHOULD include inefficiency or waste
- tools or institutions MAY improve conversion efficiency

## Energy Utilization

Utilization is where stored or converted energy becomes action.

### Examples

- bodily movement
- construction
- maintenance
- food preparation
- heating
- defense
- communication effort

### Requirements

- meaningful actions SHOULD have energy cost
- maintenance SHOULD have ongoing energy burden
- civilization complexity SHOULD increase baseline utilization demand

## Energy Loss

Perfect efficiency is forbidden by design.

### Loss Modes

- metabolic loss
- spoilage
- transport loss
- conversion waste
- idle dissipation

### Importance

Loss is not a bookkeeping nuisance.

Loss is one of the reasons scale, storage, and coordination are hard.

## Energy Accounting Model

Phase 1 requires a minimal but consistent accounting model.

### Minimum Accounting Requirements

- every acting resident SHOULD have maintenance cost
- every physically meaningful action SHOULD have energy cost
- every stored reserve SHOULD change over time through use, gain, decay, or transfer
- every major group store SHOULD be queryable
- major energy transitions SHOULD be auditable

### Recommended Mental Model

Think in terms of:

- inflow
- reserve
- outflow
- loss

If inflow stays below total outflow plus loss for long enough, collapse pressure should emerge naturally.

## Individual Energy Budget

Phase 1 life simulation SHOULD include a minimal per-resident energy budget.

### Recommended Components

- baseline maintenance cost
- temporary action budget
- reserve state
- exhaustion state
- starvation threshold

This allows residents to face real tradeoffs between movement, work, risk, and rest.

### Phase 1 Calibration — Caloric Units

Phase 1 uses real kilocalorie (kcal) units for the individual energy budget, rather than an abstract 0-100 scale, so mortality thresholds are physically interpretable:

| Quantity                    | Value        | Meaning |
|------------------------------|--------------|---------|
| Reserve capacity (`MAX_ENERGY`) | 3000 kcal   | Full, well-fed caloric reserve |
| Erosion threshold             | 2000 kcal   | Below this, health begins to erode (graduated, not a cliff) |
| Death-zone threshold          | 1500 kcal   | Below this, erosion becomes severe |
| Baseline daily metabolic cost  | 60 kcal/tick (before season/technology modifiers) | Scales inversely with the endurance trait |

Each simulation tick represents one full day-night cycle. Upkeep is computed as a day component and a night component (0.8× and 1.2× the season's multiplier respectively, averaging back to exactly the season multiplier), so that:

- **Season** shapes the baseline multiplier applied to both day and night loss (winter is the dominant seasonal cost; other seasons carry mild, physically-motivated variation).
- **Day/night** gives technologies a specific physical lever: fire reduces nighttime loss specifically (it does nothing about daytime heat); shelter reduces the season multiplier uniformly (it blocks exposure day and night); clothing reduces the resident's personal metabolic rate uniformly (it is worn constantly).
- **Health erosion** is a direct, graduated function of the caloric reserve alone — there is no separate "cold damage" formula. Cold, hunger, and malnutrition all work through the same physical quantity.

Foraging conversion (harvest → kcal) is calibrated so that a resident foraging under normal conditions comfortably sits above the 2000 kcal erosion threshold — "well-fed" is the achievable, common state, not a rare surplus. Dipping into the erosion or death bands should reflect genuine scarcity (winter, overpopulation, drought), not routine operation. See RFC-0004 Mortality Factors and RFC-0006 for how food storage, shelter, clothing, and fire knowledge each independently reduce these losses.

## Group and Settlement Energy Budget

As coordination emerges, energy accounting SHOULD scale upward.

### Group-Level Concerns

- shared food stores
- fuel stores
- labor mobilization potential
- maintenance burden
- surplus versus deficit

This is the bridge from survival behavior to proto-civilization behavior.

## Surplus

Surplus is a central concept and SHOULD be modeled explicitly.

### Meaning

Surplus is the portion of captured and stored energy that remains after maintenance and immediate survival costs.

### Why It Matters

Surplus enables:

- larger groups
- specialization
- infrastructure
- long-range movement
- experimentation
- memory institutions

Without surplus, life loops remain short and local.

## Scarcity

Scarcity is not only "not enough food."

It is any condition where energy capture, storage, transport, or conversion is insufficient for desired action.

### Effects of Scarcity

- migration pressure
- conflict pressure
- reduced maintenance
- collapse of coordination
- abandonment of infrastructure

Scarcity should be able to propagate upward into social structure without needing scripted drama.

## Efficiency

Efficiency gains are allowed, but they MUST NOT be confused with free energy.

### Requirements

- better tools MAY improve yield from the same source
- better organization MAY reduce waste
- better storage MAY preserve more captured value
- better transport MAY extend useful reach

All efficiency gains still depend on real upstream energy.

## Energy Density

Different sources or stores may provide different usable concentration.

Energy density is important because it shapes mobility, military reach, storage practicality, and infrastructure possibilities.

Phase 1 MAY treat this abstractly, but the concept SHOULD be preserved.

## Interfaces to Physics

The energy system depends on the physics layer for:

- local resource availability
- environmental productivity
- movement cost
- storage location
- transport path constraints

Energy accounting MUST NOT float free from space.

## Interfaces to Life

The life layer SHOULD be able to:

- inspect local energy opportunities
- spend energy to act
- gain energy from successful acquisition
- suffer penalties from deficit or exhaustion

Life decisions become meaningful when actions are energy-constrained.

## Interfaces to Civilization

Later civilization systems SHOULD be able to build on energy accounting for:

- surplus pooling
- infrastructure maintenance
- logistics
- specialization
- long-distance exchange
- state-scale fragility or power

This is one reason energy should be defined before advanced politics or economics.

## Constitutional Compliance

This RFC is subordinate to `RFC-0001 Universe Constitution`.

It directly supports:

### Law 3: Causality

- energy gains and losses MUST have causal sources

### Law 4: Energy Conservation

- usable energy MUST trace to modeled origin and transformation

### Law 5: Matter Conservation

- many energy pathways depend on depletable material resources

### Law 10: Entropy

- stores decay
- structures require maintenance
- idle systems lose usable value

## Phase 1 Implementation Guidance

Phase 1 SHOULD stay intentionally small.

A good first version would include:

- per-resident maintenance cost
- local food-energy acquisition
- simple stored reserves
- movement energy cost
- action energy cost
- spoilage or decay
- small shared store abstraction

That is enough to make survival, migration, and local organization physically meaningful.

## Open Questions

- ~~What is the best internal unit for Phase 1 accounting?~~ Resolved: kilocalories (see Phase 1 Calibration above), for physical interpretability.
- ~~Should food, fuel, and bodily reserves share one abstract energy unit or separate ones?~~ Resolved for Phase 1: bodily caloric reserve (`energy`, kcal) is distinct from standing biomass and leftover food caches (a separate matter-denominated currency converted to kcal only at the moment of consumption).
- How much uncertainty should energy capture include?
- When should storage quality become distinct from storage quantity?
- What is the minimum group-store model needed before tribes emerge?

## Future Dependencies

The following RFCs depend directly on this one:

- `RFC-0004 Life Engine`
- `RFC-0005 AI Decision`
- `RFC-0007 Civilization Emergence`
- `RFC-0009 Player Protocol`
- `RFC-0010 Economy Protocol`

## Conclusion

Energy is the first variable because it turns world possibility into lived constraint.

If OCP can account honestly for how energy is captured, stored, moved, converted, and spent, then survival pressure, surplus, scarcity, and civilization growth can emerge from the world instead of being authored from above.
