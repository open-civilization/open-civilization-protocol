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

## The Malthusian Trap

The Malthusian trap is the foundational population dynamic of OCP. It is not a failure state — it is the baseline condition from which civilization must escape.

### Mechanism

1. Population grows when food is sufficient (births > deaths).
2. Population hits the carrying capacity ceiling set by resource regeneration.
3. Beyond the ceiling: per-capita food drops, starvation rises, disease amplifies, conflict erupts.
4. Population crashes back to or below carrying capacity.
5. Cycle repeats.

### Why It Matters for Emergence

The Malthusian trap is what gives civilization its purpose. Without it, there is no pressure to organize:

- **Agriculture emerges** because foraging hits a ceiling.
- **Storage emerges** because seasonal variation kills the unprepared.
- **Trade emerges** because local scarcity can be offset by distant surplus.
- **Cooperation emerges** because coordinated groups extract resources more efficiently than individuals.
- **War emerges** because one group can raise its effective carrying capacity by taking another group's territory.

Every emergent institution in human history can be understood as a strategy to raise, redistribute, or defend against the carrying capacity ceiling.

### Escaping the Trap

The only way to permanently raise carrying capacity is through emergent changes to the resource equation:

- Agricultural knowledge → higher effective regrow rates
- Tool-making → higher foraging efficiency
- Storage technology → smoothing seasonal variation
- Trade networks → redistributing surplus across zones

These must emerge from resident behavior and knowledge accumulation (RFC-0006). They cannot be granted by the engine.

### Phase 1 Calibration

Phase 1 uses a 60×80 map divided into three climate zones (cold, temperate, tropical). The initial population of 55 is seeded near the environment's natural baseline capacity and scattered across all zones — the engine does not target a fixed carrying-capacity number; it emerges from terrain, season multipliers, and whatever knowledge the population happens to discover.

The first winter acts as a founding bottleneck: the cold zone reliably depopulates to zero within the first year (no domesticated animals, storage, clothing, or shelter exist yet to make it survivable), the temperate zone stabilizes through selective winter pressure, and the tropical zone — survivable at baseline without any knowledge — becomes the initial population center. This mirrors the real constraint that early human populations concentrated in habitable climate bands before adaptation technologies existed.

Because carrying capacity itself rises as domestication, shelter, and clothing spread (see RFC-0003, RFC-0006), population is not a fixed oscillation band but a rising one. A verified 70-year (2269-tick) run: population grew from the 55-person seed to a stable ~300, with carrying capacity rising from a baseline around 130-160 to 185+ as cultivated land expanded, while population pressure oscillated persistently around 1.4-1.6 (moderate, sustained overshoot, not runaway collapse). Key emergence drivers visible across such a run:

