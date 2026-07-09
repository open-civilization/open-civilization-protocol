# RFC-0004 Life Engine

## Status

Draft

## Summary

This RFC defines the life simulation layer of OCP.

The life engine governs how individual residents exist, act, survive, reproduce, and adapt within the constraints set by the universe constitution, the physics layer, and the energy system.

Life in OCP has no quests, no plot, and no scripted characters. Every resident is a bounded agent that must negotiate reality through perception, intent, and consequence.

## Motivation

Without a well-defined life layer, the project faces two failure modes:

- if residents are too simple (pure state machines with no internal variation), behavior converges to a single optimal pattern and nothing interesting emerges
- if residents are too complex (full LLM reasoning every tick), the system becomes unaffordable and unscalable at 1000+ residents

The life engine must find the middle path: enough internal structure to produce heterogeneous behavior and meaningful tradeoffs, but cheap enough to run thousands of residents per tick without calling an LLM for routine decisions.

## Goals

This RFC defines:

- the minimal resident model for Phase 1
- the survival loop
- the reproduction loop
- the adaptation and variation model
- physiological and cognitive state
- the intent-action-resolution cycle from the resident's perspective
- the boundary between life-layer decisions and AI-layer decisions

## Non-Goals

This RFC does not define:

- the AI reasoning architecture (see RFC-0005)
- the knowledge representation system (see RFC-0006)
- civilization-level organization (see RFC-0007)
- player interaction surfaces (see RFC-0009)
- detailed genetics or evolutionary biology

## Architectural Position

```text
Universe
    ↓
Physics
    ↓
Life          ← this RFC
    ↓
Civilization
    ↓
Player
```

Life sits between Physics and Civilization.

- Physics provides the objective world: terrain, resources, movement cost, environmental conditions.
- Life perceives a local, partial, delayed view of that world and acts within it.
- Civilization emerges from the aggregate patterns of life behavior — it is never injected from above.

## Normative Language

The key words "MUST", "MUST NOT", "SHOULD", and "MAY" in this document are to be interpreted as binding protocol terms.

## First Principle

Life has only three native goals:

```text
Survive
Reproduce
Increase fitness
```

There are no quests. There is no plot. There is no main character.

Every resident is an autonomous bounded agent that pursues survival and reproduction under constraint. Everything above that — cooperation, competition, culture, war, trade — must emerge from these goals interacting with scarcity, proximity, and variation.

## Resident Model

A resident is the atomic unit of life in OCP.

### Minimum Resident State

Phase 1 residents SHOULD carry at least the following state:

- identity (unique, persistent)
- location (spatial cell reference)
- age
- energy reserve
- health
- physiological status (hunger, fatigue, injury)
- cognitive budget (per-tick computation ceiling, varies by individual)
- memory (bounded, lossy, local)
- trait vector (individual attributes affecting behavior and capability)
- social bonds (list of known individuals with relationship quality)

### Heterogeneity Requirement

Residents MUST NOT be identical at initialization or across generations.

- Trait vectors MUST vary across individuals.
- Cognitive budgets MUST vary as specified in RFC-0001 Law 8.
- Initial conditions (location, energy, traits) SHOULD be varied.

Heterogeneity is not cosmetic diversity. It is the structural precondition for comparative advantage, specialization, and emergent division of labor.

## Survival Loop

The survival loop is the innermost cycle of life. It runs every tick for every living resident.

### Core Survival Cycle

```text
Perceive (local, partial, delayed)
    ↓
Evaluate (needs, threats, opportunities)
    ↓
Decide (choose intent)
    ↓
Act (submit intent to physics)
    ↓
Receive outcome (success, failure, partial)
    ↓
Update state (energy, health, memory, location)
```

### Survival Requirements

- Every resident MUST have a baseline maintenance cost per tick (energy drain from simply existing).
- If energy reserve falls below a starvation threshold, health MUST degrade.
- If health reaches zero, the resident dies.
- Death MUST be permanent within a lineage. There is no resurrection.
- Residents MUST be able to die from starvation, disease, infant mortality, accidents, conflict, exposure, or age.

