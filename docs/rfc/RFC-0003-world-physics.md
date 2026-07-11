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

- Agricultural techniques and animal husbandry (implemented — see below) increase effective regrow rates.
- Food storage (implemented — see RFC-0004) smooths seasonal variation.
- Tool use (if it emerges) increases foraging efficiency.
- Trade (if it emerges) redistributes surplus from abundant to scarce zones.

None of these are designed as unlocks. They arise from the interaction of life, knowledge, and environment (see RFC-0006 for the acquisition pathway). Until they emerge in a given lineage or region, the Malthusian ceiling holds.

### Domestication and Land Improvement

Cells carry a `cultivation` state (0 to 1) representing sustained agricultural or pastoral improvement, distinct from `biomass` (the immediate standing stock of food). Cultivation is not seeded or scripted — it accumulates only when a resident who holds the relevant knowledge (`crop_cultivation` or `animal_husbandry`, see RFC-0006) works a cell whose terrain and climate zone are physically suited to that activity.

**Terrain suitability** (a physical property of the land, like `biomass_cap`):

| Terrain  | Farming Suitability | Grazing Suitability |
|----------|---------------------|----------------------|
| Plains   | 1.0                 | 0.8                  |
| River    | 0.7                 | 0.0                  |
| Forest   | 0.2                 | 0.0                  |
| Mountain | 0.0                 | 1.0                  |
| Desert   | 0.0                 | 0.3                  |

**Zone suitability** (why cold zones graze and temperate zones farm, not the reverse):

| Zone      | Farming Suitability | Grazing Suitability | Rationale |
|-----------|----------------------|-----------------------|-----------|
| Cold      | 0.1                  | 1.0                   | Short growing season unsuited to crops; open cold-tolerant terrain suits herding |
| Temperate | 1.0                  | 0.25                  | Long enough growing season and fertile plains favor cultivation |
| Tropical  | 0.0                  | 0.0                    | Baseline foraging is already abundant enough that domestication provides no discovered advantage in Phase 1 — tropical populations remain at natural primary production |

A cell's effective terrain suitability is `terrain_suitability × zone_suitability`. Since tropical zone suitability is 0 for both activities, domestication cannot take hold there regardless of terrain — this is a physical constraint of the model, not a scripted gate.

**Effect on productivity**: a cultivated cell's biomass regrowth is multiplied by `1 + cultivation × 7.0 × ag_tech_mult`, so land at full cultivation and baseline technology regenerates up to 8× faster than wild land of the same terrain — before any further agricultural technology is layered on (see Agricultural Technology Ladder below). This bonus feeds directly into the carrying capacity formula (see above), so as cultivation spreads across a region, that region's sustainable population rises — this is the mechanism by which domestication multiplies a zone's baseline energy output, as opposed to a one-time unlock.

**Entropy**: cultivation decays slowly when a cell is not actively worked, so abandoned farmland or pasture reverts toward wild land over time (RFC-0001 Law 10). Sustaining an improved landscape requires an ongoing, living population of knowledge-holders, not a permanent flag. `ag_tech_mult` (below) is the one exception: once a plot has been worked with a given technology, that ceiling never decreases — technique embedded in how land is worked doesn't un-happen even if the land itself later reverts to wild, only its realized cultivation level does.

The same entropy principle applies to `leftover` — food already harvested but not yet consumed (scavenged surplus, stored food dropped or abandoned on a cell). Each tick it decays at `5% × season_mult`, i.e. faster in productive seasons and slower through winter, same seasonal multiplier as regrowth. Without this, scavengeable surplus would accumulate indefinitely and silently inflate the effective carrying capacity above what the land actually, sustainably produces — real stockpiles rot, get taken by scavengers, or are stolen by non-residents, and this term stands in for all three without modeling them individually.

### Agricultural Technology Ladder

Energy density per unit of cultivated land is not a single fixed multiplier — it is a growing ceiling (`Cell.ag_tech_mult`, starting at 1.0) that ratchets upward as a lineage or region accumulates real agricultural technology, mirroring the historical trajectory from early domestication through irrigation, selective breeding, and industrial-era fertilizer/pesticides (the "Green Revolution," the single largest jump in yield per area in human history). Each tier is discovered independently through the Experiment pathway (RFC-0006) and stacks multiplicatively.

**1. Crop and livestock archetypes** (zoology/botany-flavored, assigned randomly on domestication): when `crop_cultivation` or `animal_husbandry` is first successfully domesticated, a specific archetype is chosen at random, weighted by climate zone — which staple a population ends up with is a random outcome of what was locally available to experiment with, not a designed choice:

| Crop archetype | Energy density | Favored zone | Real-world analogy |
|---|---|---|---|
| Wheat | 1.4× | Temperate | The historically dominant temperate staple, precisely because of superior caloric yield density |
| Rice | 1.3× | Temperate (some tropical) | Water-intensive but very high-yield where irrigation exists |
| Soybean | 1.15× | Temperate (some tropical) | Secondary legume staple, versatile but lower density than the grains |
| Fruit | 1.0× | Tropical | Perennial tree/vine crops — reliable yield without needing seasonal replanting |
| Sweet potato | 0.55× | Cold (rare) | A late, low-yield crop only reachable once cold-zone farming suitability (already near-zero) is overcome — deliberately marginal, not a substitute for pastoralism there |
| Corn | 0.6× | Cold (rare) | Same rationale as sweet potato — a rare, low-density cold-zone crop rather than a staple |

| Livestock archetype | Energy density | Favored zone | Real-world analogy |
|---|---|---|---|
| Sheep | 0.9× | Cold | Hardiest and earliest-domesticated, thrives on marginal grazing land |
| Cattle | 1.3× | Cold | Needs richer pasture but yields the most meat per animal |
| Horse | 0.85× | Cold | A later, rarer, more prized domesticate — steppe pastoralism |