- **Winter death cycles**: recurring, real losses each winter, softened but never eliminated by food storage/shelter/clothing knowledge as it spreads
- **Epidemic outbreaks**: population-scale events triggered by local crowding density, with visible death-rate spikes (observed up to 12 deaths/tick against a 2-5/tick background) and a rising population-average `immunity` trait afterward — outbreaks select for resistance, they don't just cull randomly
- **Raiding under pressure**: raid probability scales with population pressure past 1.2, but only for residents with sociability < 0.5 — overcrowding pushes the anti-social toward violence disproportionately, not the population uniformly; targeting is biased toward non-bonded strangers (resource seizure from outsiders, via Hamilton's-rule relatedness) below pressure 1.5, and only loses that bias — spilling into established relationships and kin — under sustained crisis (see RFC-0004 Raiding)
- **Opportunistic raiding (population as a resource)**: the pressure-driven raid above requires real local desperation (near-zero energy and depleted local food) to fire at all, which live data showed drops to near-zero once a population is well-fed — spatially adjacent, well-fed clusters coexisted with zero raids recorded over long stretches. A second, independent trigger lets a comfortable, physically stronger resident raid a nearby weaker stranger purely because the power gap is profitable, not because either party is starving — still Hamilton's-rule stranger-preferring, still `_capability` (intelligence+perception+strength+speed), still no authored war/territory object. A decisive win against an unattached stranger can, at low probability, escalate from a one-off theft into ongoing coerced labor extraction (`coerced_by`): the coerced resident keeps deciding and acting for themselves, only a share of their foraging surplus is redirected to the controller each tick, ending when the controller dies or via a small standing escape chance — never a permanent lock, per Collapse and Regression below.
- **Territorial retreat (attempted, reverted)**: a Hawk-Dove/Bourgeois-framed mechanic where a resident individually flees a local area once nearby unbonded strangers were decisively stronger than their own bonded allies was implemented and tested across four parameter passes (including a real destination search, not a blind flee-direction step). All four produced a real population decline toward near-extinction and rising `inbreeding_load` instead of the intended healthier-outcrossing effect — adding a fourth competing reason to relocate (alongside general/winter migration and fission) structurally destabilized the reproduction economy in ways threshold tuning didn't fix. Reverted; needs a different design before it's tried again, not just softer numbers.
- **Trade and resource conflict**: named resources (crops, cold-zone minerals — RFC-0003) give raiding and ordinary interaction a richer payoff than abstract energy alone. Trade is not a scripted route or allocation system (explicitly out of scope above) — it is `_maybe_trade`, an opportunistic one-off gift during an otherwise-ordinary interaction, triggered only when one resident holds real surplus of something the other visibly lacks, exactly the same emergent, individual-level pattern raiding already uses. Raiding gets a matching extension: a raider who holds no minerals at all under elevated pressure raids more readily, and a won raid now seizes a share of the victim's resource stockpile alongside energy. Whether anything resembling a persistent "trade network" (see Conditions for Emergence above) actually emerges from repeated individual exchanges is an experimental question, not something this mechanism guarantees.
  - The SOCIAL decide() block that leads into `_maybe_trade` originally only risked approaching a genuine stranger under population pressure (`pressure > 1.0`) — meaning a well-fed but dietarily monotonous resident (see RFC-0003's diet-diversity/salt writeup) had no in-engine reason to ever risk contact with someone from a different specialization, so cross-region trade essentially never fired in testing. A resident whose own recent diet is monotonous (`recent_food_types`) now also risks approaching a stranger specifically (not a familiar/kin default) independent of pressure — still only ever acting on someone already in perception range, never a reason to travel toward a distant stranger (same non-negotiable constraint that made the reverted territorial-retreat/exogamy attempts fail).
- **General migration under pressure**: once pressure exceeds 1.3, residents actively search a wider radius for less-crowded, better-resourced ground rather than compete on a depleted local patch, independent of season — a spatial release valve for overshoot, distinct from the winter-specific cold-avoidance migration
- **Language and writing**: both are downstream of population and cooperation reaching a real scale — in the verified run, neither appeared until population pressure had been sustained above ~0.6-0.9 for many generations, then both reached ~75% adoption within a few hundred further ticks (see RFC-0006)

Expansion into the cold zone specifically remains gated on emergent adaptation (principally `animal_husbandry`, the zone's suited domestication path) rather than population pressure alone — pressure drives residents to spread out and compete harder, but it cannot make an unsurvivable winter survivable by itself.

## Scaling Pressures

Organizations do not form because they are designed. They form because individual survival strategies become insufficient at certain scales.

### Population Density and the Malthusian Ceiling

- As local populations approach carrying capacity, resource competition intensifies non-linearly.
- Disease probability scales with pressure² — crowding amplifies epidemics.
- Raiding behavior emerges among starving individuals, creating a violence cycle.
- Coordination reduces conflict cost and improves collective foraging/defense.
- Without coordination mechanisms, dense populations are unstable and crash.

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

Stage 1 implemented, individual-level building block: `carrying_capacity` (see RFC-0004) is a
9th heritable trait, mean 10, with occasional individuals well past the `MERCHANT_CAPACITY_
THRESHOLD=40` cutoff that `is_merchant()` reads off it — no authored "Merchant" role, same
threshold-readout pattern as `is_gifted_scout()`. A real cap on total personal resource holdings
(`_add_resource`, replacing the previously-unbounded `r.resources[x] += y` pattern at every
accumulation site: mining, crop surplus, gift-receiving, raid loot, inheritance) makes the trait
mean something economically, and merchants get wider perception (`MERCHANT_CELL_CAP`, matching
the gifted-scout perception boost) so they can actually see the surrounding scarcity/surplus
pattern the trait's own flavor text describes. Deliberately scoped to Stage 1 only: a merchant
still only ever acts on an already-adjacent trade partner via the existing `_maybe_trade`/SOCIAL
block (with `is_merchant` added as its own trigger condition alongside diet-driven contact,
see below) — no long-distance travel-to-market or price-arbitrage behavior yet. That "Stage 2"
vision (seek out and travel toward a specific distant settlement with a specific known deficit)
is explicitly deferred, since it's exactly the persistent-distant-target shape that collapsed
the territorial-retreat and exogamy attempts (see Hierarchies below) — it would need the same
committed-target persistence mechanism as `scout_target`/FISSION before it's safe to try.

**Merchant profit redistribution** extends the same building block: `_maybe_trade` was a
one-way gift for ordinary residents (surplus-holder gives, no return leg), but a merchant who
completes one now also collects the reciprocal leg — the partner's own surplus-vs-the-merchant's-
deficit good comes back, a genuine two-way barter rather than a gift. This barter earns a flat
kcal margin (`MERCHANT_TRADE_PROFIT_KCAL`) representing the practical value of matching a local
glut against a local shortage. Explicitly NOT a currency or price object (see Design, below) —
no abstract unit of account is introduced, no global price is computed; it's a fixed reward
attached to one individual's successful match, same category of thing as a scavenge yield.
Deliberately not kept: per the same redistribution-not-accumulation logic as `chief_standing`
(Sahlins' Big Man model, cited above) and `FOLLOWER_TRIBUTE_SHARE`, most of the margin goes to
a bonded chief-standing ally if the merchant has one, and the remainder is split among the
merchant's own living, *bonded* children (bonded, not merely biological — mirrors how every
other resource transfer in the engine only ever reaches someone already in contact, never an
absent relative). Both legs count toward the merchant's own `energy_given_away`, so a
successful-enough merchant accumulates real `chief_standing` themselves — an emergent
merchant-to-chief pathway that falls out of reusing the existing standing metric, not a second
authored ladder.

**Closing the trade-diet loop**: the pressure-gated dietary imbalance penalty (RFC-0003) already
gave a low-diversity resident a behavioral reason to risk approaching a stranger (the SOCIAL
block's `low_diversity` condition), but two gaps meant that contact didn't actually fix
anything. First, the reciprocal barter leg in `_maybe_trade` was merchant-exclusive
(`r.is_merchant()`), so an ordinary resident who initiated contact out of dietary need could
only ever give their own surplus away, never receive the category they were missing — unless a
merchant happened to separately initiate contact with them later. Second, even a resource
received via trade (`r.resources`, a passive stockpile) was never connected to
`recent_food_types` (the diet-diversity tracker, updated only by `_do_forage`'s act of directly
producing food), so holding a traded good couldn't relieve the penalty even when received.
Both gaps are closed: the reciprocal leg now also fires for any resident whose own recent diet
is monotonous (same `low_diversity` test as the SOCIAL trigger), not just merchants — they get
the real exchange but not the merchant's profit skim, since their motive is nutritional need,
not brokerage; and any food-category good (`FOOD_CATEGORY`) received through either leg of a
trade is recorded into `recent_food_types` at the tick received, same as if it had been
foraged directly. This makes "a resident short on variety trades with someone who has it" an
actual, functioning loop rather than a one-way gift that never reaches the person who needed
it — merchants remain the ones who profit from matching gluts to shortages, but they're no
longer the only ones who can complete a real exchange.

**Trade's actual supply-side bottleneck**: even with demand-side motivation working (pressure-
gated penalty, `low_diversity`-driven contact, the closed loop above), live data showed only
45 of 232 merchants held any resources at all, and most of those holdings (0.1-1.4 units) sat
below the trade-candidacy threshold. Lowering that threshold (`TRADE_SURPLUS_FLOOR`, 2.0 -> 0.5)
alone didn't move local trade frequency at all — `resource_holders` stayed in the single digits
across a 1500-tick, 3-seed test regardless, meaning most residents were never accumulating
resources in the first place, not just falling short of an arbitrary floor. The real bottleneck
is production and retention: crop surplus only converts to a tradeable stockpile in the narrow
window where a farmer's energy already exceeds `MAX_ENERGY` (`CROP_SURPLUS_CONVERSION`), and
`RESOURCE_STOCKPILE_DECAY` erodes whatever does accumulate at 1%/tick between those rare events.
`MINING_YIELD_PER_TICK` (0.8 -> 1.5), `CROP_SURPLUS_CONVERSION` (0.02 -> 0.05), and
`RESOURCE_STOCKPILE_DECAY` (0.01 -> 0.005, halved) were all raised together on direct request.
Verified safe across the same 3 test seeds (no extinctions, one seed measurably healthier) and
produced the first real trade event observed in any local test this session — still rare, but a
genuine first data point rather than zero, confirming the diagnosis was directionally right even
though the effect size at this local population scale (hundreds, not the live server's
thousands) remains small.

**A precise trade-funnel trace, and a real architectural limit.** A follow-up instrumented run
(3000 ticks, wrapping `_maybe_trade`/`_do_interact`/`decide` to count outcomes rather than
sampling the live event feed) found the still-remaining bottleneck precisely: of 6028 `interact`
actions, only 741 (12%) ever reached the trade check at all (the rest resolved as mate
provisioning or food-sharing first, both higher-priority in `_do_interact`), and of those 741,
705 (95%) had a genuinely empty `r.resources` — even though 96.5% of the population knows
`crop_cultivation`. The actual gate is `pre_cap_energy > MAX_ENERGY`: average population energy
runs 900-1300, so a single tick's harvest exceeding the full 3000 energy ceiling is a rare
spike, not a routine "well-fed" state, and raising `CROP_SURPLUS_CONVERSION`'s rate (above)
never touches how often that spike happens at all.

Two independent fixes were tried on direct request. Lowering the trigger threshold
(`CROP_SURPLUS_ENERGY_THRESHOLD_FRACTION`, requiring 65% of `MAX_ENERGY` instead of the full
100%) verified safe across 10 seeds and shipped. Giving farming its own small unconditional
per-tick yield (mirroring how `MINING_YIELD_PER_TICK` already works, independent of any energy
threshold) did not ship: a 10-seed test found 3 real extinctions that didn't happen without it,
and shrinking the per-tick amount 5x (0.15 -> 0.03) didn't fix it, isolating the cause as an
architectural one rather than a magnitude one — `_maybe_trade`'s own gate,
`not r.resources or random.random() >= TRADE_CHANCE`, short-circuits on emptiness, so flipping
most of the population's `r.resources` from empty to non-empty at once silently changes how
many `random()` calls get consumed per interaction across the entire shared global random
stream (`Simulation.__init__` seeds Python's module-level `random`, not a per-resident
instance), which cascades into a completely different, unrelated population trajectory for
susceptible seeds — the same class of RNG-divergence chaos documented in RFC-0003's cold-zone
winter-regrow investigation, but this time confirmed to have a real, elevated failure rate (3/10
seeds) rather than being dismissible as one unlucky seed. Any future attempt at giving more
knowledge domains their own unconditional yield needs either a per-resident/per-domain RNG
stream (removing the shared-stream coupling entirely) or to avoid ever changing whether
`r.resources` is empty for a large fraction of the population in a short span of ticks.

**Merchant seeks chief**: even with production/retention fixed, a merchant still only ever
encountered whoever happened to be randomly nearby -- no targeting of who's actually worth
approaching. The safe fix reuses FOLLOW STRONGER's existing pattern exactly (ordinary residents
already gravitate toward a meaningfully-more-capable bonded ally, see `_capability`): a merchant
bonded to a chief-standing ally now travels toward them specifically and interacts with them
directly on arrival, rather than the generic SOCIAL block's random pick among whoever's nearby.
This is safe for the same reason FOLLOW STRONGER is -- the target is an EXISTING bond, not a
freshly-detected stranger, so the same chief tends to get picked tick after tick because the
*bond* is stable, not because of a stored/committed target field re-evaluated by comparing
"best available" each tick (the exact pattern that collapsed the territorial-retreat and
inbreeding-aware-exogamy attempts). A chief is also a natural information/redistribution hub in
its own right (Sahlins' Big Man model, already cited above for `chief_standing`) and their own
followers already cluster there via the same FOLLOW STRONGER mechanic, so reaching the chief
also means reaching a real local economic cluster, without any new "market" object or explicit
aggregate-stockpile data structure on the chief.

Verified across the same 3 test seeds: zero extinctions, but population ran measurably lower in
2 of 3 seeds versus the immediately-prior baseline (132/282/217 vs. 330/554/140) -- one seed
improved, two declined. The likely mechanism: the trigger (`r.energy > 1200`, matching FOLLOW
STRONGER's own threshold) isn't a true hunger gate, so a merchant with a nearby-but-not-adjacent
bonded chief prioritizes walking over foraging even when only moderately fed, trading some of
their own energy margin for the trip. Shipped anyway on direct request after disclosing the
tradeoff -- accepted as the cost of giving merchants real information/target discipline instead
of pure chance encounters.

### Hierarchies

- some residents consistently influencing others' behavior
- resource flow from periphery to center
- decision-making patterns where few residents' choices affect many

Implemented, individual-level building blocks for this (all riding on `chief_standing` — see
RFC-0004 — a pure readout of a resident's own redistribution history, never assigned by the
engine):

- **Follower tribute**: a resident bonded to a chief-standing ally voluntarily redirects a
  modest share of their own forage surplus to that leader each tick — the material counterpart
  of the existing FOLLOW STRONGER behavior (bonded residents already physically gravitate
  toward more capable allies). Does not inflate the chief's own `energy_given_away`, so
  receiving tribute cannot itself manufacture more standing.
- **Chiefly rivalry**: `chief_standing` is a scarce, contested status — a chief who opportunity-
  raids (see below) preferentially targets another chief among qualifying candidates, rather
  than treating every stranger as interchangeable prey.
- **Mate choice concentration**: when multiple immediately-reachable reproduction candidates are
  available, higher `chief_standing` is preferred (RFC-0011: "high-status male reproductive
  concentration" is an explicitly sanctioned emergent pattern). Deliberately scoped to only
  ever-adjacent candidates, never a reason to travel toward a distant "better" candidate
  re-evaluated fresh each tick — see the Collapse and Regression note below for why.
- **Leadership succession**: a dead chief's standing cannot be transferred (would be granting an
  unearned capability), but their accumulated resources, half their remaining energy, and their
  follower bond network transfer to an heir — the most capable gifted scout among their own
  followers, falling back to the eldest living son. This is inherited capital giving the heir a
  real head start, not an inherited title; the heir still has to redistribute to earn
  `chief_standing` in their own right.
- **Opportunistic raiding**: the original pressure-gated raid trigger requires real local
  desperation to fire at all, which live data showed drops to ~zero once a population is
  well-fed. A second, independent trigger lets a comfortable, decisively stronger resident raid
  a weaker nearby stranger purely because the power gap is profitable — still Hamilton's-rule
  stranger-preferring, still `_capability`-gated, no authored war object. Its raid chance now
  also scales with `payoff_ratio` (candidate energy relative to the raider's own) rather than
  firing at a flat rate once the power-gap gate is cleared, so a barely-worthwhile target and an
  obviously lucrative one aren't raided equally often.
- **Real group membership, not just pairwise bonds, for "who counts as a stranger"**: live
  observation showed raid frequency was far lower than the pressure/capability math implied,
  because the original stranger check (`no bond OR low relatedness`) missed residents who'd
  drifted into the same physically-cohering settlement without ever forming a *direct* bond with
  a given individual — they'd read as strangers to each other despite functionally belonging to
  the same group. `_tick`'s existing periodic union-find over the bond graph (already computing
  `group_count`, see below) now also stores each resident's connected-component root
  (`self._group_root`); `_is_outsider(r, res, group_root)` checks same-root membership when both
  residents are in that index (falling back to the original bond/relatedness heuristic
  otherwise) and is now the shared stranger-detection used by opportunistic raiding, desperation
  raiding, territorial defense, and nomadic winter raiding — a real definition of "us" grounded
  in the actual social graph, not a per-pair fiction. Pure detection over data the engine already
  computes; nothing about group membership is authored or assigned.
- **Territorial defense**: a resident whose home area is cultivated (`cultivated_land`, a
  side-effect of crop farming already tracked per cell) fights a nearby outsider who encroaches
  on it, gated on real local dominance (`TERRITORIAL_DEFENSE_POWER_RATIO`) rather than
  desperation — defending a farmed investment is a different motive than raiding for food, and
  produces a distinct message (`fought ... over cultivated land`) rather than reusing the raid
  event type. Same non-negotiable constraint as everything else here: acts only on an
  already-adjacent outsider, never travels toward one.
- **Nomadic winter raid**: since `animal_husbandry` is now cold-zone-exclusive (RFC-0003's zone
  exclusivity), simply knowing it proves pastoral origin. A herder in `winter` who has migrated
  out of the cold zone (see the existing `MIGRATE (winter)` behavior) but is currently
  comfortable (`r.energy > 900`, i.e. not desperate) raids a nearby outsider more readily than
  the baseline case, echoing real Eurasian-steppe winter-incursion patterns (Mongol, Hunnic,
  Scythian). Nothing coordinates a "raiding party" — when many individually-migrating herders
  share the disposition and land in the same winter refuge, the aggregate reads as a coordinated
  raid, but each resident's decision is independent and local.

**Attempted and reverted** (see Collapse and Regression): a Hawk-Dove/Bourgeois "territorial
retreat" mechanic (individually flee a local area once nearby strangers are decisively stronger
than one's own allies) and an inbreeding-load-aware exogamy preference (chase the
lowest-`inbreeding_load` candidate rather than the nearest) were both implemented and tested
across multiple parameter passes. Both produced a real population decline toward
near-extinction, from the same root cause: re-evaluating and potentially re-targeting a distant
"better" option fresh every tick, with no persistence, means a resident can spend indefinite
time traveling without ever closing the distance or completing the action — chronic wasted
movement instead of foraging/reproducing. Any future version of either idea needs a persistent,
committed target (see `scout_target`'s pattern for FISSION) rather than a per-tick re-pick.

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