### Survival Pressure

Survival pressure is the gap between what a resident needs to stay alive and what the local environment makes available.

- High survival pressure SHOULD increase movement, risk-taking, and conflict.
- Low survival pressure SHOULD enable surplus accumulation, experimentation, and social investment.
- Survival pressure SHOULD vary spatially and temporally rather than being globally uniform.
- When population exceeds carrying capacity (see RFC-0003), survival pressure intensifies non-linearly, amplifying all mortality factors.

## Perception

Residents MUST perceive the world locally, not globally.

### Perception Requirements

- A resident MUST only observe cells within a limited perception radius.
- Perception SHOULD be affected by terrain, weather, and time of day where applicable.
- Perceived information MAY be incomplete, delayed, or inaccurate.
- A resident MUST NOT have access to another resident's internal state (energy, intent, memory) unless explicitly communicated.

### Perception vs. Reality

The life engine MUST maintain a strict separation between:

- world truth (objective state held by the physics engine)
- agent belief (the resident's local, partial, potentially outdated model of the world)

This separation is constitutionally required by RFC-0001 Law 7 (Bounded Cognition).

## Intent and Action

Residents do not directly mutate world state. They propose intent.

### Intent Model

An intent is a structured proposal from a resident to the physics engine.

Example intents:

- move to adjacent cell
- forage for food
- hunt
- fish
- drink
- rest
- build shelter
- repair structure
- communicate with nearby resident
- share food
- attack

### Resolution

- Physics MUST resolve each intent against world state.
- Resolution MUST account for location, resource availability, energy cost, time cost, and environmental conditions.
- Resolution MUST return success, failure, or partial success with resulting state changes.
- A resident's energy SHOULD be deducted for attempting an action regardless of outcome (effort is not free).

## Reproduction

Reproduction is the mechanism by which population persists and variation propagates.

### Reproduction Requirements

- Reproduction MUST require energy surplus above survival threshold.
- Reproduction MUST consume significant energy from the parent(s).
- Offspring MUST inherit traits from parent(s) with mandatory variation.
- Offspring MUST NOT be copies of their parent(s).

### Variation Requirement

- Trait inheritance MUST include noise, drift, or recombination.
- Variation is not a bug or an imprecision. It is the search mechanism by which the population explores behavioral and physiological space.
- Without variation, natural selection has nothing to select from, and the population converges to a monoculture that cannot adapt to changing conditions.

### Phase 1 Reproduction Model

Phase 1 MAY use a simplified reproduction model:

- asexual or paired reproduction
- trait vector inherited with random perturbation
- fixed gestation/maturation cost in energy and time
- offspring start with low energy reserves and reduced cognitive budget

Sexual reproduction, mate selection, and kinship complexity MAY be deferred to Phase 2.

### Phase 1 Reproduction Parameters

| Parameter          | Value | Rationale                                         |
|--------------------|-------|----------------------------------------------------|
| REPRODUCTION_AGE   | 13    | Earliest age for reproduction                      |
| REPRODUCTION_ENERGY| 55    | Both parents must have energy above this threshold |
| REPRODUCTION_COST  | 25    | Energy deducted from each parent per birth          |
| OFFSPRING_ENERGY   | 20    | Starting energy of newborn                          |

### Fertility Suppression Under Pressure

Reproduction probability is suppressed by two independent signals — ambient population pressure (acute, environment-wide) and each individual's own accumulated malnutrition debt (chronic, personal history):

```text
fertility = max(0.0, 1.0 − (pressure − 1.0) × 0.5)
if malnutrition_debt > 60.0:
    fertility = 0.0
else:
    fertility *= max(0.5, 1.0 − (malnutrition_debt / NUTRITION_DEBT_CAP) × 0.5)
```

Below pressure 1.0 the first term alone would exceed 1.0 (always fertile); it declines linearly above that, reaching zero at pressure 3.0. Independently, a resident whose malnutrition debt has crossed 60 (of a 100 cap) cannot reproduce at all regardless of current pressure or momentary energy surplus — chronic nutritional stress, not just this tick's caloric reserve, is what suppresses fecundity, mirroring the same debt-driven mechanism that governs Age Decline (see Mortality Factors below).

## Aging and Death

### Aging

- Residents SHOULD age over simulation time.
- Age SHOULD affect capability: young residents may have lower cognitive budgets and physical capacity; old residents may have accumulated memory and social bonds but declining physical capacity.
- Maximum lifespan SHOULD be bounded.

### Phase 1 Lifecycle Parameters

MAX_AGE is a theoretical ceiling, not a realistic expectation for most residents — actual lifespan is dominated by nutritional history (see Age Decline below), so a well-fed post-agricultural population approaches it while a chronically food-insecure pre-agricultural one does not:

| Parameter          | Value | Rationale                                   |
|--------------------|-------|---------------------------------------------|
| MAX_AGE            | 100   | Theoretical maximum lifespan                |
| REPRODUCTION_AGE   | 13    | Earliest age for reproduction               |
| INFANT_AGE         | 5     | End of high-mortality childhood period       |
| Age decline onset  | 30    | Earliest possible onset of physical decline (only reached this early under chronic malnutrition) |

### Mortality Factors

Death may occur from multiple causes, each modeled independently:

#### Starvation (Caloric Health Model)

Starvation is modeled as a direct, graduated function of caloric reserve (see RFC-0002 Phase 1 Calibration for the full kcal model) rather than a single cliff-edge check at zero energy.

- Below 2000 kcal (of a 3000 kcal reserve capacity), health begins to erode gradually: `1.5 × deficit_ratio × pressure_mult` per tick, where `deficit_ratio = (2000 − energy) / 2000`.
- Below 1500 kcal, an additional, steeper term applies: `8.0 × severe_deficit_ratio × pressure_mult` per tick, where `severe_deficit_ratio = (1500 − energy) / 1500`.
- `pressure_mult = max(1.0, population_pressure²)`, so both terms amplify under Malthusian overshoot, same as before.
- There is no separate "cold damage" or "starvation-at-zero" special case: cold, malnutrition, and hunger all funnel through this same caloric quantity. Cold zones and winter simply raise the daily caloric burn rate (see Winter Exposure below) faster than foraging can replace it, pushing residents into these bands.
- Foraging conversion rates are calibrated so a resident foraging under normal conditions comfortably stays above 2000 kcal — the erosion band should represent genuine scarcity (winter, overpopulation), not routine operation.

#### Malnutrition

- When population pressure exceeds 1.0, ALL residents lose health at `5.0 × (pressure − 1.0)²` per tick.
- This represents chronic food shortage affecting the entire population, not just those who have completely run out of energy.
- On top of this steady erosion, each tick under pressure carries an independent `(pressure − 1.0) × 0.1` chance of a sudden additional 10–35 health loss — an acute overcrowding-mortality event (disease outbreaks, accidents, violence incidental to crowding) layered on top of the smooth chronic term, rather than malnutrition being purely gradual.

#### Disease

- Base probability: 0.5% per tick per resident.
- Crowding bonus: +1.0% per additional resident on the same cell.
- Population pressure multiplier: probability × pressure² when over carrying capacity.
- Weakened residents (health < 40): probability × 1.5.
- Damage: 10–35 health points per episode.
- This is background, independent-per-resident disease risk. See Epidemic below for a distinct, population-scale mechanism.

#### Epidemic (Genetic Resistance)

Epidemics are distinct from ordinary background disease: a rarer, far more severe event that strikes a whole crowded area at once rather than rolling independently per resident per tick.

**Mechanism:**
- Each resident carries a heritable `immunity` trait (0–1, same inheritance/mutation model as other traits — RFC-0004 Trait System).
- Every tick, the engine finds the most crowded cell. If its population is at or above a density threshold, there is a small per-tick chance an outbreak ignites there.
- When an outbreak ignites, every resident within a radius of the hotspot is exposed simultaneously.
- Each exposed resident's mortality probability is `0.35 × (1 − immunity)` — a resident with immunity near 1.0 is nearly unaffected; one with immunity near 0 faces a high chance of being gravely stricken (40 health damage, often fatal in combination with other stressors).

**Why this matters:** because immunity is heritable, an epidemic does not kill uniformly — it selects. The residents who survive a severe outbreak are disproportionately the ones whose inherited immunity happened to be high, and they pass that trait to their offspring at the same rate as any other trait (mutation and blending included). Repeated epidemics in dense, settled populations should therefore raise average population immunity over generations — the same natural-selection-under-pressure pattern already established for food storage knowledge (RFC-0006), but operating on a genetic trait instead of a knowledge domain. This is deliberately left as a basic mechanism; more detailed genetics (specific resistance to specific pathogens, trade-offs, etc.) are a future refinement.

#### Infant Mortality

- Residents under age 5 face 2.5% per tick chance of health loss (8–20 damage).
- This produces meaningful childhood mortality consistent with primitive-era demographics.

#### Winter Exposure (Caloric Burn Rate, Not a Separate Damage Formula)

Winter creates acute food scarcity (0.005–0.05× regrowth relative to baseline, see RFC-0003) and raises daily caloric burn — there is no separate, scripted "winter death roll" or "cold damage" mechanic. Cold works entirely by raising how many kcal a resident burns per tick, which then interacts with the Starvation model above.

**Upkeep mechanism (RFC-0002 Phase 1 Calibration):**
- Every season (not just winter) has a zone-specific upkeep multiplier; winter carries the dominant cost: tropical 1.3×, temperate 1.8×, cold 2.8×. Spring/summer/autumn multipliers are close to 1.0 (mild, physically-motivated variation).
- Each tick (one day-night cycle) computes day loss and night loss separately: `day = season_mult × 0.8`, `night = season_mult × 1.2`, averaging back to exactly the season multiplier. This gives technologies distinct, physically sensible levers:
  - `shelter_building` reduces the season multiplier itself by up to 30% at full skill — it blunts exposure uniformly, day and night.
  - `fire_making` reduces the *night* multiplier specifically by up to 40% at full skill — fire helps when it's dark and cold, not during the day.
  - `clothing_making` reduces the resident's overall metabolic burn by up to 25% at full skill — personal insulation, worn constantly.
  - `food_storage` reduces burn by up to 30% at full skill — preserved food drawn down during scarcity.
  - These four reductions stack multiplicatively; no single technology alone reaches another's ceiling.
- Near-zero winter regrowth (0.005–0.05×) means foraging cannot offset this elevated burn, so caloric reserves deplete through the season and residents are pushed into the Starvation model's erosion/death bands above.
- Cold zone's upkeep (2.8×) is severe enough that without food storage, clothing, shelter, and fire knowledge, cold-zone residents are reliably killed off within a single winter. This is a deliberate consequence of the model, not a special-cased death rule.
- Tropical and temperate zones are survivable at baseline: winter is costly but not universally lethal, so a knowledge-free population persists there while thinning each winter.

**Discovery:** all four winter technologies (`food_storage`, `shelter_building`, `clothing_making`, `fire_making`) are discovered through the same Experiment pathway — a resident in the caloric death-zone (below 1500 kcal) during winter has a small per-tick chance of learning each independently. Colder zones and seasons push residents into this crisis state far more often, so these technologies emerge first and fastest exactly where they matter.

**Natural Selection Path:**
- Winters recur every year and impose real, repeated losses — this is not a single filtering event but an ongoing pressure.
- Residents with food storage knowledge lose energy more slowly each winter and so survive more reliably.
- Surviving knowledge-holders reproduce more (see Reproduction) and transmit knowledge to offspring with fidelity loss (see RFC-0006), so the proportion of knowledge-holders in the population rises over generations.
- If a lineage loses the knowledge (e.g. through population bottleneck or isolation), winter mortality reverts to the higher no-knowledge baseline for that group — knowledge loss has a real, felt cost.

#### Random Accidents

- 0.3% per tick chance of injury (8–22 damage), amplified by pressure_mult.
- Represents falls, animal attacks, drowning, and other environmental hazards.

#### Age Decline (Nutrition-Linked)

Age decline onset and severity depend on a resident's nutritional history, not chronological age alone.

**Mechanism:**
- Each resident accumulates `malnutrition_debt`: it rises while energy stays below a chronic-hunger threshold and slowly heals while energy stays above a well-fed threshold, capped at 100.
- Past age 30, decline probability per tick combines two terms: `(age − 30) / 60` (a slow ramp reaching its natural ceiling near MAX_AGE for a well-fed resident) plus `malnutrition_debt / 100 × 0.8` (which can add the equivalent of decades of aging at any age past 30 for a chronically hungry resident).
- Damage: 5 health points per episode.

**Why this matters:** a resident who forages hand-to-mouth in a pre-agricultural tropical zone — well-fed some days, hungry others — accumulates debt steadily and starts declining sharply in their 30s regardless of how many years MAX_AGE nominally allows. A resident in a food-secure, post-agricultural population with reliable surplus (see RFC-0003 Domestication) recovers from occasional shortfalls and can approach the full 100-year ceiling. This ties the abstract MAX_AGE constant to the same knowledge-and-environment dynamics that govern the rest of the simulation, rather than treating lifespan as a fixed demographic parameter.

### Death Classification

When a resident dies, the cause is classified as:

- `old_age` — exceeded MAX_AGE
- `starvation` — energy was 0 at time of death
- `infant_death` — died before INFANT_AGE
- `disease` — all other health-collapse deaths

### Legacy on Death

When a resident dies:

- material possessions SHOULD remain at the death location or transfer to nearby residents.
- knowledge held only by that resident MAY be lost unless previously transmitted.
- social bonds referencing the deceased SHOULD update (grief, memory, reputation).
- the resident's historical record MUST remain available per RFC-0001 Law 1.

## Social Interaction

Residents MUST be able to interact with other residents in proximity.

### Interaction Types

Phase 1 SHOULD support at least:

- communication (exchange of partial information)
- food sharing or gift giving
- cooperative action (joint foraging, joint construction)
- conflict (competition over resources, territory, mates)
- imitation (observing and copying behavior or technique)

### Communication

- Communication MUST require spatial proximity or a modeled transmission channel.
- Communication MUST NOT transfer perfect knowledge. Distortion, omission, and misunderstanding SHOULD be possible.
- Communication cost SHOULD be low relative to physical actions, enabling social behavior to emerge without prohibitive overhead.

### Conflict

- Conflict MUST be resolvable through physics-layer mechanics (energy cost, injury risk, outcome uncertainty).
- Conflict MUST NOT be scripted or predetermined.
- The weaker party MUST have some probability of escape, injury to the aggressor, or deterrence through allies.

### Resource Conflict

When multiple hungry residents compete for scarce food on the same cell (biomass < 15), there is an 18% chance of combat. Outcome is determined by strength traits with randomness. The loser takes 5–25 damage.

### Raiding

Raiding is a desperate survival behavior triggered when a resident is starving (energy < 540 kcal — see RFC-0002 for the kcal-scale energy model) with no local food available (biomass < 3 and leftover < 2 on the current cell):

- The resident attacks an adjacent resident who has more energy (> 900 kcal).
- Raid probability: `0.3 + risk_tolerance × 0.5`, plus `0.25 × (pressure − 1.2)` when pressure exceeds 1.2 — but only for residents with sociability < 0.5. Highly social residents (sociability ≥ 0.5) do not get this pressure-driven boost to their raid probability; overcrowding pushes the anti-social toward violence disproportionately, not the population uniformly.
- **Targeting is relatedness-biased (Hamilton's rule)**: relatedness is computed via `parent_id` (parent-child or full siblings both count as relatedness 0.5; everyone else 0.0). Below pressure 1.5, a raider prefers a stranger — someone with no positive bond and relatedness < 0.25 — over a raid target from among its own bonded relationships or kin, if any qualifying stranger is adjacent. At or above pressure 1.5, that bias collapses and any adjacent higher-energy resident is fair game, sorted by relatedness (least-related preferred) rather than filtered — representing conflict breaking out even within one's own established relationships once scarcity is severe enough. This targeting logic is purely individual-level bond/relatedness bias; RFC-0007 explicitly avoids an engine-authored Group/War object, so there is no faction-level conflict model, only this per-resident preference.
- If the raider wins (strength contest with randomness): steals up to 40% of victim's energy, victim takes 5–18 damage.
- If the raider loses: takes 10–28 damage.
- Raiding degrades social bonds between attacker and victim.

Raiding becomes frequent during high-pressure periods (pressure > 1.4), creating visible conflict cycles and food redistribution under scarcity.

### General Migration (Malthusian Release Valve)

Beyond winter-driven migration toward warmer zones, sustained high population pressure (> 1.3) combined with real hunger (energy < 1650 kcal) gives any resident a 20%-per-tick chance to instead move toward the best food it can see within a much wider search radius (`view radius + 4` cells) — spreading out into unclaimed, less-crowded territory rather than only competing or raiding locally. This is emergent spatial redistribution from individual foraging decisions, not a scripted settlement mechanic, and together with raiding forms the two release valves (flight and fight) that keep Malthusian overshoot from being resolved by mortality alone (see RFC-0007).

## Memory

Residents MUST have bounded, lossy memory.

### Memory Requirements

- Memory MUST be finite in capacity.
- Older or less-reinforced memories SHOULD decay over time.
- Memory SHOULD include at minimum:
  - spatial memory (places visited, resource locations known)
  - social memory (individuals encountered, interaction outcomes)
  - procedural memory (techniques or behaviors learned)
- Memory retrieval MAY be imperfect (partial recall, false associations).
- Capacity for spatial/social memory and capacity for procedural/knowledge memory MUST be
  governed separately (implemented — see Cognition Model below): a resident with room to
  track more places is not thereby able to hold more distinct skills, and vice versa.

### Memory and Knowledge

Memory is the individual-level substrate on which the knowledge system (RFC-0006) builds. Without persistent individual memory, there is no foundation for cultural transmission.

## Cognition Model (implemented)

Phase 1 originally specified "cognitive budget allocation" and "learning rate" as trait
categories (see Trait System below) and a finite memory capacity (see Memory Requirements
above), but left both unquantified. This section makes them concrete, using a
computer-hardware analogy that keeps the three resources conceptually distinct and
individually variable, as Law 8 requires:

- **IQ / CPU** — `Traits.intelligence`, a heritable trait in the same family as
  strength/speed/perception. It is a ceiling, not a guaranteed rate: actual "usable
  compute" is intelligence throttled by available energy
  (`usable_intelligence = intelligence × min(1, energy / COMPUTE_ENERGY_THRESHOLD)`),
  the same principle as a CPU clocking down under insufficient power. A starving genius
  learns no faster than a well-fed average mind. Thinking itself has a metabolic cost
  (`THINKING_ENERGY_COST`, scaled by intelligence), so raw intelligence is not a free
  advantage.
- **RAM / working memory** — `Resident.brain_capacity()`, bounding how many spatial-memory
  entries a resident can track at once. Varies by age (lower before `REPRODUCTION_AGE`,
  peak in adulthood, declining after `BRAIN_CAPACITY_ELDER_ONSET`), by chronic
  malnutrition (`malnutrition_debt`), and by the heritable intelligence trait. This
  replaces a single flat constant that was previously identical for every resident,
  which violated the Heterogeneity Requirement above.
- **Disk / long-term knowledge capacity** — `Resident.knowledge_capacity()`, bounding how
  many distinct knowledge domains (`known_knowledge` entries) a resident can hold onto at
  once. When a resident learns something new while already at capacity, the weakest-held
  domain is forgotten to make room. Writing (RFC-0006) raises this ceiling
  (`WRITING_KNOWLEDGE_CAPACITY_BONUS`) by externalizing memory outside any single brain —
  before this cap existed, a long-lived, well-traveled resident could accumulate every
  skill in the simulation, which is the literal mechanism behind the "everyone ends up
  knowing everything" unrealism this model exists to prevent.

### Cognition Parameters

| Parameter                        | Value | Rationale                                                        |
|-----------------------------------|-------|--------------------------------------------------------------------|
| COMPUTE_ENERGY_THRESHOLD          | 1200  | Energy at/above which intelligence runs at full throttle           |
| THINKING_ENERGY_COST              | 3.0   | Daily kcal cost of cognition, scaled by intelligence                |
| BASE_BRAIN_CAPACITY               | 50    | Working-memory slots at peak adulthood, well-nourished              |
| BRAIN_CAPACITY_CHILD_MULT         | 0.4   | Working memory is still developing before REPRODUCTION_AGE          |
| BRAIN_CAPACITY_ELDER_ONSET        | 60    | Age at which working-memory decline begins                          |
| BRAIN_CAPACITY_ELDER_SPAN         | 40    | Span over which that decline completes                              |
| BASE_KNOWLEDGE_CAPACITY           | 6     | Distinct knowledge domains an unlettered mind can hold               |
| WRITING_KNOWLEDGE_CAPACITY_BONUS  | 10    | Additional domains once writing externalizes memory                 |
| LEARNING_ENERGY_COST              | 8.0   | kcal cost to a listener who successfully learns something new       |
| TEACHING_ENERGY_COST              | 5.0   | kcal cost to a speaker for actively transmitting knowledge          |

### Consequences for Emergence

Teaching and learning both require energy surplus above the respective cost, same as
movement already required affording the terrain's movement cost. Combined with capacity
limits that vary by age, nutrition, and heritable intelligence, no individual can
realistically hold every skill or travel indefinitely regardless of condition — this is
what makes specialization and division of labor a consequence of individual constraint
rather than a scripted outcome, per the Heterogeneity Requirement's stated purpose.

## Trait System

Traits define how residents differ from each other.

### Trait Categories

Phase 1 SHOULD include traits affecting:

- physical capability (strength, speed, endurance)
- perception range or quality
- cognitive budget allocation (implemented — `intelligence` trait, throttled by energy; see Cognition Model)
- risk tolerance
- sociability (tendency toward cooperation vs. solitary behavior)
- learning rate (implemented — same `intelligence` trait; see Cognition Model)
- disease immunity (implemented — drives differential survival during epidemics, see Mortality Factors)
- carrying capacity (implemented — `carrying_capacity` trait, mean 10, occasional individuals well past 40; caps total personal resource stockpile, see `_add_resource`, and widens perception radius at the high end. `Resident.is_merchant()` is a pure threshold readout over this one trait — not an authored "Merchant" role — matching `is_gifted_scout()`'s pattern of emergence from a trait combination/value rather than a hardcoded category)

### Trait Properties

- Traits MUST be heritable with variation (see Reproduction).
- Traits SHOULD affect action outcomes (a stronger resident gathers faster, a more perceptive resident detects threats earlier).
- Traits MUST NOT include "civilization-level" attributes like "leadership" or "diplomacy" as built-in categories. Such capabilities, if they appear, must emerge from combinations of simpler traits and experience.

## Group Behavior

The life engine MUST NOT hardcode groups, tribes, or social structures.

### Emergence Path

Groups SHOULD emerge from:

- repeated positive interactions between individuals
- shared resource access
- proximity and co-habitation
- kinship (once reproduction produces family lines)
- mutual defense benefit

### Detection vs. Design

The engine MAY detect and label emergent groups for observation and analysis purposes, but MUST NOT grant detected groups any privilege, bonus, or capability that the constituent individuals do not already possess.

A "tribe" is a pattern the engine notices, not a unit the engine creates.

## Boundary with AI Layer

The life engine handles the what and the how of resident existence.

The AI layer (RFC-0005) handles the why of non-routine decisions.

### Division of Responsibility

Life engine (rules, every tick):

- maintenance cost deduction
- perception filtering
- routine survival decisions (eat available food, flee obvious danger, sleep when exhausted)
- intent submission and outcome processing
- state updates
- memory decay

AI layer (LLM, sparse invocation):

- novel situation assessment ("I've never seen this before")
- high-stakes social decisions ("should I trust this stranger?")
- cultural acts ("what should I call this place?")
- migration decisions ("should I leave this area?")
- negotiation of non-routine exchanges

This boundary is critical for cost control. The life engine MUST be able to run a full tick for a resident without invoking the AI layer in the common case.

## Constitutional Compliance

This RFC is subordinate to RFC-0001 Universe Constitution.

### Law 0: Persistence

- resident death does not delete history

### Law 1: Legacy Persists

- possessions, knowledge traces, and built structures survive their creator

### Law 3: Causality

- every resident state change has a traceable cause

### Law 4: Energy Conservation

- survival, movement, reproduction, and action all consume modeled energy

### Law 5: Matter Conservation

- resource consumption by residents depletes local stocks

### Law 6: Knowledge Cannot Appear from Nothing

- residents learn only through observation, experiment, imitation, inheritance, or communication

### Law 7: Bounded Cognition

- strict separation between world state and agent belief state

### Law 8: Bounded Computation

- heterogeneous cognitive budgets, no perfect-play reasoning
- implemented via the `intelligence` trait, throttled by available energy, plus
  age/nutrition-varying working-memory and knowledge-capacity ceilings — see Cognition Model

### Law 10: Entropy

- memory decays, health degrades without maintenance, possessions deteriorate

## Phase 1 Implementation Guidance

A good Phase 1 life engine would include:

- 50–1000 residents (start small, scale up)
- per-tick survival loop with energy accounting
- local perception with limited radius
- intent-action-resolution cycle through physics
- simple trait vector with heritable variation
- bounded lossy memory
- basic social interaction (communication, sharing, conflict)
- reproduction with energy cost and trait drift
- aging and natural death
- no LLM calls in the default tick path

That is enough to produce migration, clustering, resource competition, proto-cooperation, and behavioral divergence across populations — the preconditions for everything that comes later.

## Open Questions

- What is the optimal perception radius for Phase 1 (too small = isolation, too large = omniscience)?
- How should initial population be seeded — clustered, scattered, or mixed?
- What is the minimum memory capacity that supports useful social behavior without excessive state?
- Should group warfare (coordinated multi-resident attacks) be modeled, or does individual raiding suffice for Phase 1?
- How should emerging agricultural behavior (if it appears) modify mortality parameters?

## Future Dependencies

The following RFCs depend directly on this one:

- `RFC-0005 AI Decision`
- `RFC-0006 Knowledge System`
- `RFC-0007 Civilization Emergence`
- `RFC-0009 Player Protocol`

## Conclusion

The life engine is where OCP stops being a set of rules and starts being a world.

If residents face real survival pressure, perceive locally, vary individually, reproduce with drift, remember lossily, and interact socially — then the preconditions for emergent complexity exist.

The life engine does not need to be smart. It needs to be honest.