Replaced the earlier generic `grazer`/`browser` abstraction with three named cold-zone species
on direct request, same reasoning as the crop table above: which specific animal a herder ends
up with is a weighted-random outcome of local suitability (`_pick_archetype`), not an authored
choice. All three are cold-zone-exclusive under the existing zone exclusivity (only `cold` has
`grazing_suitability > 0`); a temperate/tropical livestock archetype is a separate, not-yet-
implemented ask that needs its own zone-exclusivity change first (raising tropical's
`grazing_suitability` above 0, currently 0 like temperate's), not just another table entry.

**Mineral resources** are a separate, non-food resource class — physical goods to trade or have
raided rather than an energy source. Cold-zone-dominant real geology (coal seams, iron-bearing
rock, and oil deposits concentrate in specific rock formations, not arable land), discovered
through the identical Experiment pathway as crop/livestock domestication (a new `mining`
knowledge type, gated by mountain/desert terrain suitability):

| Mineral archetype | Favored zone | Real-world analogy |
|---|---|---|
| Coal | Cold (some temperate) | The dominant pre-industrial mineral fuel, concentrated in specific cold/mountainous geology |
| Iron ore | Cold (some temperate) | Base metal for tools and, later, industrial machinery |
| Oil | Cold (some temperate) | Rarer, later-relevant extractive resource |

A resident who discovers `crop_cultivation` and produces more than they can personally consume
(surplus beyond the caloric energy cap) converts the excess into a held stockpile of their
specific crop rather than wasting it; a `mining` holder accumulates their mineral type per tick
worked. Held resources decay slowly (same entropy principle as `leftover` food) so stockpiles
don't grow unbounded. See RFC-0007 for how these named resources drive trade and raiding.

**2. Domestication is not guaranteed to succeed.** A "wild variant found" event (the existing discovery roll) only represents *trying* a promising plant or animal — most such attempts fail to become a stable, transmittable domesticate (of the world's ~200,000 plant species, only a few hundred were ever actually domesticated). A second, independent roll (45% chance) determines whether the attempt actually takes; a failure leaves no trace, and the underlying discovery roll keeps trying on subsequent ticks.

**3. Further tiers, each gated on a real prerequisite:**

| Tier | Requires | Multiplier | Rationale |
|---|---|---|---|
| Irrigation | `crop_cultivation` + water-adjacent cell | 1.5× | Water management requires cultivation to already exist and physical access to water |
| Selective breeding | `crop_cultivation` skill ≥ 60 | 1.6× | Generations of choosing better seed/stock requires deep personal mastery, not a novice's first season |
| Fertilizer/pesticides | `writing` + `selective_breeding` | 2.2× | Systematic agricultural science requires record-keeping across seasons and generations — this is deliberately gated behind writing, not population size or a tick count |

A cell's `ag_tech_mult` ratchets up to the highest combination any farmer or herder working it has achieved (crop/livestock archetype × irrigation × breeding × fertilizer, each present or absent) and never decreases. At full stack this represents roughly a 50× yield ceiling over wild foraging of the same terrain (7.0 base cultivation bonus × up to 1.4 archetype × 1.5 irrigation × 1.6 breeding × 2.2 fertilizer) — in the same order of magnitude as the real historical gap between pre-agricultural foraging and industrial farming.

### Phase 1 Calibration

Phase 1 uses a 60×80 map. Initial population is seeded near the environment's natural baseline capacity (~55 residents) and is allowed to find its own equilibrium through births and deaths — the engine does not target a fixed carrying-capacity number, it emerges from terrain, season multipliers, and mortality mechanics.

| Terrain   | Biomass Cap | Regrow Rate |
|-----------|------------|-------------|
| Plains    | 30         | 0.7         |
| Forest    | 45         | 1.0         |
| River     | 25         | 0.6         |
| Lake      | 15         | 0.4         |
| Mountain  | 6          | 0.08        |
| Desert    | 3          | 0.02        |
| Coast     | 28         | 0.6         |

### Island Specialization and Dietary Diversity

Implemented: a large river-island (`_carve_river`, mid-map) is a deliberately distinct economic
zone rather than just more farmland. `Cell.near_island` marks it and its flanking water, which
multiplies fishing suitability (`TERRAIN_FISHING`, 2.5x near the island). Salt has its own
dedicated, deterministic suitability (`SALT_WATER_SUITABILITY`/`SALT_ISLAND_SUITABILITY`,
separate from the generic zone-weighted `MINERAL_ARCHETYPES` pick so it never biases the
coal/iron_ore/oil chance): reachable at *any* water tile, not just near the island, but the
island itself is ten times richer -- salt is a real, findable-anywhere good with a strong
regional concentration, not an exclusive.

Salt isn't food (minerals stay non-caloric/tradeable per the existing model), but now has real
teeth on both sides: holding any multiplies forage gain 1.15x (`SALT_FOOD_BONUS_MULT`, mirroring
its real preservative role), holding none applies a 0.85x penalty (`SALT_DEFICIT_MULT`) rather
than a neutral baseline -- salt is a near-necessity, not a bonus, which is what actually makes
seeking or trading for it matter. Live-tested: this measurably lowers total sustainable
population (a real cost, most of the map doesn't have salt yet at any given time) without
destabilizing births/deaths equilibrium.

This pairs with dietary diversity (`recent_food_types` on Resident, a rolling per-type
last-eaten-tick record bounded to the fixed food vocabulary). Revised from an initial
distinct-archetype-count formula to three real food categories -- crop, meat, fish
(`FOOD_CATEGORY`; salt stays entirely separate, see below) -- since a specific crop_type (wheat
vs rice) doesn't functionally differ enough to matter, only whether the actual food GROUP
varies: `DIET_CATEGORY_MULT` gives 0.7x for one category (including wild-only foraging), 1.2x
for two, 1.5x for all three. Deepening the single-category penalty (making imbalance sting
harder) was tried twice on direct request and reverted both times: 0.55 sent 2 of 3 seeds fully
extinct and pinned the third at 79-250 population; the smaller step to 0.6 still sent 1 of 3
seeds extinct, confirmed via a same-seed A/B control (that exact seed survives fine to pop 648
at 0.7, ruling out "just a fragile seed"), with the other two also running measurably below the
healthy 300-900 baseline. The single-category tier is most residents' baseline forage rate much
of the time, not a rare edge case, so it compounds directly into the population's core energy
budget -- this lever appears to have very little safe headroom below 0.7; a different mechanism
is probably needed to make imbalance sting harder without risking collapse. Salt multiplies on
top of the diet multiplier, separately: 1.15x if held, 0.85x deficit otherwise
(`SALT_FOOD_BONUS_MULT`/`SALT_DEFICIT_MULT` -- a wider 1.3/0.7 spread was tried and reverted
after it collapsed a local test population to 18 residents by tick 800; the two multipliers
compound, so pushing both further apart at once is riskier than it looks). The deficit side was
also tried widened *alone* to 0.8 (bonus untouched at 1.15, isolating it from the earlier
combined attempt) and still isn't safe: one of the same 3 test seeds went fully extinct at tick
541. That seed survives fine under every current baseline value and had already separately
failed under both diet-imbalance attempts above -- a real cross-mechanism signal, not one
fragile seed, that the population's margin for additional tightening on the "eat well" energy
budget is thin right now regardless of which specific multiplier is the lever.
Salt's own suitability is separate again: reachable at any water tile, but the island is ten
times richer, and it's excluded entirely from the cold zone (`SALT_WATER_SUITABILITY`/
`SALT_ISLAND_SUITABILITY`).

**Pressure-gated deepening (the version that actually shipped)**: all three flat-multiplier
attempts above failed by hitting a small/founding population exactly as hard as a large,
established one -- the single-category tier is most residents' baseline state much of the time,
so any flat tightening taxes the population's thinnest, most fragile phase (early growth) just
as much as its most resilient phase (large, past its initial bottleneck). The fix wasn't a
smaller number, it was gating the extra penalty on `Simulation._pressure` (population /
carrying capacity, already computed every tick, see the Malthusian Trap section of RFC-0007):
below `DIET_IMBALANCE_PRESSURE_THRESHOLD` (1.0, i.e. population at or under carrying capacity)
the single-category tier stays at the safe flat 0.7x; above it, an extra penalty ramps in
linearly over `DIET_IMBALANCE_PRESSURE_RAMP` (1.0 pressure-unit) up to
`DIET_IMBALANCE_MAX_EXTRA_PENALTY` (0.15 -- the same magnitude as the 0.55 flat attempt that
failed catastrophically at every pressure level). Verified across the same 3 seeds used for
every prior attempt: zero extinctions, including the one seed that had failed under all three
flat-multiplier attempts above (fully recovered to a healthy trajectory once the founding-phase
penalty was removed). One seed did settle into a lower sustained population plateau once
persistently crowded rather than its usual range -- not a collapse, a real self-limiting
equilibrium, and the intended effect: population pressure is exactly the condition meant to make
a diet-diverse trade partner (see `is_merchant`, RFC-0007) worth the risk of approaching, so a
population that stays comfortably under its ceiling should never feel this tax at all.

Deepened again from 0.15 to 0.2 on direct request, now that the supply side has real teeth
(closed trade-diet loop, boosted crop-surplus production, merchant-seeks-chief) -- same gated
structure untouched (`DIET_IMBALANCE_PRESSURE_THRESHOLD`/`_RAMP` unchanged, so a small/founding
population is still never touched). Verified across 10 seeds this time (1, 2, 3, 4, 5, 6, 7, 8,
9, 42 -- widened past the original 3-seed suite specifically because that suite had already
missed one real regression this session, see `SINGLE_CATEGORY_ENERGY_CAP`'s postmortem below):
zero extinctions, and most seeds' final population came out identical or near-identical to the
0.15 baseline, meaning the deeper penalty rarely changed a seed's actual trajectory at the
pressure levels these runs reached -- a low-risk deepening given how the gating already
protects the population's most fragile phase.

**A hard ceiling, not just a multiplier (tried, reverted)**: a multiplicative penalty alone
(everything above) only reduces per-forage *efficiency* -- it doesn't stop a strong forager
sitting on abundant biomass from simply out-harvesting the penalty in absolute kcal, buying
back what a monotonous diet costs by gathering more of the same thing rather than actually
diversifying. Per direct request, `SINGLE_CATEGORY_ENERGY_CAP` added a hard per-tick kcal
ceiling on top of the multiplier when the recent diet is a single category, independent of
stockpile, biomass abundance, or forager strength.

First tried at 400 kcal: a Monte-Carlo sample of the actual pre-cap gain formula (varying
`traits.strength`, the harvest roll, and `salt_mult`) showed the median single-category gain
already sits around 260-290 and the 90th percentile around 440, so 400 was clipping a large
share of *ordinary* foraging -- a 3-seed local test confirmed it, showing 2 of 3 seeds decline
toward near-extinction. Recalibrated to 700 (above the ~99th percentile of the same sample) and
shipped after the 3-seed suite came back clean.

**It wasn't actually safe.** A later investigation (prompted by `avg_diet_diversity` still not
improving on the live server) tested seed 42 -- a long-used, previously stable seed that had
simply never been included in the 3-seed regression suite -- and found it went fully extinct
under the shipped 700 cap (tick 981, visible decline from tick 300 onward). Bisection across
the session's 5 diet/trade commits confirmed the cap, and only the cap, as the cause. The
Monte-Carlo calibration's mistake: it measured a population-wide percentile by drawing a fresh
random `traits.strength` for each sample, which describes how many *individuals* in a snapshot
exceed a given gain -- not how often any ONE individual gets clipped over their actual
lifetime. `traits.strength` is fixed per resident, so a genuinely strong forager's harvest sits
above the cap on nearly *every* single-category tick, not as a rare outlier. A flat ceiling
therefore acts as a persistent tax specifically on the population's strongest/most productive
foragers -- precisely the individuals the rest of the group's provisioning economy (mate
provisioning, food-share, follower tribute) depends on -- producing a slow cascading decline
rather than an obvious sharp shock, which is exactly why a small regression suite missed it.
Fully reverted; confirmed seed 42 (and seeds 1-3, all measurably healthier than under the cap)
survive without it. Any future version of this idea needs to scale with the individual's own
capability (e.g. relative to their own diverse-diet ceiling), not a single population-wide flat
number, and needs a wider seed sample specifically because this failure mode is gradual and
individual-dependent rather than an obvious immediate crash.

A settlement anywhere is realistically limited to whatever staples its local terrain suits, so
sustained high output requires either genuine local variety (farm + herd + fish) or exchange
with a differently-specialized settlement (see RFC-0007 for the trade trigger this connects to,
and the `is_merchant` trait that specializes in exactly this exchange).

### Zone Exclusivity

Cold and temperate zones are now mutually exclusive economies, not just "one is better at X":
`grazing_suitability`/`farming_suitability` in `CLIMATE_ZONES` are 0.0 in the zone that isn't
that zone's specialty (temperate has zero grazing; cold has zero farming and zero salt). This
gives real, felt economic reasons for cross-zone exchange rather than everyone being a passable
generalist everywhere. Cold-zone herding also gets its own yield bonus
(`COLD_ZONE_GRAZING_BONUS`, 1.5x) reflecting real nomadic pastoralism (Eurasian steppe, etc.) as
a genuinely thriving economy, not merely the only viable option there.

A fully farming-free cold zone (tried first) created a real bootstrapping trap: near-zero
winter regrowth (`winter: 0.005`) plus 2.8x winter upkeep meant almost nobody survived long
enough to ever discover `animal_husbandry` in the first place, so the zone stayed near-empty
even after tripling the discovery odds (`HUSBANDRY_DISCOVERY_MULT`). A small farming fallback
(0.15 suitability) was tried as a fix and made total population measurably *worse* across a
3-seed comparison -- crop_cultivation and animal_husbandry are independent discovery rolls, and
the only crops with any cold-zone weight (`sweet_potato`/`corn` in `CROP_ARCHETYPES`) are the
two weakest archetypes (~0.55-0.6x energy density vs wheat's 1.4x), so a resident unlucky
enough to roll farming first likely burns a knowledge-capacity slot and effort on a genuinely
weak option instead of the much more valuable herding path. Reverted.

Directly softening `winter` (regrow) was also tried (0.005 -> 0.025) and reverted: it caused a
real, isolated extinction in one local test seed (confirmed via same-seed A/B control, not RNG
noise) with zero improvement in cold-zone occupancy across any of the 3 seeds tested, so it
wasn't worth the risk for no measured benefit.

**A precise diagnostic** (2000-tick instrumented run, tracking cause of death and how long any
single resident ever stayed in the cold zone continuously) found the actual dominant killer:
disease, not starvation (384 disease deaths vs 133 starvation over one sample), and a hard
~80-tick ceiling that no resident ever exceeded across the whole run, regardless of seed. The
mechanism: low energy from harsh winter upkeep erodes health directly
(`HEALTH_EROSION_RATE`/`DEATH_ZONE_RATE`), and once health drops below 40, `DISEASE_LOW_HEALTH_
MULT` (1.25x) makes disease measurably more likely, which does further health damage --
compounding into a death spiral before anyone can establish a stable pastoral economy. This
chain was also using the single *global* `Simulation._pressure` (population over the WHOLE
map's carrying capacity) to scale itself, meaning a nearly-empty cold zone was still inheriting
the full brunt of crowding happening elsewhere on the map it had nothing to do with.

Two targeted fixes shipped, deliberately NOT touching winter food production/upkeep at all:
`COLD_ZONE_DISEASE_MULT` (0.5x disease probability in the cold zone specifically, reflecting the
real historical pattern that cold, dry climates suppress pathogen survival/transmission better
than warm humid ones -- this directly targets the actual dominant death cause), and a *cold-zone-
only* regional pressure substitution for the health-erosion/malnutrition/disease/accident chain
(`Simulation._zone_pressure['cold']` instead of the global `self._pressure`, computed the same
way but restricted to the cold zone's own population and carrying capacity). The regional-
pressure fix was first tried for all three zones and reverted after 2 of 10 test seeds went
extinct via a real, direct effect (steady decline from the very first checkpoint, not RNG-chaos
divergence) -- tropical's own regional pressure runs consistently much higher than the global
average (`farming_suitability`/`grazing_suitability` are both 0 there, so its local carrying
capacity is far worse per capita than the temperate-heavy blend that used to dilute it), and
tropical/temperate hold the vast majority of the population, so exposing them to their own true
local pressure was a net-negative trade even though it fixed a real unfairness for the small
cold-zone minority. Scoped down to cold only.

Verified across 10 seeds: 9 survived cleanly; one (a seed that had independently failed under
5 separate, unrelated changes earlier this session) went extinct even in the narrowed version,
traced specifically to `COLD_ZONE_DISEASE_MULT` changing how often the disease-damage-roll's
secondary `random()` call fires -- the same shared-global-RNG-stream chaos-divergence class
documented elsewhere in this file, just via a different trigger (a probability threshold gating
a conditional follow-up random call, rather than a boolean-emptiness short-circuit). Shipped
anyway given the 9/10 track record and that seed's independently-established fragility.

Honest result: a follow-up diagnostic after shipping found cold-zone occupancy and husbandry
discovery still near-zero in the same test seed -- this is a real, targeted fix for one
contributing factor (disease-driven death), not a full solution to the cold-zone bootstrapping
trap. The trap remains open; a future attempt should look beyond disease/pressure at the
direct calorie-erosion-to-health pathway itself, or population-independent seeding of viable
early cold-zone founders.

**Founding herders (tried next, also insufficient on its own).** Per direct request:
`FOUNDING_HERDER_COUNT` (5 per founding cluster) pre-loads `animal_husbandry` at world
generation for founders who already land, via the existing random initial spawn, on genuinely
grazing-suitable cold-zone terrain (`TERRAIN_GRAZING > 0`) -- same knowledge level/format as an
ordinary discovery event, no relocation or other privilege, just skipping the discovery *roll*
specifically for a handful of founders. Real-world motivation: founding pastoralist dispersals
(Eurasian steppe migrations) brought already-domesticated herds with them rather than
reinventing domestication locally from scratch on arrival every time.

Verified across the same 10 seeds: all 10 survived cleanly this time, including the
previously-fragile seed from the disease-mult fix above (now healthy) -- a real, safe
improvement with no regressions. But a follow-up diagnostic showed it does NOT solve the
underlying trap: even pre-equipped founders still died out by roughly tick 400-600 in the same
test seed, and the ~80-tick continuous-residency ceiling barely moved (81 vs 80/70 in earlier
diagnostics). This confirms the earlier hypothesis -- whether a resident *knows* husbandry
isn't what determines cold-zone survival time; the ~80-tick ceiling is set by the direct
calorie-erosion-to-health pathway itself (`HEALTH_EROSION_RATE`/`DEATH_ZONE_RATE` scaling with
caloric deficit), which no amount of pre-loaded knowledge changes if the harsh winter economics
kill a resident on the same timeline regardless. The trap remains open; the next attempt needs
to touch that erosion pathway directly (not disease, not pressure, not discovery odds) --
carefully, given every previous direct attempt at winter numbers has either caused chaos-
divergence extinctions or produced zero measured benefit.

**Wider cold-zone forage search radius (first real improvement).** Per direct request: instead
of touching the regrow *rate* (the lever behind every earlier failed/insufficient attempt),
widen how far a resident standing in the cold zone can *search* for food. Real wild game is
genuinely present across the cold zone, just sparser per cell than a temperate farm plot, so a
forager there should be able to search further to find it. `COLD_ZONE_FORAGE_CELL_CAP` (9, up
from `PERCEPTION_CELL_CAP`'s 4) widens the existing `_best_food`/CRITICAL-HUNGRY search-a-cell-
then-`_step_toward`-it mechanism specifically for cold-zone residents -- the same mechanism
already used for merchants/gifted scouts, applied to a zone instead of a rare trait. Cells don't
move, so this carries none of the persistent-re-targeting risk a resident-chasing mechanic
would.

This is the first cold-zone intervention this session to show a clear, measured improvement:
`max_cold_streak` (longest any resident stayed continuously in the cold zone) rose from 80/81 to
96, with cold-zone population peaking at 32 and husbandry holders at 74 early in the test run
(previous attempts never exceeded roughly 10-18). It comes with a real, confirmed cost: one seed
(42, previously a reliable "canary" that caught the `SINGLE_CATEGORY_ENERGY_CAP` regression)
dropped from a healthy 1171 to a fragile-but-not-extinct 22, verified via same-seed A/B control
as a direct causal effect of this specific change, not RNG-chaos noise. The other 9 of 10 test
seeds stayed healthy. Shipped after disclosing the tradeoff -- accepted as the cost of the
session's first real progress on this problem.

**Horse-specific transportation bonuses.** Per direct request, a resident who specifically
domesticated a horse (see `LIVESTOCK_ARCHETYPES`) gets two further benefits on top of the
zone-wide cold forage bonus: `HORSE_FORAGE_CELL_CAP` widens the same `_best_food` terrain-scan
radius even further (real-world logic already established for `HORSE_RAID_RANGE`, just applied
to the food search instead of the raid-target search), and `HORSE_MOVE_COST_MULT` makes the
direct kcal cost of a single movement step (`_do_move`) cheaper, since the horse does the
physical work a human otherwise would.

First tried at `HORSE_FORAGE_CELL_CAP=16`/`HORSE_MOVE_COST_MULT=0.4`: each constant verified
safe in isolation via separate single-variable A/B controls on the one seed affected, but the
COMBINATION caused a real, reproducible extinction that neither constant caused alone -- cheap
movement plus a much wider search radius compounds into far more aggressive horse-owner
wandering than either bonus produces by itself, a genuine interaction effect rather than
RNG-chaos noise (both isolated variants stayed healthy at 766/596 final population on the same
seed; only the combination went to 0). Narrowed together to `HORSE_FORAGE_CELL_CAP=12`/
`HORSE_MOVE_COST_MULT=0.6` and reverified across the same 10 seeds: all 10 survived, including
full recovery of the previously-extinct seed (1033) and the fragile one from the base
forage-radius change (recovered from 22 to 959 once the horse bonuses were added -- horses
appear to net help that seed once tuned to a safer magnitude, not just avoid harming it). Cold-
zone metrics held up at the narrower values too: `max_cold_streak` reached 87, cold-zone
population peaked at 42 and husbandry holders at 82 in the same diagnostic -- both higher than
the zone-wide-only version's peaks, so narrowing the horse bonuses didn't cost the underlying
improvement.

### Tropical Zone Disease (tried, reverted)

Per a broader "civilization pressure" framing (each climate zone should have both a real
advantage and a real pressure, not just cold getting attention by default): a
`TROPICAL_ZONE_DISEASE_MULT`, the real-world counterpart to `COLD_ZONE_DISEASE_MULT` (warm,
humid climates support pathogen survival/transmission far better than cold, dry ones -- real
historical tropical disease burden), was tried and reverted. First at 1.6x: a 10-seed test found
1 real extinction (seed 6), confirmed via same-seed A/B control as a direct causal effect (963
healthy with the multiplier off, 0 with it on) -- not RNG-chaos noise. Narrowed to 1.3x on the
assumption a smaller number would be safer, the same pattern that worked for the horse-bonus
interaction above -- it wasn't: narrowing *increased* the failure count to 2 (seed 6 still died,
plus a new one, seed 9, that had been fine at 1.6x). A smaller multiplier causing *more*
failures than a larger one rules out a simple dose-dependent relationship.

The likely reason: unlike `COLD_ZONE_DISEASE_MULT`, which only ever touched a tiny population
share, tropical typically holds a large share of the whole population (winter migration alone
pushes a lot of people there every year), so a disease-probability change there shifts the
shared global random module's secondary-random-call timing (see the `_maybe_trade`/crop-yield
chaos-divergence postmortems in RFC-0007) for a much bigger, less predictable slice of the
population -- chaos-divergence risk that doesn't shrink monotonically with the multiplier's
magnitude the way a real causal effect would. Reverted entirely. Giving tropical its own
disease/decay identity needs either a much smaller, more targeted mechanism than a population-
wide probability multiplier, or the per-resident/per-domain RNG stream fix that would remove
the shared-stream coupling behind this whole class of chaos-divergence issue in the first place.

### Cold Zone Calorie-Erosion Reduction (the actual root cause, finally addressed directly)

Every cold-zone diagnostic this session (disease suppression, regional pressure, founding
herders, wider forage radius, horse bonuses) kept converging on the same conclusion: the
~80-96-tick ceiling on continuous cold-zone residency was never really about disease or
discovery odds, it was the direct calorie-erosion-to-health pathway itself (`HEALTH_EROSION_
RATE`/`DEATH_ZONE_RATE`, both scaling with caloric deficit) -- harsh winter upkeep drives energy
into the erosion/death-zone bands, and this health cost, not disease, sets the actual ceiling.
Per direct request to finally address this: `COLD_ZONE_EROSION_MULT` (0.6) discounts both rates
for cold-zone residents specifically. Deliberately scoped the same low-blast-radius way as
`COLD_ZONE_DISEASE_MULT` (a small population share), not a global `HEALTH_EROSION_RATE`/
`DEATH_ZONE_RATE` change, which would carry the same large-population chaos-divergence risk that
just sank the tropical disease attempt -- and not the same lever as the reverted direct
winter-regrow attempt either (that changed food production/supply; this changes how harshly a
given deficit is punished, leaving supply untouched).

This produced the strongest cold-zone result of the whole session: cold-zone population peaked
at 61 and husbandry holders at 185 in a 2000-tick diagnostic (previous best: 42 and 82,
respectively), `max_cold_streak` reached 89. Verified across 10 seeds: 9 survived cleanly. One
(seed 2, a seed that had independently shown fragility under numerous unrelated changes earlier
this session) went extinct -- but a same-seed A/B control showed it was *already* declining
toward fragility even with the change disabled (75 by tick 1200, not a healthy population), so
this isn't the clean "healthy baseline collapses under the change" pattern seen in some earlier
reverted attempts -- more a seed already near its own edge getting tipped over. Shipped given
the scale of the improvement and that context.

### Cold Zone Fertility (same architectural bug, different mechanic)

Direct feedback after the erosion fix: cold-zone population still wasn't sustaining growth --
survival got measurably better across every fix above, but the population still spikes then
crashes back toward zero rather than settling into steady growth. Root cause, found by
re-reading the REPRODUCE block in `decide()`: fertility (`fertility = max(0.0, 1.0 - (pressure -
1.0) * 0.5)`) was reading the same GLOBAL `self._pressure` the calorie-erosion fix had already
identified and fixed for health/disease -- a nearly-empty cold zone's residents had their
*reproduction chance*, not just their survival odds, suppressed by however crowded temperate/
tropical happened to be, the identical unfairness in a different mechanic. `decide()` now
accepts an optional `zone_pressure` dict (`Simulation._zone_pressure`, already computed every
tick); a cold-zone resident's fertility uses `zone_pressure['cold']` instead of the global
`pressure` parameter. Scoped to cold only, same low-blast-radius pattern as every other zone-
specific fix this session -- temperate/tropical fertility is untouched.

Verified across 10 seeds: 9 survived cleanly, one (seed 7) dropped to a fragile-but-not-extinct
8. The cold-zone diagnostic showed husbandry holders peak at a new high (106) and
`max_cold_streak` reach 93, both consistent with the ongoing trend -- but honestly, the
underlying "spikes then crashes back to zero" pattern persists even with this fix. This is a
real, correct architectural fix (the same class of bug already proven real for erosion/disease),
not a placebo, but it wasn't the missing piece that makes the cold zone durably self-sustaining
on its own -- after five compounding zone-scoped fixes (disease, regional pressure, founding
herders, forage radius, horse bonuses, erosion, now fertility), the pattern of "better peaks,
still no durable equilibrium" suggests the remaining gap may not be a single remaining
parameter at all, but something more structural about how a sparse, spread-out population
finds mates/reproduces at low density, or requires a fundamentally different diagnostic pass
before the next attempt.

### Cold Zone Winter Hunting Bonus

Direct request: "哪怕冬季，都可以觅食动物来补充能量" (even in winter, wild animals should be
forageable for energy) -- real wild game is genuinely still present in the cold zone during
winter, just sparser than other seasons (the `CLIMATE_ZONES` winter regrow multiplier, which
this deliberately does NOT touch, given the reverted direct winter-regrow attempt's RNG-
divergence chaos postmortem earlier this session). `COLD_ZONE_WINTER_HUNT_BONUS` (10.0) adds a
conversion-formula bonus (same additive pattern as `ANIMAL_HUSBANDRY_BASE_BONUS`/`FISHING_BASE_
BONUS`) for anyone foraging in the cold zone during winter -- independent of `animal_husbandry`
knowledge, unlike `COLD_ZONE_GRAZING_BONUS`, so it's available to a resident who hasn't
domesticated anything yet, precisely the bootstrapping-phase pioneers this is meant to help.
Smaller than full husbandry mastery's bonus (20.0 base) -- opportunistic hunting is real but
secondary to actual herding, not a replacement for it.

Verified across 10 seeds: 9 survived cleanly, one (seed 1) dropped to a fragile-but-not-extinct
9, confirmed via same-seed A/B control as a real causal effect on a seed that was otherwise
healthy (497 with the bonus off) -- not an already-fragile seed getting tipped over, the more
concerning pattern. Cold-zone diagnostic showed a new population peak (73, up from the previous
best of 61) and husbandry peak of 142. Shipped given the seventh consecutive net-positive
zone-scoped fix and the continuing trend of real peak improvement, though (per the fertility
section above) the underlying "spikes then crashes" pattern has still not been fully resolved.

### Cold Zone Herder Migration Reluctance (the actual missing piece)

After seven consecutive fixes that all targeted survival or reproduction odds without ever
fully breaking the "spikes then crashes back to zero" pattern, a new hypothesis: the crash
might not be about *death* at all. `MIGRATE (winter)` unconditionally moves ANY resident with
`energy < 900` in winter toward a warmer zone -- including an established herder who already
knows `animal_husbandry`, with zero distinction from an ordinary wanderer who has nothing
keeping them in place. Every earlier fix improved a herder's odds of *surviving* a hard winter,
but none of them addressed whether a herder who survived would actually *stay* once things got
merely uncomfortable (well above outright death, but still below the flat 900 migration
trigger) rather than walking away from whatever pastoral foothold they'd built.

`COLD_ZONE_HERDER_MIGRATION_THRESHOLD` (400, down from the flat 900) applies only to cold-zone
residents who already know `animal_husbandry` -- abandoning an established herd/land is a
bigger decision than an ordinary forager relocating, so they tolerate real hardship before
finally giving up. Everyone else's migration behavior (including cold-zone residents who
haven't domesticated anything, who genuinely have nothing keeping them there) is completely
unchanged.

This was the missing piece. Verified across 10 seeds: all 10 survived cleanly, no tradeoff to
disclose this time. The cold-zone diagnostic result is a different order of magnitude from
every earlier fix: cold-zone population held steady in the 218-434 range for the ENTIRE
2000-tick run (previous best was a peak of 73 that always crashed back toward zero), husbandry
holders similarly sustained at 219-407, `max_cold_streak` reached 101, and total cold-zone
resident-ticks logged (570,287) were more than 10x any earlier diagnostic. The cold zone is, for
the first time this session, a genuinely self-sustaining population rather than a recurring
boom-bust cycle.

Real historical pattern that falls out of this without any new "raiding party" object: nomadic
winter raiding (see decide()'s `NOMADIC WINTER RAID` block, RFC-0007) -- since
`animal_husbandry` is now cold-zone-exclusive, knowing it alone proves pastoral origin, and a
herder who's migrated south for winter (see the existing `MIGRATE (winter)` block) but is
comfortable enough not to need that migration raids nearby outsiders more readily than the
ordinary case, echoing Mongol/Hunnic/Scythian-style incursions. Nothing coordinates a "raiding
party"; when many individually-migrating herders share the same disposition and reach the same
farmland in the same winter, the aggregate reads as coordinated, but each decision is
individual.

### Horse Discovery Weight

Follow-up per direct request, once the herder-migration-reluctance breakthrough made a
sustained cold-zone population real: live data showed 100% of current cold-zone herders had
rolled `cattle` -- `horse` (the archetype the transportation bonuses `HORSE_FORAGE_CELL_CAP`/
`HORSE_MOVE_COST_MULT`/`HORSE_RAID_RANGE` key off) was the rarest of the three
`LIVESTOCK_ARCHETYPES` options (`zone_weights['cold']`: sheep 3.0, cattle 2.5, horse 1.5, about
21% of picks) and had never actually appeared. Raised horse's weight to 2.5, matching cattle
(Monte-Carlo-verified new split: ~37% sheep / 32% cattle / 31% horse).

Lower risk than most changes this session: `_pick_archetype`'s `random.choices` call always
consumes the same amount of randomness regardless of which option wins, so reallocating weights
among already-equally-likely-to-fire outcomes doesn't carry the RNG-divergence chaos risk that
probability-*threshold* changes (disease multipliers, migration triggers) have shown repeatedly
this session. Verified across the same 10 seeds: all 10 fully healthy, and the cold-zone
diagnostic showed the herder-migration-reluctance breakthrough not just holding but improving
further (population sustained 186-360 the whole 2000-tick run, up from 218-434's already-strong
baseline in spots, `max_cold_streak` reaching 101). One test run's specific 10 founding herders
happened to roll zero horses despite the improved odds (a ~2.4% chance event, not a sign the fix
isn't working) -- the weight change itself is confirmed correct via direct sampling.

### Horse Owner Power-Up (carrying, movement, perception, combat)

Direct request, once horse ownership was confirmed live and viable: a domesticated horse should
make a real, multi-dimensional difference to how a resident lives, not just extend raid range.
Five simultaneous multipliers were requested for any resident whose `animal_husbandry` knowledge
rolled the `horse` archetype (`_has_horse(r)`):

- `HORSE_CARRY_MULT = 5.0` — `_add_resource` multiplies `r.traits.carrying_capacity` by this for
  horse-owners before computing available room, so a mounted resident can actually accumulate and
  move meaningful trade goods instead of being capped like a pedestrian.
- `HORSE_MOVE_COST_NEAR_ZERO = 0.05` — replaces the previous `HORSE_MOVE_COST_MULT = 0.6` in
  `_do_move`; a horse effectively removes the caloric cost of travel rather than merely
  discounting it.
- `HORSE_SPEED_MULT = 20` — `_step_toward` (signature extended to `steps=1`) now walks up to
  `steps` tiles in the target direction per call, stopping at the first impassable tile or the
  target, and returns a single `('move', ...)` action to the farthest tile reached. `_do_move`
  still evaluates cost/hazard once for that final destination cell only (consistent with the
  near-zero-cost intent — intermediate tiles aren't separately charged). Every `_step_toward`
  call site in `decide()` and `_explore()` now passes `horse_steps = HORSE_SPEED_MULT if
  has_horse else 1`.
- `HORSE_PERCEPTION_MULT = 10` — applied only to `cell_radius` (the terrain/food scan radius) in
  `decide()`'s `scout_cap` computation, deliberately **not** to `radius` (the separate variable
  `near_res` — resident detection — uses). `radius` already reaches 60-65 at high
  perception/sociability; a further 10x there would make resident-detection span nearly the whole
  map, a severe behavioral/performance risk disproportionate to the request's intent. Reach for
  *other residents* (raiding, following, seeking a chief) remains governed by the separate,
  already-tested `HORSE_RAID_RANGE = 8`. This is a deliberate narrowing of a literal reading of
  "perception range x10" to the terrain-scan half of perception only.
- `HORSE_COMBAT_MULT = 5.0` — a new `_combat_capability(r)` helper multiplies `_capability(r)` by
  this for horse-owners, used at the three raid power-ratio comparisons
  (`OPPORTUNISTIC_RAID_POWER_RATIO`, `TERRITORIAL_DEFENSE_POWER_RATIO`,
  `NOMADIC_WINTER_RAID_POWER_RATIO`) and at `_do_raid`'s actual `r_power`/`t_power` win/loss roll.
  Deliberately **not** applied to `FOLLOW STRONGER`'s capability comparison — the user's request
  specifically named combat/martial power ("武力值"), not general provider capability.

Combining five simultaneous large multipliers carried real risk: an earlier, much smaller
two-way combination this session (`HORSE_FORAGE_CELL_CAP` + `HORSE_MOVE_COST_MULT`) produced a
genuine interaction-effect extinction that neither change caused in isolation. This was tested
accordingly — full 10-seed regression (`test_trade_floor.py`, seeds 1-9 and 42, 1500 ticks) plus
the cold-zone diagnostic (`test_cold_diagnose.py`, seeds 1, 8, 42, 2000 ticks) at the full,
literal combined magnitude with no pre-emptive narrowing.

Result: all 13 runs healthy, zero extinctions. The cold-zone diagnostic showed population and
husbandry counts *exceeding* the pre-power-up baseline (e.g. seed 8: cold_pop/husbandry reaching
531/565 by tick 2000, up from the prior 218-434 sustained range) — horse-owners' near-zero travel
cost and 5x carrying capacity appear to strengthen exactly the trade/provisioning loop the
herder-migration-reluctance fix (see above) depends on, rather than destabilizing it. Shipped at
the full requested magnitude; no narrowing was needed.

### Horse's Own Energy Pool (grazing constraint on the power-up above)

Direct follow-up: the horse itself needs its own upkeep, not just the rider's — a real grazing
constraint on how far the power-up above can be exploited away from the horse's native cold-zone
range. New `Resident.horse_energy` field (default `-1.0` sentinel = "not yet initialized",
lazily set to `HORSE_ENERGY_MAX` the first tick `_has_horse(r)` is true — covers both fresh
invention and hereditary/taught acquisition without touching every acquisition call site).

Per-tick update (`Simulation._tick`, right after the ordinary upkeep block, before `decide()`
runs for that tick):

```python
if _has_horse(r):
    if r.horse_energy < 0:
        r.horse_energy = HORSE_ENERGY_MAX
    replenish = (HORSE_ENERGY_REPLENISH_COLD if climate_zone(r.y) == 'cold'
                 else HORSE_ENERGY_REPLENISH_OTHER)
    r.horse_energy = max(0.0, min(HORSE_ENERGY_MAX,
                                   r.horse_energy + replenish - HORSE_ENERGY_CONSUMPTION))
```

Constants map directly to the request's own numbers: `HORSE_ENERGY_MAX = 3000.0` (mirrors
`MAX_ENERGY`'s "full caloric reserve" scale), `HORSE_ENERGY_REPLENISH_COLD = 500.0`,
`HORSE_ENERGY_REPLENISH_OTHER = 450.0` ("进入温带,每个tick补充的卡路里只有450" — tropical is
treated the same as temperate since the request only named temperate explicitly and horses have
no natural range in either warm zone), `HORSE_ENERGY_CONSUMPTION = 500.0` (constant regardless of
zone, per "消耗也是500卡路里"). Net change per tick is therefore exactly 0 in the cold zone
(steady-state maintenance — staying below `HORSE_ENERGY_MAX` in cold does **not** recover lost
energy, since replenish only matches, never exceeds, consumption there — a literal reading of the
request's own 500=500 framing) and a steady -50/tick everywhere else, so a horse runs down over
roughly 60 ticks of continuous non-cold operation and only *stops* draining (not un-drains) by
returning to cold.

Degradation is a smooth, deterministic taper — no `random()` call anywhere in this mechanic, so
unlike most of this session's probability-threshold changes it carries none of the
RNG-divergence-chaos risk:

```python
def _horse_bonus_scale(r):
    if r.horse_energy < 0:
        return 1.0
    return max(0.0, min(1.0, r.horse_energy / HORSE_ENERGY_DEGRADE_THRESHOLD))

def _horse_mult(r, base_mult):
    if not _has_horse(r):
        return 1.0
    return 1.0 + (base_mult - 1.0) * _horse_bonus_scale(r)
```

`HORSE_ENERGY_DEGRADE_THRESHOLD = 1500.0` (half of `HORSE_ENERGY_MAX`) — bonuses stay
full-strength until horse_energy drops to this point (~30 ticks of grace), then fade linearly to
1.0 (no bonus, never a penalty below the pedestrian baseline — an exhausted horse is worth no
more than walking, never worse) over the next ~30 ticks as energy approaches 0.

`_horse_mult` replaces the flat `HORSE_CARRY_MULT`/`HORSE_SPEED_MULT`/`HORSE_COMBAT_MULT` checks
at every site that uses them (`_add_resource`, `decide()`'s `horse_steps`, `_explore()`'s own
`horse_steps`, `_combat_capability`, `_do_raid`'s `r_power`/`t_power`) — these are the three
dimensions the user explicitly named as degrading ("移动速度,武力,携带数量"). Deliberately **not**
applied to `HORSE_MOVE_COST_NEAR_ZERO` or `HORSE_PERCEPTION_MULT`, which stay constant for as
long as `animal_husbandry(horse)` is known at all, matching the original request's own list.

A new `avg_horse_energy_pct` metric (population-average `horse_energy / HORSE_ENERGY_MAX` across
horse-owners only, 0 if none) was added for live observability, same pattern as
`avg_diet_diversity`.

Verified two ways: (1) a standalone unit-level sanity script exercising the update/taper math
directly (cold-zone net-zero, temperate -50/tick drain, exact taper values at known energy
levels, non-horse-owners completely unaffected, no negative/over-cap clamping) — confirmed exact
match to the designed formulas; (2) the full 10-seed regression + 3-seed cold-zone diagnostic at
the same seeds as the power-up above — all healthy, zero extinctions, cold-zone population/
husbandry counts in the same strong range as the power-up's own results (e.g. seed 8: 462/447 at
tick 2000). Shipped at the literal requested numbers with no narrowing.

### Climate Zones

The map is divided into three horizontal climate bands (top to bottom):

| Zone      | Rows     | Season Multipliers                                | Non-Winter Character | Winter Character |
|-----------|----------|----------------------------------------------------|-----------------------|-------------------|
| Cold      | 0–26     | spring 1.1, summer 0.8, autumn 0.35, winter 0.005  | Modest growth possible | Uninhabitable without knowledge — population converges to zero |
| Temperate | 27–53    | spring 1.4, summer 1.0, autumn 0.55, winter 0.02   | Sustains a small population | Harsh bottleneck; knowledge meaningfully improves survival |
| Tropical  | 54–79    | spring 1.2, summer 1.0, autumn 0.75, winter 0.05   | Sustains the largest population | Seasonal challenge; knowledge accelerates growth |

**Survival Model: Knowledge Optimizes a Viable Baseline, Doesn't Gatekeep It**

Non-winter seasons are generous enough that a population can establish and grow in temperate and tropical zones with zero knowledge. Winter is the recurring bottleneck:

- **No knowledge**: winter upkeep costs scale by zone (tropical 1.3×, temperate 1.8×, cold 2.8×) against near-zero regrowth, producing real starvation losses each winter — heaviest in cold, moderate in temperate, lightest in tropical.
- **With food storage knowledge**: winter upkeep is reduced (up to 30% at full skill), meaningfully raising survival odds without making survival deterministic.
- **Cold zone is a special case**: even a theoretical non-winter carrying capacity is irrelevant if winter alone is unsurvivable. Without stored food, shelter, or clothing — none of which exist by default — cold-zone populations are killed off by winter within their first year. This is intentional: pre-knowledge humans without domesticated animals or storage technique genuinely could not winter in cold climates. Cold zone habitation is a downstream consequence of knowledge accumulation, not a baseline given.

**Why This Matters**:
- Base environment is viable in tropical/temperate zones: population can establish and grow without any knowledge
- Cold zone is legitimately uninhabitable at baseline — this is physically honest, not a scripted gate
- Winter is a recurring, real mortality event, not a one-time filter
- Knowledge provides a genuine, gradual survival edge without becoming a hard requirement for life itself

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
