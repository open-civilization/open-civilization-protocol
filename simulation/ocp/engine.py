"""
OCP Phase 1 Simulation Engine
Minimal world tick runner implementing RFC-0001 through RFC-0007.
"""

from dataclasses import dataclass, field
from typing import Optional
import random
import math
import time
import threading
from .ai import AIEngine

# ── Configuration ──

GRID_W = 60
GRID_H = 80
INITIAL_POPULATION = 55  # Seeded near total baseline carrying capacity (~5 cold + 10 temperate + 40 tropical)
MAX_AGE = 100  # theoretical ceiling; nutritional history determines who actually approaches it
REPRODUCTION_AGE = 13

# ── Energy Model (kcal) ──
# `energy` is a resident's caloric reserve, modeled in real kilocalorie units so mortality
# thresholds are physically interpretable rather than an abstract 0-100 scale. A tick
# represents one full day-night cycle; each tick deducts one day's net caloric loss.
MAX_ENERGY = 3000.0             # full caloric reserve — "well-fed" baseline
REPRODUCTION_ENERGY = 1800.0    # reserve required (55% of max) before reproduction is attempted
REPRODUCTION_COST = 750.0       # reserve spent per parent per birth
OFFSPRING_ENERGY = 600.0        # newborn starting reserve
BASELINE_ENERGY_COST = 60.0     # baseline daily metabolic burn before season/technology modifiers
PERCEPTION_BASE_RADIUS = 3
MAX_HEALTH = 100.0
SEASON_LENGTH = 8
TRAIT_MUTATION = 0.15

# ── Cognition Model (IQ / working memory / long-term knowledge capacity) ──
# Intelligence is a heritable trait, same family as strength/speed/perception. It sets a
# learning-speed ceiling, but like a CPU under power throttling, that ceiling is only
# reachable when energy is adequate — a starving brain thinks and learns worse regardless
# of raw intelligence (see Resident.usable_intelligence). This is the concrete mechanism
# RFC-0001 Law 8 (Bounded Computation) calls for: cognitive budgets that vary per
# individual rather than a single constant applied to everyone.
COMPUTE_ENERGY_THRESHOLD = 1200.0  # energy at/above which intelligence runs at full throttle
THINKING_ENERGY_COST = 3.0         # baseline daily kcal cost of cognition, scales with intelligence

# Working memory ("RAM") bounds how many spatial locations a resident can actively track
# at once. Replaces the old flat MEMORY_CAPACITY constant, which was identical for every
# resident regardless of age or nutrition — a direct violation of RFC-0004's Heterogeneity
# Requirement (see Resident.brain_capacity).
BASE_BRAIN_CAPACITY = 50            # working-memory slots at peak adulthood, well-nourished
BRAIN_CAPACITY_CHILD_MULT = 0.4     # still developing before REPRODUCTION_AGE
BRAIN_CAPACITY_ELDER_ONSET = 60     # working memory begins declining from this age
BRAIN_CAPACITY_ELDER_SPAN = 40      # ...and bottoms out around ELDER_ONSET + ELDER_SPAN

# Long-term knowledge capacity ("disk") caps how many distinct knowledge domains a
# resident can hold onto at once (see Resident.knowledge_capacity). Before this,
# known_knowledge had no ceiling at all — any long-lived, well-traveled resident could
# accumulate every skill in the game, which is exactly the "everyone ends up knowing
# everything" unrealism this model exists to prevent.
BASE_KNOWLEDGE_CAPACITY = 6           # distinct knowledge domains an unlettered mind can hold
WRITING_KNOWLEDGE_CAPACITY_BONUS = 10 # writing is external memory (see the "external memory
                                       # organ" comment on WRITING_DISCOVERY_CHANCE below); it
                                       # raises the effective ceiling rather than the individual
                                       # brain having to hold everything itself

LEARNING_ENERGY_COST = 8.0   # kcal cost to a listener who successfully learns something new
TEACHING_ENERGY_COST = 5.0   # kcal cost to a speaker for actively transmitting knowledge

# Mortality factors — base rates are mild; population pressure amplifies them
DISEASE_BASE_CHANCE = 0.005
DISEASE_CROWD_BONUS = 0.01
DISEASE_DMG_MIN = 10
DISEASE_DMG_MAX = 35
# Epidemic — a distinct, rarer, population-scale event (see _tick for the mechanism)
EPIDEMIC_DENSITY_THRESHOLD = 6   # radius-2 local population that creates outbreak risk
EPIDEMIC_IGNITION_CHANCE = 0.02  # per tick, once density threshold is crossed anywhere
EPIDEMIC_RADIUS = 3              # spatial radius of affected residents around the hotspot
EPIDEMIC_BASE_MORTALITY = 0.35   # death chance for a resident with immunity=0
EPIDEMIC_DMG = 40                # health damage dealt to stricken residents
INFANT_AGE = 5
INFANT_MORTALITY_CHANCE = 0.025
CONFLICT_CHANCE = 0.18
CONFLICT_DMG_MIN = 5
CONFLICT_DMG_MAX = 25
TERRAIN_HAZARD = {'mountain': 0.06, 'river': 0.04, 'desert': 0.04, 'coast': 0.01}
HAZARD_DMG_MIN = 5
HAZARD_DMG_MAX = 20
ACCIDENT_CHANCE = 0.003
ACCIDENT_DMG_MIN = 8
NUTRITION_STRESS_ENERGY = 900    # below this (30% of max), chronic malnutrition debt accumulates
NUTRITION_RECOVERY_ENERGY = 1950 # above this (65% of max), malnutrition debt slowly heals
NUTRITION_DEBT_RATE = 0.5        # debt gained per tick while chronically hungry
NUTRITION_RECOVERY_RATE = 0.15   # debt healed per tick while reliably well-fed
NUTRITION_DEBT_CAP = 100.0      # debt ceiling
AGE_DECLINE_ONSET = 30          # age decline can begin this early if malnourished
AGE_DECLINE_SPAN = 60           # a well-fed resident's decline stretches across this many years
ACCIDENT_DMG_MAX = 22

TERRAIN = {
    'plains':   {'move': 1.0, 'cap': 30,  'regrow': 0.7, 'water': False, 'color': '#8fbc5a'},
    'forest':   {'move': 1.8, 'cap': 45,  'regrow': 1.0, 'water': False, 'color': '#2d6a2e'},
    'river':    {'move': 2.5, 'cap': 25,  'regrow': 0.6, 'water': True,  'color': '#4a90d9'},
    'lake':     {'move': 99., 'cap': 15,  'regrow': 0.4, 'water': True,  'color': '#1a5fb4'},
    'mountain': {'move': 3.5, 'cap': 6,   'regrow': 0.08,'water': False, 'color': '#8a7461'},
    'desert':   {'move': 2.0, 'cap': 3,   'regrow': 0.02,'water': False, 'color': '#d4a843'},
    'coast':    {'move': 1.2, 'cap': 28,  'regrow': 0.6, 'water': True,  'color': '#7ecfc0'},
}

SEASONS = ['spring', 'summer', 'autumn', 'winter']

# Climate zones: top = cold, middle = temperate, bottom = tropical
# Non-winter multipliers set high to ensure baseline viability (40 tropical, 10 temperate, 5 cold)
# Winter multipliers set low to create a seasonal bottleneck, but not automatic extinction —
# knowledge softens the bottleneck, absence of knowledge means higher (not total) mortality
#
# `*_upkeep` fields are per-season caloric burn multipliers (independent from the plain season
# fields above, which govern food regrowth, not personal metabolism). Non-winter multipliers
# stay close to 1.0 — mild, physically-motivated variation — so the extensively-tuned baseline
# survivability is preserved; winter carries the dominant seasonal cost as before.
CLIMATE_ZONES = {
    'cold':      {'spring': 1.1, 'summer': 0.8, 'autumn': 0.35, 'winter': 0.005,
                  'spring_upkeep': 0.95, 'summer_upkeep': 1.0, 'autumn_upkeep': 1.1, 'winter_upkeep': 2.8,
                  'grazing_suitability': 1.0, 'farming_suitability': 0.1},
    'temperate': {'spring': 1.4, 'summer': 1.0, 'autumn': 0.55, 'winter': 0.02,
                  'spring_upkeep': 0.9, 'summer_upkeep': 1.0, 'autumn_upkeep': 1.05, 'winter_upkeep': 1.8,
                  'grazing_suitability': 0.25, 'farming_suitability': 1.0},
    'tropical':  {'spring': 1.2, 'summer': 1.0, 'autumn': 0.75, 'winter': 0.05,
                  'spring_upkeep': 0.9, 'summer_upkeep': 1.05, 'autumn_upkeep': 1.0, 'winter_upkeep': 1.3,
                  'grazing_suitability': 0.0, 'farming_suitability': 0.0},
}

# Terrain suitability for domestication (physical property of the land, like biomass_cap)
# Cold zone pasture-grade terrain suits grazing; temperate arable terrain suits crop cultivation.
# Tropical zone's zone-level suitability above is 0, so terrain suitability never activates there.
TERRAIN_GRAZING = {'plains': 0.8, 'mountain': 1.0, 'desert': 0.3}
TERRAIN_FARMING = {'plains': 1.0, 'river': 0.7, 'forest': 0.2}

DOMESTICATION_DISCOVERY_CHANCE = 0.0025  # per qualifying forage tick, before suitability scaling
# Not every wild variant a forager experiments with actually becomes a stable domesticate —
# most real domestication attempts throughout history failed (of the world's ~200,000 plant
# species, only a few hundred were ever domesticated). A discovery "hit" above represents
# trying a promising wild plant/animal; whether it actually takes is a separate, harder roll.
DOMESTICATION_SUCCESS_CHANCE = 0.45
# Residents forage nomadically and rarely revisit the exact same cell many ticks in a row,
# so a single visit must contribute a meaningful amount for land improvement to be observable
# at population scale; decay is slow so occasional return visits still net-accumulate.
CULTIVATION_GAIN_RATE = 1.2  # cultivation gained per forage tick at full skill and suitability
CULTIVATION_DECAY = 0.0002  # cultivation lost per tick when not actively tended
CULTIVATION_MAX_BONUS = 7.0  # at cultivation=1.0, regrow is multiplied by (1 + this) — real farmland
                              # vastly outproduces wild foraging per unit area, BEFORE any further
                              # agricultural technology (see ag_tech_mult / CROP_ARCHETYPES below)

# Crop archetypes — zoology/botany-flavored energy density profiles, randomly assigned when
# crop_cultivation is first successfully domesticated, weighted by which staple crop TYPE
# actually suits the discoverer's climate zone (grains dominate temperate agriculture
# precisely because of superior caloric yield density per cultivated area; tropical
# agriculture historically leaned on calorie-dense-per-labor but bulkier tubers; legumes
# are viable everywhere but are a secondary rather than staple crop).
CROP_ARCHETYPES = {
    'grain': {'energy_density_mult': 1.4, 'zone_weights': {'temperate': 3.0, 'tropical': 0.5, 'cold': 0.4}},
    'tuber': {'energy_density_mult': 1.0, 'zone_weights': {'temperate': 0.8, 'tropical': 3.0, 'cold': 0.6}},
    'legume': {'energy_density_mult': 1.15, 'zone_weights': {'temperate': 1.2, 'tropical': 1.5, 'cold': 0.3}},
}
LIVESTOCK_ARCHETYPES = {
    'grazer': {'energy_density_mult': 1.1, 'zone_weights': {'cold': 3.0, 'temperate': 1.0, 'tropical': 0.3}},
    'browser': {'energy_density_mult': 0.95, 'zone_weights': {'tropical': 2.0, 'temperate': 1.0, 'cold': 0.2}},
}

# Agricultural technology ladder — each tier multiplies the land's energy-density ceiling
# further, mirroring the real historical trajectory (irrigation civilizations, then
# selective breeding of higher-yield varieties over generations, then industrial-era
# fertilizer/pesticides — the "Green Revolution," the single largest jump in yield per
# area in history). A cell's ag_tech_mult ratchets up to the best tier any farmer working
# it has achieved and never decreases — technique embedded in how a plot is worked doesn't
# un-happen, even though the plot's cultivation LEVEL can still lapse if untended.
IRRIGATION_DISCOVERY_CHANCE = 0.003    # per tick, requires crop_cultivation + water-adjacent cell
IRRIGATION_MULT = 1.5
BREEDING_DISCOVERY_CHANCE = 0.002      # per tick, requires deep crop_cultivation mastery
BREEDING_SKILL_THRESHOLD = 60.0        # generations of selection require real mastery, not a novice
BREEDING_MULT = 1.6
FERTILIZER_DISCOVERY_CHANCE = 0.0015   # per tick, requires writing (systematic record-keeping) + breeding
FERTILIZER_MULT = 2.2

# ── Caloric Health Model ──
# Cold, hunger, and technology are unified through a single physical quantity: how many
# kcal a resident has in reserve. There is no separate "cold damage" formula — cold works
# entirely by raising caloric burn rate (below), and health only erodes as a direct,
# graduated consequence of the caloric reserve itself dropping through two real thresholds.
CALORIE_EROSION_THRESHOLD = 2000.0  # below this, health begins to erode (graduated)
CALORIE_DEATH_ZONE = 1500.0         # below this, erosion becomes severe
HEALTH_EROSION_RATE = 1.5           # health/tick at full deficit within the erosion band (2000->0)
DEATH_ZONE_RATE = 8.0               # additional health/tick at full deficit within the death band (1500->0)

# Day/night split: each tick is one full day-night cycle. Night loss and day loss are
# weighted equally (0.5/0.5) so their average exactly equals the season's upkeep multiplier
# — this preserves prior calibration exactly while giving fire a specific, physically
# sensible lever (fire helps at night; it does nothing about daytime heat).
DAY_LOSS_FACTOR = 0.8
NIGHT_LOSS_FACTOR = 1.2

# Shelter, clothing, and fire — Experiment pathway triggered by direct caloric crisis
# (reserve in the death-zone band). Colder zones and seasons push residents into this
# state far more often, so these technologies emerge first and fastest exactly where they
# matter — no separate zone gate is needed beyond the caloric-crisis condition itself.
SHELTER_DISCOVERY_CHANCE = 0.50   # per winter tick spent in caloric crisis
CLOTHING_DISCOVERY_CHANCE = 0.10  # per winter tick spent in caloric crisis
FIRE_DISCOVERY_CHANCE = 0.04      # per winter tick spent in caloric crisis
SHELTER_UPKEEP_REDUCTION = 0.3    # shelter blunts environmental exposure, day and night
CLOTHING_UPKEEP_REDUCTION = 0.25  # clothing reduces personal metabolic loss, uniformly
FIRE_NIGHT_REDUCTION = 0.4        # fire specifically offsets the amplified nighttime loss

# ── Knowledge Transmission Channels (information-theoretic channel model) ──
# Cross-individual and cross-generation knowledge transfer is modeled as a lossy channel.
# Each communication technology a resident has discovered opens a channel with its own
# base retention (fidelity). When multiple independent channels are available for the
# same transmission event, they combine using the standard redundant-channel formula
# from reliability engineering: a message survives if AT LEAST ONE channel gets it through,
# so combined_retention = 1 - product(1 - channel_i) over all available channels.
FIDELITY_IMITATION = 0.30   # floor: watching + instinctive inheritance, no verbal exchange
FIDELITY_ORAL = 0.60        # spoken language: explicit verbal teaching
FIDELITY_WRITTEN = 0.95     # writing: symbolic external memory, near-lossless encoding

# Spoken language is not a philosophical tool invented in a vacuum — it is a high-pressure
# survival cooperation protocol: a way to compress and relay fitness-relevant information
# between bounded-cognition individuals (RFC-0001 Law 7). It requires three conditions
# together, not any single trigger:
#   - cooperation payoff: an actual cooperative act with the other individual (food sharing
#     is the strongest available signal), not mere proximity or small talk
#   - repeated game: the same pair interacting many times (a stranger met once has no reason
#     to develop shared signals with you; someone you rely on repeatedly does)
#   - coordination pressure: real environmental uncertainty/scarcity (population pressure)
#     making joint action valuable, plus embeddedness in an actual group (enough bonds) —
#     a solitary individual has no one to coordinate with regardless of pressure
LANGUAGE_GROUP_SIZE = 2              # must be embedded in a real, sustained group
LANGUAGE_BOND_THRESHOLD = 0.1        # this specific relationship must carry real cooperative value
LANGUAGE_REPEAT_THRESHOLD = 3        # repeated game — interacted with this individual several times
LANGUAGE_PRESSURE_THRESHOLD = 0.01    # environmental uncertainty/scarcity creates coordination payoff
LANGUAGE_DISCOVERY_CHANCE = 0.02     # per qualifying interaction
LANGUAGE_COOPERATION_BONUS = 4.0     # multiplier when the interaction was an actual cooperative act

# Writing is not oral tradition's natural extension — it is an external memory organ a
# civilization grows once oral memory alone can no longer carry its own complexity. It
# requires: mature spoken language already in place, a stable/organized group (not a
# transient encounter), a memory deficit (enough distinct knowledge domains that individual
# recall becomes unreliable), and resource surplus (recording is itself costly time/effort
# that must be affordable) — matching real writing's historical origins in accounting,
# storage records, and land/name tracking, not literature.
WRITING_DISCOVERY_CHANCE = 0.003     # per qualifying tick
WRITING_COMPLEXITY_THRESHOLD = 3     # distinct knowledge domains needed to motivate a record
WRITING_ENERGY_THRESHOLD = 1650      # writing requires surplus, not survival-mode scarcity
WRITING_GROUP_SIZE = 3               # writing serves a larger, more organized group than language alone
WRITING_PRESSURE_THRESHOLD = 0.9     # society has grown to fill its available capacity


def _pick_archetype(archetypes, zone):
    """Weighted-random selection of a crop/livestock archetype for the given climate zone —
    which specific staple a population ends up with is a random outcome of what was
    available to experiment with locally, not a designed choice."""
    names = list(archetypes.keys())
    weights = [archetypes[n]['zone_weights'].get(zone, 0.1) for n in names]
    return random.choices(names, weights=weights, k=1)[0]


def _ag_tech_mult(r):
    """The energy-density ceiling multiplier this resident's current agricultural
    knowledge would confer if applied to a plot — crop/livestock archetype x irrigation x
    selective breeding x fertilizer, each an independent, stacking tier."""
    mult = 1.0
    if 'crop_cultivation' in r.known_knowledge:
        crop_type = r.known_knowledge['crop_cultivation'].get('crop_type')
        if crop_type in CROP_ARCHETYPES:
            mult *= CROP_ARCHETYPES[crop_type]['energy_density_mult']
    if 'animal_husbandry' in r.known_knowledge:
        livestock_type = r.known_knowledge['animal_husbandry'].get('crop_type')
        if livestock_type in LIVESTOCK_ARCHETYPES:
            mult *= LIVESTOCK_ARCHETYPES[livestock_type]['energy_density_mult']
    if 'irrigation' in r.known_knowledge:
        mult *= IRRIGATION_MULT
    if 'selective_breeding' in r.known_knowledge:
        mult *= BREEDING_MULT
    if 'fertilizer' in r.known_knowledge:
        mult *= FERTILIZER_MULT
    return mult


def _transmission_fidelity(speaker, pressure):
    """Best available channel fidelity for knowledge originating from `speaker`,
    combining independent channels (writing + oral) via redundant-channel recovery."""
    has_writing = 'writing' in speaker.known_knowledge
    has_language = 'spoken_language' in speaker.known_knowledge
    if has_writing and has_language:
        return 1 - (1 - FIDELITY_WRITTEN) * (1 - FIDELITY_ORAL)  # ≈ 0.98
    if has_writing:
        return FIDELITY_WRITTEN
    if has_language:
        return FIDELITY_ORAL
    return FIDELITY_IMITATION


def _learn_knowledge(r, kname, entry):
    """Add a brand-new knowledge domain to a resident, respecting their long-term
    knowledge capacity ('disk', see Resident.knowledge_capacity). If already full, the
    weakest-held domain is forgotten to make room — knowledge storage is finite, not an
    ever-growing dict, which is what let any long-lived resident learn every skill in the
    game before this cap existed."""
    if kname in r.known_knowledge:
        return
    if len(r.known_knowledge) >= r.knowledge_capacity():
        weakest = min(r.known_knowledge.items(), key=lambda kv: kv[1].get('level', 0))[0]
        del r.known_knowledge[weakest]
        r.skills.pop(weakest, None)
    r.known_knowledge[kname] = entry
    r.skills[kname] = entry['level'] * 100


def _reinforce_knowledge(r, kname, base_rate):
    """Grow an already-known skill's level through practice, scaled by the resident's
    usable intelligence (IQ throttled by available energy) — smarter, better-fed
    individuals learn faster from the same amount of practice."""
    if kname not in r.known_knowledge:
        return
    current = r.known_knowledge[kname]['level']
    learning_mult = 0.5 + r.usable_intelligence()
    r.known_knowledge[kname]['level'] = min(1.0, current + base_rate * (1.0 - current) * learning_mult)
    r.skills[kname] = r.known_knowledge[kname]['level'] * 100


def climate_zone(y):
    third = GRID_H // 3
    if y < third:
        return 'cold'
    elif y < third * 2:
        return 'temperate'
    return 'tropical'

SYLLABLES = [
    'ka','ri','mo','tu','na','le','si','ba','do','en',
    'fa','gu','hi','jo','ku','la','mi','no','pa','ro',
    'sa','ti','un','va','we','xi','yo','zu','ar','el',
]


# ── Data Types ──

@dataclass
class Cell:
    x: int
    y: int
    terrain: str
    elevation: float
    biomass: float
    biomass_cap: float
    water: bool
    climate: str = 'temperate'
    leftover: float = 0.0  # Food left behind by residents (emergent storage)
    cultivation: float = 0.0  # Land improvement from sustained farming/grazing (0-1, decays if untended)
    ag_tech_mult: float = 1.0  # Ratcheting energy-density ceiling for this plot (crop archetype x
                                # irrigation x selective breeding x fertilizer); never decreases once
                                # achieved — technique embedded in a plot's practice doesn't un-happen,
                                # even though the *land's* cultivation level can still lapse if untended

    def passable(self):
        return self.terrain != 'lake'

    def season_mult(self, season):
        return CLIMATE_ZONES[self.climate][season]


@dataclass
class Traits:
    strength: float
    speed: float
    perception: float
    endurance: float
    sociability: float
    risk_tolerance: float
    immunity: float = 0.5  # natural disease resistance; heritable, drives epidemic survival
    intelligence: float = 1.0  # cognitive ceiling — learning speed & decision quality,
                                # throttled by available energy (Resident.usable_intelligence)

    @staticmethod
    def random():
        return Traits(
            strength=random.uniform(0.6, 1.4),
            speed=random.uniform(0.6, 1.4),
            perception=random.uniform(0.6, 1.4),
            endurance=random.uniform(0.6, 1.4),
            sociability=random.uniform(0.1, 0.9),
            risk_tolerance=random.uniform(0.1, 0.9),
            immunity=random.uniform(0.1, 0.9),
            intelligence=random.uniform(0.6, 1.4),
        )

    def mutate(self):
        def m(v, lo, hi):
            return max(lo, min(hi, v + random.gauss(0, TRAIT_MUTATION)))
        return Traits(
            strength=m(self.strength, 0.3, 1.8),
            speed=m(self.speed, 0.3, 1.8),
            perception=m(self.perception, 0.3, 1.8),
            endurance=m(self.endurance, 0.3, 1.8),
            sociability=m(self.sociability, 0.0, 1.0),
            risk_tolerance=m(self.risk_tolerance, 0.0, 1.0),
            immunity=m(self.immunity, 0.0, 1.0),
            intelligence=m(self.intelligence, 0.3, 1.8),
        )

    def blend(self, other):
        return Traits(
            strength=(self.strength + other.strength) / 2,
            speed=(self.speed + other.speed) / 2,
            perception=(self.perception + other.perception) / 2,
            endurance=(self.endurance + other.endurance) / 2,
            sociability=(self.sociability + other.sociability) / 2,
            risk_tolerance=(self.risk_tolerance + other.risk_tolerance) / 2,
            immunity=(self.immunity + other.immunity) / 2,
            intelligence=(self.intelligence + other.intelligence) / 2,
        ).mutate()


@dataclass
class MemEntry:
    x: int
    y: int
    biomass: float
    tick: int


@dataclass
class Bond:
    rid: int
    quality: float
    last_tick: int
    interactions: int = 0  # repeated-game counter — how many times this pair has interacted


@dataclass
class Resident:
    id: int
    name: str
    x: int
    y: int
    age: int
    energy: float
    health: float
    traits: Traits
    alive: bool
    parent_id: Optional[int]
    generation: int
    memory: list
    bonds: dict
    birth_tick: int
    death_tick: Optional[int] = None
    death_cause: Optional[str] = None
    children: int = 0
    food_total: float = 0.0
    skills: dict = field(default_factory=lambda: {'food_storage': 0.0})
    known_knowledge: dict = field(default_factory=lambda: {})  # knowledge_name -> {level, source, tick_learned}
    malnutrition_debt: float = 0.0  # cumulative nutritional stress; drives aging independent of raw age
    energy_intake_today: float = 0.0  # gross kcal gained this tick (foraging, harvest, being fed)
    energy_spent_today: float = 0.0   # gross kcal spent this tick (upkeep + whatever action was taken)

    def view_radius(self):
        return max(1, int(PERCEPTION_BASE_RADIUS * self.traits.perception))

    def usable_intelligence(self):
        """Raw IQ throttled by available energy — a starving brain can't think at its
        ceiling, the same principle as a CPU clocking down under insufficient power.
        Used to scale learning speed everywhere knowledge/skill levels grow."""
        return self.traits.intelligence * min(1.0, self.energy / COMPUTE_ENERGY_THRESHOLD)

    def brain_capacity(self):
        """Working-memory slot count ('RAM') — how many spatial-memory entries this
        resident can track at once. Varies by age (still developing in childhood,
        declining in old age) and by chronic malnutrition, not a flat global constant."""
        if self.age < REPRODUCTION_AGE:
            age_mult = BRAIN_CAPACITY_CHILD_MULT + (1.0 - BRAIN_CAPACITY_CHILD_MULT) * (self.age / REPRODUCTION_AGE)
        elif self.age > BRAIN_CAPACITY_ELDER_ONSET:
            decline = min(1.0, (self.age - BRAIN_CAPACITY_ELDER_ONSET) / BRAIN_CAPACITY_ELDER_SPAN)
            age_mult = 1.0 - decline * (1.0 - BRAIN_CAPACITY_CHILD_MULT)
        else:
            age_mult = 1.0
        nutrition_mult = 1.0 - (self.malnutrition_debt / NUTRITION_DEBT_CAP) * 0.5
        return max(5, int(BASE_BRAIN_CAPACITY * age_mult * nutrition_mult * (0.7 + 0.3 * self.traits.intelligence)))

    def knowledge_capacity(self):
        """Long-term knowledge storage ('disk') — how many distinct knowledge domains this
        resident can hold onto at once. Writing externalizes memory, raising the ceiling
        (see the "external memory organ" comment on WRITING_DISCOVERY_CHANCE)."""
        cap = BASE_KNOWLEDGE_CAPACITY * (0.7 + 0.3 * self.traits.intelligence)
        if 'writing' in self.known_knowledge:
            cap += WRITING_KNOWLEDGE_CAPACITY_BONUS
        return max(1, int(cap))

    def upkeep(self):
        return BASELINE_ENERGY_COST / self.traits.endurance + THINKING_ENERGY_COST * self.traits.intelligence


# ── World Generation ──

def _noise(w, h, scale):
    cw, ch = w // scale + 2, h // scale + 2
    coarse = [[random.random() for _ in range(cw)] for _ in range(ch)]
    out = [[0.0] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            fx, fy = x / scale, y / scale
            ix, iy = int(fx), int(fy)
            dx = (fx - ix); dx = dx * dx * (3 - 2 * dx)
            dy = (fy - iy); dy = dy * dy * (3 - 2 * dy)
            out[y][x] = ((coarse[iy][ix] * (1-dx) + coarse[iy][ix+1] * dx) * (1-dy)
                       + (coarse[iy+1][ix] * (1-dx) + coarse[iy+1][ix+1] * dx) * dy)
    return out


def _octave_noise(w, h, octaves=3):
    result = [[0.0] * w for _ in range(h)]
    amp, total = 1.0, 0.0
    for i in range(octaves):
        scale = max(2, 16 >> i)
        layer = _noise(w, h, scale)
        for y in range(h):
            for x in range(w):
                result[y][x] += layer[y][x] * amp
        total += amp
        amp *= 0.5
    for y in range(h):
        for x in range(w):
            result[y][x] /= total
    return result


def generate_world(seed=None):
    if seed is not None:
        random.seed(seed)
    elev = _octave_noise(GRID_W, GRID_H)
    moist = _octave_noise(GRID_W, GRID_H)
    grid = []
    for y in range(GRID_H):
        row = []
        cz = climate_zone(y)
        for x in range(GRID_W):
            e, m = elev[y][x], moist[y][x]
            if cz == 'cold':
                if e > 0.65:                         t = 'mountain'
                elif e < 0.18 and m > 0.55:          t = 'lake'
                elif e < 0.22 and m > 0.50:          t = 'river'
                elif m < 0.30:                       t = 'desert'
                elif m > 0.55:                       t = 'forest'
                else:                                t = 'plains'
            elif cz == 'tropical':
                if e > 0.78:                         t = 'mountain'
                elif e < 0.20 and m > 0.50:          t = 'lake'
                elif e < 0.28 and m > 0.40:          t = 'river'
                elif e < 0.32 and m > 0.30:          t = 'coast'
                elif m > 0.45:                       t = 'forest'
                elif m < 0.15:                       t = 'desert'
                else:                                t = 'plains'
            else:
                if e > 0.72:                         t = 'mountain'
                elif e < 0.18 and m > 0.55:          t = 'lake'
                elif e < 0.25 and m > 0.45:          t = 'river'
                elif e < 0.30 and m > 0.35:          t = 'coast'
                elif m > 0.60:                       t = 'forest'
                elif m < 0.25:                       t = 'desert'
                else:                                t = 'plains'
            props = TERRAIN[t]
            row.append(Cell(x, y, t, e,
                            props['cap'] * random.uniform(0.4, 0.9),
                            props['cap'], props['water'], cz))
        grid.append(row)
    return grid


def _rand_name():
    return ''.join(random.choice(SYLLABLES) for _ in range(random.randint(2, 3))).capitalize()


def _spawn(rid, grid, tick, parent=None, partner=None):
    if parent:
        x, y = parent.x, parent.y
        traits = parent.traits.blend(partner.traits) if partner else parent.traits.mutate()
        gen = parent.generation + 1
        pid = parent.id
        nrg = OFFSPRING_ENERGY
        # Inherit knowledge from parents — fidelity ceiling set by the parent's best
        # available transmission channel (imitation/oral/written, see _transmission_fidelity)
        inherited_knowledge = {}
        parent_fidelity = _transmission_fidelity(parent) * random.uniform(0.85, 1.0)
        for kname, kdata in parent.known_knowledge.items():
            # Copy the full entry (preserving extra fields like crop_type/livestock archetype
            # that aren't part of the generic level/source/tick_learned shape) before overriding
            inherited_knowledge[kname] = {
                **kdata,
                'level': kdata['level'] * parent_fidelity,
                'source': f'inherited_from_{parent.name}',
                'tick_learned': tick,
            }
        if partner and partner.known_knowledge:
            # Also inherit from partner, taking the best version
            partner_fidelity = _transmission_fidelity(partner) * random.uniform(0.85, 1.0)
            for kname, kdata in partner.known_knowledge.items():
                if kname in inherited_knowledge:
                    # Take the better version
                    if kdata['level'] > inherited_knowledge[kname]['level']:
                        inherited_knowledge[kname] = {
                            **kdata,
                            'level': kdata['level'] * partner_fidelity,
                            'source': f'inherited_from_{partner.name}',
                            'tick_learned': tick,
                        }
                else:
                    inherited_knowledge[kname] = {
                        **kdata,
                        'level': kdata['level'] * partner_fidelity,
                        'source': f'inherited_from_{partner.name}',
                        'tick_learned': tick,
                    }
    else:
        while True:
            x, y = random.randint(0, GRID_W-1), random.randint(0, GRID_H-1)
            if grid[y][x].passable():
                break
        traits = Traits.random()
        gen, pid = 0, None
        nrg = random.uniform(1950, 2700)
        inherited_knowledge = {}

    child = Resident(rid, _rand_name(), x, y, 0, nrg, MAX_HEALTH, traits,
                    True, pid, gen, [], {}, tick)
    child.known_knowledge = inherited_knowledge
    cap = child.knowledge_capacity()
    if len(child.known_knowledge) > cap:
        # A newborn's own long-term knowledge capacity ('disk') caps what can be
        # retained from parents — keep the strongest-held domains rather than letting
        # inheritance bypass the cap that governs everyone else.
        kept = sorted(child.known_knowledge.items(), key=lambda kv: kv[1].get('level', 0), reverse=True)[:cap]
        child.known_knowledge = dict(kept)
    child.skills = {kname: kdata['level'] * 100 for kname, kdata in child.known_knowledge.items()}
    return child


# ── Perception ──

def _nearby_cells(x, y, r, grid):
    cells = []
    for dy in range(-r, r+1):
        for dx in range(-r, r+1):
            nx, ny = x+dx, y+dy
            if 0 <= nx < GRID_W and 0 <= ny < GRID_H and abs(dx)+abs(dy) <= r:
                cells.append((grid[ny][nx], abs(dx)+abs(dy)))
    return cells


def _nearby_residents(x, y, r, residents):
    return [(res, abs(res.x-x)+abs(res.y-y))
            for res in residents
            if res.alive and 0 < abs(res.x-x)+abs(res.y-y) <= r]


# ── Fast-Tier Decision ──

def _best_food(cells):
    best, score = None, -1
    for c, d in cells:
        if not c.passable() or d == 0:
            continue
        s = c.biomass / max(1, d)
        if s > score:
            score, best = s, c
    return best


def _step_toward(rx, ry, tx, ty, grid):
    dx = max(-1, min(1, tx - rx))
    dy = max(-1, min(1, ty - ry))
    nx, ny = rx + dx, ry + dy
    if 0 <= nx < GRID_W and 0 <= ny < GRID_H and grid[ny][nx].passable():
        return ('move', nx, ny, None)
    return ('rest', None, None, None)


def decide(r, grid, residents, tick, pressure=0.0):
    radius = r.view_radius()
    cells = _nearby_cells(r.x, r.y, radius, grid)
    near_res = _nearby_residents(r.x, r.y, radius, residents)
    here = grid[r.y][r.x]

    season = SEASONS[(tick // SEASON_LENGTH) % 4]

    # SCAVENGE: Pick up leftover food if hungry (highest priority when available)
    if r.energy < 1500 and here.leftover > 3:
        return ('scavenge', None, None, None)

    # DESPERATE: raid nearby cells for leftover food (no killing needed)
    if r.energy < 750 and here.biomass < 2 and here.leftover < 2:
        # Look for nearby cells with leftovers
        cells = _nearby_cells(r.x, r.y, 2, grid)
        leftover_cells = [(c, d) for c, d in cells if c.leftover > 5 and d > 0]
        if leftover_cells:
            target_cell = max(leftover_cells, key=lambda x: x[0].leftover)[0]
            return _step_toward(r.x, r.y, target_cell.x, target_cell.y, grid)

    # RAID: attack someone for energy as last resort — a Malthusian release valve.
    # Under moderate pressure, targeting is biased toward strangers (resource seizure
    # from outsiders); only under extreme pressure does that bias fade, representing
    # conflict breaking out even within one's own established relationships once
    # scarcity is severe enough (RFC-0007: no engine-authored Group/War object, this is
    # purely individual-level targeting bias using the existing bond system).
    raid_base = 0.3 + r.traits.risk_tolerance * 0.5
    if pressure > 1.2 and r.traits.sociability < 0.5:
        raid_base += 0.25 * (pressure - 1.2)

    if r.energy < 540 and here.biomass < 3 and here.leftover < 2:
        adjacent = [(res, d) for res, d in near_res if d <= 1 and res.energy > 900]
        if adjacent and random.random() < raid_base:
            # Hamilton's rule: prefer raiding strangers over genetic relatives
            # Compute relatedness via parent_id — siblings share a parent, parent-child share
            def relatedness(a, b):
                if a.parent_id is None or b.parent_id is None:
                    return 0.0
                if a.parent_id == b.id or b.parent_id == a.id:
                    return 0.5  # parent-child
                return 0.5 if a.parent_id == b.parent_id else 0.0  # full siblings
            strangers = [(res, d) for res, d in adjacent
                         if (res.id not in r.bonds or r.bonds[res.id].quality <= 0)
                         and relatedness(r, res) < 0.25]
            # Below extreme pressure, prefer seizing from strangers over one's own
            # established relationships or kin; only true crisis (pressure >= 2.0) erodes that
            # Raise pressure threshold for raiding relatives (kin discount per Hamilton's rule)
            pool = strangers if (strangers and pressure < 1.5) else adjacent
            if pool is adjacent:
                # Even among all adjacent, prefer lower-relatedness targets when pressure is moderate
                pool.sort(key=lambda x: relatedness(r, x[0]))
            target = max(pool, key=lambda x: x[0].energy)[0]
            return ('raid', None, None, target.id)

    # MIGRATE (winter): move to a warmer zone when the cold itself is the acute threat
    if r.energy < 900 and season == 'winter' and climate_zone(r.y) != 'tropical':
        if r.y > 52:  # Already in tropical
            pass
        elif r.y > 26:  # In temperate, move toward tropical
            target_y = min(r.y + 2, 79)
            return ('move', r.x, target_y, None)
        else:  # In cold, move toward temperate
            target_y = min(r.y + 3, 79)
            return ('move', r.x, target_y, None)

    # MIGRATE (general): under sustained high population pressure — regardless of season
    # or zone — spread out toward less-crowded, better-resourced ground rather than
    # compete for the same depleted local patch. This is expansion into unclaimed
    # territory as a release valve, not a scripted settlement mechanic: the resident
    # simply moves toward the best food it can see within a wider search radius.
    if pressure > 1.3 and r.energy < 1650 and random.random() < 0.20:
        wide_cells = _nearby_cells(r.x, r.y, radius + 4, grid)
        far_candidates = [(c, d) for c, d in wide_cells if d > radius and c.biomass > 15]
        if far_candidates:
            target_cell = max(far_candidates, key=lambda x: x[0].biomass)[0]
            return _step_toward(r.x, r.y, target_cell.x, target_cell.y, grid)

    # CRITICAL / HUNGRY: find food
    if r.energy < 1200:
        if here.biomass > 3:
            return ('forage', None, None, None)
        best = _best_food(cells)
        if best:
            return _step_toward(r.x, r.y, best.x, best.y, grid)
        return _random_move(r, grid)

    # INJURED: rest
    if r.health < 50 and r.energy > 600:
        return ('rest', None, None, None)

    # REPRODUCE — fertility drops under Malthusian pressure; additionally, chronic malnutrition
    # (measured by malnutrition_debt) directly suppresses individual fecundity even when energy
    # is momentarily sufficient, reflecting real physiological depletion from past caloric stress.
    if r.energy > REPRODUCTION_ENERGY and r.age > REPRODUCTION_AGE:
        fertility = max(0.0, 1.0 - (pressure - 1.0) * 0.5)
        # Malnutrition debt reduces fertility: a resident at full debt (100.0) has fertility halved
        # Additionally, if malnutrition debt exceeds a critical threshold, reproduction is impossible
        if r.malnutrition_debt > 60.0:
            fertility = 0.0
        else:
            fertility *= max(0.5, 1.0 - (r.malnutrition_debt / NUTRITION_DEBT_CAP) * 0.5)
        if random.random() < fertility:
            partners = [(res, d) for res, d in near_res
                        if res.energy > REPRODUCTION_ENERGY and res.age > REPRODUCTION_AGE]
            if partners:
                p = min(partners, key=lambda x: x[1])[0]
                if abs(p.x - r.x) + abs(p.y - r.y) <= 1:
                    return ('reproduce', None, None, p.id)
                return _step_toward(r.x, r.y, p.x, p.y, grid)

    # SOCIAL
    if r.traits.sociability > 0.5 and near_res and pressure > 1.0 and random.random() < 0.5:
        t = random.choice(near_res)[0]
        if abs(t.x - r.x) + abs(t.y - r.y) <= 1:
            return ('interact', None, None, t.id)

    # FORAGE if not full
    if r.energy < 2400 and here.biomass > 10:
        return ('forage', None, None, None)

    # EXPLORE
    return _explore(r, cells, grid)


def _explore(r, cells, grid):
    known = {(m.x, m.y) for m in r.memory}
    cands = []
    for c, d in cells:
        if not c.passable() or d == 0:
            continue
        s = c.biomass_cap
        if (c.x, c.y) not in known:
            s *= 2
        cands.append((c, s))
    if cands:
        total = sum(s for _, s in cands)
        if total > 0:
            pick = random.random() * total
            cum = 0
            for c, s in cands:
                cum += s
                if cum >= pick:
                    return _step_toward(r.x, r.y, c.x, c.y, grid)
    return ('rest', None, None, None)


def _random_move(r, grid):
    dirs = [(0,1),(0,-1),(1,0),(-1,0)]
    random.shuffle(dirs)
    for dx, dy in dirs:
        nx, ny = r.x+dx, r.y+dy
        if 0 <= nx < GRID_W and 0 <= ny < GRID_H and grid[ny][nx].passable():
            return ('move', nx, ny, None)
    return ('rest', None, None, None)


# ── Physics Resolution ──

def _do_move(r, tx, ty, grid):
    if tx is None:
        return None
    if not (0 <= tx < GRID_W and 0 <= ty < GRID_H):
        return None
    cell = grid[ty][tx]
    if not cell.passable():
        return None
    cost = TERRAIN[cell.terrain]['move'] / r.traits.speed * 30.0  # kcal per movement action
    if r.energy >= cost:
        r.energy -= cost
        r.x, r.y = tx, ty
        # Terrain hazard — injury risk in harsh terrain
        hazard = TERRAIN_HAZARD.get(cell.terrain, 0)
        if hazard and random.random() < hazard / r.traits.endurance:
            dmg = random.uniform(HAZARD_DMG_MIN, HAZARD_DMG_MAX)
            r.health -= dmg
            return f'{r.name} was injured crossing {cell.terrain} (-{dmg:.0f}hp)'
    return None


def _do_forage(r, grid, tick, residents=None):
    cell = grid[r.y][r.x]
    if cell.biomass <= 0 and cell.leftover <= 0:
        return None

    zone_cfg = CLIMATE_ZONES[cell.climate]
    discovery_msg = None

    # Domestication — Experiment pathway (RFC-0006): repeated work on suitable land
    # occasionally yields the insight that planting/herding beats pure extraction.
    # Suitability is a physical fact of terrain x zone, not a scripted unlock.
    farm_suit = TERRAIN_FARMING.get(cell.terrain, 0) * zone_cfg['farming_suitability']
    graze_suit = TERRAIN_GRAZING.get(cell.terrain, 0) * zone_cfg['grazing_suitability']

    # Trying a wild variant is one roll; whether it actually becomes a stable domesticate
    # is a second, independent roll (DOMESTICATION_SUCCESS_CHANCE) — most experiments with
    # a promising wild plant/animal don't pan out, matching real domestication's high
    # attrition rate. A failed attempt leaves no trace; the per-tick discovery roll keeps
    # trying on subsequent ticks regardless.
    if farm_suit > 0 and 'crop_cultivation' not in r.known_knowledge:
        if random.random() < DOMESTICATION_DISCOVERY_CHANCE * farm_suit:
            if random.random() < DOMESTICATION_SUCCESS_CHANCE:
                crop_type = _pick_archetype(CROP_ARCHETYPES, cell.climate)
                _learn_knowledge(r, 'crop_cultivation', {
                    'level': 0.15, 'source': 'experimented_with_planting', 'tick_learned': tick,
                    'crop_type': crop_type,
                })
                discovery_msg = f'{r.name} domesticated a {crop_type} crop'
    if graze_suit > 0 and 'animal_husbandry' not in r.known_knowledge:
        if random.random() < DOMESTICATION_DISCOVERY_CHANCE * graze_suit:
            if random.random() < DOMESTICATION_SUCCESS_CHANCE:
                livestock_type = _pick_archetype(LIVESTOCK_ARCHETYPES, cell.climate)
                _learn_knowledge(r, 'animal_husbandry', {
                    'level': 0.15, 'source': 'experimented_with_herding', 'tick_learned': tick,
                    'crop_type': livestock_type,
                })
                discovery_msg = f'{r.name} domesticated {livestock_type} livestock'

    # Agricultural technology ladder — irrigation, selective breeding, fertilizer/pesticides.
    # Each is an independent Experiment-pathway discovery gated on a real prerequisite:
    # irrigation needs water-adjacent land, breeding needs deep personal mastery (many
    # seasons of practice), fertilizer needs writing (systematic record-keeping across
    # seasons/generations is what makes agricultural science possible at all).
    if (cell.water and 'crop_cultivation' in r.known_knowledge and 'irrigation' not in r.known_knowledge
            and random.random() < IRRIGATION_DISCOVERY_CHANCE):
        _learn_knowledge(r, 'irrigation', {
            'level': 0.2, 'source': 'water_management_experience', 'tick_learned': tick
        })
        discovery_msg = f'{r.name} developed irrigation'
    if (r.skills.get('crop_cultivation', 0) >= BREEDING_SKILL_THRESHOLD
            and 'selective_breeding' not in r.known_knowledge
            and random.random() < BREEDING_DISCOVERY_CHANCE):
        _learn_knowledge(r, 'selective_breeding', {
            'level': 0.2, 'source': 'generations_of_seed_selection', 'tick_learned': tick
        })
        discovery_msg = f'{r.name} began selectively breeding higher-yield crops'
    if ('writing' in r.known_knowledge and 'selective_breeding' in r.known_knowledge
            and 'fertilizer' not in r.known_knowledge
            and random.random() < FERTILIZER_DISCOVERY_CHANCE):
        _learn_knowledge(r, 'fertilizer', {
            'level': 0.2, 'source': 'systematic_agricultural_science', 'tick_learned': tick
        })
        discovery_msg = f'{r.name} developed fertilizer and pest control'

    # A cell's energy-density ceiling ratchets up to the best agricultural technology any
    # farmer/herder working it has achieved, and never decreases — the technique embedded
    # in how a plot is worked doesn't un-happen even if the land itself later lapses.
    if farm_suit > 0 or graze_suit > 0:
        cell.ag_tech_mult = max(cell.ag_tech_mult, _ag_tech_mult(r))

    # Tending the land — knowledge-holders raise the cell's cultivation level through
    # sustained work; skill itself deepens gradually through practice (learning by doing)
    if farm_suit > 0 and 'crop_cultivation' in r.known_knowledge:
        skill = r.skills.get('crop_cultivation', 0) / 100.0
        cell.cultivation = min(1.0, cell.cultivation + CULTIVATION_GAIN_RATE * skill * farm_suit)
        if random.random() < 0.03:
            _reinforce_knowledge(r, 'crop_cultivation', 0.02)
    if graze_suit > 0 and 'animal_husbandry' in r.known_knowledge:
        skill = r.skills.get('animal_husbandry', 0) / 100.0
        cell.cultivation = min(1.0, cell.cultivation + CULTIVATION_GAIN_RATE * skill * graze_suit)
        if random.random() < 0.03:
            _reinforce_knowledge(r, 'animal_husbandry', 0.02)

    # Learning by doing for the higher agricultural tiers — same reinforcement pattern
    for tier_skill in ('irrigation', 'selective_breeding', 'fertilizer'):
        if tier_skill in r.known_knowledge and random.random() < 0.025:
            _reinforce_knowledge(r, tier_skill, 0.02)

    # Harvest from biomass
    if cell.biomass > 0:
        harvest = min(cell.biomass, 15 * r.traits.strength) * random.uniform(0.5, 1.0)
        effort = 15.0 / r.traits.endurance  # caloric cost of the labor itself
        cell.biomass -= harvest

        # Domestication conversion efficiency — better technique extracts more usable energy
        # from the same harvested biomass (does not exceed what was actually taken from the land)
        # Base conversion is kcal yielded per unit of biomass harvested. Calibrated so a
        # resident foraging normally sits comfortably above the 2000 kcal erosion threshold
        # (i.e. "well-fed" is the achievable norm, not a rare surplus state) — dipping into
        # the erosion/death bands should reflect genuine scarcity (winter, overpopulation),
        # not routine operation.
        conversion = 38.0
        if farm_suit > 0 and 'crop_cultivation' in r.known_knowledge:
            conversion += r.skills.get('crop_cultivation', 0) / 100.0 * farm_suit * 20.0
        if graze_suit > 0 and 'animal_husbandry' in r.known_knowledge:
            conversion += r.skills.get('animal_husbandry', 0) / 100.0 * graze_suit * 20.0
        gain = harvest * conversion
        r.energy = min(MAX_ENERGY, r.energy + gain - effort)
        r.food_total += harvest

        # Leave some food behind (emergent storage)
        # Storage skill increases how much food is retained
        base_retention = random.uniform(0.1, 0.3)
        storage_skill = r.skills.get('food_storage', 0) / 100.0
        retention = min(0.55, base_retention + storage_skill * 0.25)
        leftover_amount = harvest * retention
        cell.leftover += leftover_amount

    # Resource conflict — competition over scarce food
    if residents and cell.biomass < 15:
        rivals = [o for o in residents if o.alive and o.id != r.id
                  and o.x == r.x and o.y == r.y and o.energy < 1050]
        if rivals and random.random() < CONFLICT_CHANCE:
            rival = random.choice(rivals)
            r_power = r.traits.strength * random.uniform(0.7, 1.3)
            o_power = rival.traits.strength * random.uniform(0.7, 1.3)
            loser = r if r_power < o_power else rival
            dmg = random.uniform(CONFLICT_DMG_MIN, CONFLICT_DMG_MAX)
            loser.health -= dmg
            return f'{r.name} fought {rival.name} over food — {loser.name} injured (-{dmg:.0f}hp)'

    if discovery_msg:
        return discovery_msg
    if cell.biomass > 12 or (cell.leftover > 0 and r.energy < MAX_ENERGY):
        return f'{r.name} gathered food (leftover: {cell.leftover:.0f})'
    return None


def _do_scavenge(r, grid):
    """Scavenge leftovers left by previous foragers"""
    cell = grid[r.y][r.x]
    if cell.leftover <= 0:
        return None

    # leftover is denominated in biomass units, like cell.biomass — convert to kcal at
    # the same base rate used when the biomass was originally foraged (see _do_forage)
    biomass_taken = min(cell.leftover * 0.7, (MAX_ENERGY - r.energy) / 38.0)
    scavenged_kcal = biomass_taken * 38.0
    cell.leftover -= biomass_taken
    r.energy = min(MAX_ENERGY, r.energy + scavenged_kcal)

    return f'{r.name} scavenged {scavenged_kcal:.0f} kcal from leftovers'


def _maybe_discover_language(r, target, tick, pressure, cooperative=False):
    """Spoken language discovery — Experiment pathway. Requires cooperation payoff,
    repeated game, and coordination pressure together (see constants above); an actual
    cooperative act (food sharing) is the strongest signal and gets a chance bonus over
    passive contact."""
    if 'spoken_language' not in r.known_knowledge and random.random() < LANGUAGE_DISCOVERY_CHANCE:
        return None
    if len(r.bonds) < LANGUAGE_GROUP_SIZE:
        return None
    bond = r.bonds[target.id]
    if bond.quality < LANGUAGE_BOND_THRESHOLD or bond.interactions < LANGUAGE_REPEAT_THRESHOLD:
        return None
    if pressure < LANGUAGE_PRESSURE_THRESHOLD * 0.8:
        return None
    chance = LANGUAGE_DISCOVERY_CHANCE * (1 + (pressure - 1) * 0.5) * (LANGUAGE_COOPERATION_BONUS if cooperative else 1.0)
    if random.random() < chance:
        origin = 'during_cooperation' if cooperative else 'through_repeated_contact'
        _learn_knowledge(r, 'spoken_language', {
            'level': 0.3, 'source': f'coined_with_{target.name}_{origin}', 'tick_learned': tick
        })
        return f'{r.name} and {target.name} coined shared words — spoken language emerges'
    return None


def _do_interact(r, target_id, residents, tick, pressure=0.0):
    target = None
    for res in residents:
        if res.id == target_id and res.alive:
            target = res
            break
    if not target:
        return None

    event_msg = None
    if r.id not in [b.rid for b in r.bonds.values()]:
        pass
    if target.id not in r.bonds:
        r.bonds[target.id] = Bond(target.id, 0.0, tick)
        event_msg = f'{r.name} met {target.name}'
    if r.id not in target.bonds:
        target.bonds[r.id] = Bond(r.id, 0.0, tick)

    r.bonds[target.id].last_tick = tick
    target.bonds[r.id].last_tick = tick
    r.bonds[target.id].interactions += 1
    target.bonds[r.id].interactions += 1

    # Share food if one is hungry — this is the highest-signal cooperative act available:
    # a real payoff exchanged between two individuals, not just proximity or small talk.
    if r.energy > 1800 and target.energy < 900 and r.traits.sociability > 0.4:
        share = min(450, r.energy - 1500)
        r.energy -= share
        target.energy = min(MAX_ENERGY, target.energy + share * 0.9)
        r.bonds[target.id].quality = min(1.0, r.bonds[target.id].quality + 0.2)
        target.bonds[r.id].quality = min(1.0, target.bonds[r.id].quality + 0.3)
        lang_msg = _maybe_discover_language(r, target, tick, pressure, cooperative=True)
        return lang_msg or f'{r.name} shared food with {target.name}'

    # Exchange spatial memory (with distortion per RFC-0001 Law 6)
    r.bonds[target.id].quality = min(1.0, r.bonds[target.id].quality + 0.1)
    if r.memory and random.random() < 0.5:
        mem = random.choice(r.memory)
        distorted = MemEntry(mem.x, mem.y, mem.biomass * random.uniform(0.7, 1.3), tick)
        target.memory.append(distorted)
        cap = target.brain_capacity()
        if len(target.memory) > cap:
            target.memory.sort(key=lambda m: m.tick, reverse=True)
            target.memory = target.memory[:cap]

    # Spoken language discovery — weaker signal here than the cooperative-sharing path
    # above (general contact, not an exchanged payoff), see _maybe_discover_language.
    lang_msg = _maybe_discover_language(r, target, tick, pressure, cooperative=False)
    if lang_msg:
        event_msg = lang_msg

    # Knowledge transmission — fidelity ceiling set by the speaker's best available
    # channel (imitation/oral/written); actual fidelity also scales with how well the
    # speaker themselves knows the specific knowledge being passed on.
    # Probability increases with: sociability + age (longer survival = more credibility)
    age_bonus = min(0.3, r.age / 100.0)  # Older people transmit better
    transmission_prob = (r.traits.sociability * 0.4) + age_bonus

    # Teaching and learning both cost energy — a speaker/listener too calorie-poor to
    # afford it simply cannot transmit or absorb knowledge this tick, regardless of how
    # willing either is. This is what makes "too poor in energy to learn" a real
    # constraint rather than only a probability modifier.
    can_teach = r.energy > TEACHING_ENERGY_COST
    can_learn = target.energy > LEARNING_ENERGY_COST
    if r.known_knowledge and can_teach and can_learn and random.random() < transmission_prob:
        # Pick a random knowledge the speaker has
        knowledge_name = random.choice(list(r.known_knowledge.keys()))
        speaker_knowledge = r.known_knowledge[knowledge_name]
        channel_fidelity = _transmission_fidelity(r)
        listener_learning_mult = 0.5 + target.usable_intelligence()

        # Listener learns with distortion/loss proportional to quality gap
        if knowledge_name not in target.known_knowledge:
            # First time hearing about this knowledge — capped by the speaker's channel,
            # scaled down if the speaker's own grasp of it is still shallow, scaled up if
            # the listener's own usable intelligence (IQ throttled by their energy) is high
            fidelity = channel_fidelity * (0.5 + speaker_knowledge['level'] * 0.5)
            learned_level = min(1.0, speaker_knowledge['level'] * fidelity * listener_learning_mult)
            _learn_knowledge(target, knowledge_name, {
                **speaker_knowledge,
                'level': learned_level,
                'source': f'learned_from_{r.name}',
                'tick_learned': tick,
            })
            if not event_msg:
                event_msg = f'{r.name} taught {target.name} about {knowledge_name}'
        else:
            # Reinforce existing knowledge (only if speaker knows better)
            existing_level = target.known_knowledge[knowledge_name]['level']
            if speaker_knowledge['level'] > existing_level:
                improvement = (speaker_knowledge['level'] - existing_level) * channel_fidelity * 0.2 * listener_learning_mult
                target.known_knowledge[knowledge_name]['level'] = min(1.0, existing_level + improvement)
                target.skills[knowledge_name] = target.known_knowledge[knowledge_name]['level'] * 100

        r.energy -= TEACHING_ENERGY_COST
        target.energy -= LEARNING_ENERGY_COST

        # Learning by doing: successfully communicating deepens the speaker's own
        # language/writing fluency, same reinforcement pattern as other practiced skills
        for meta_skill in ('spoken_language', 'writing'):
            if meta_skill in r.known_knowledge and random.random() < 0.04:
                _reinforce_knowledge(r, meta_skill, 0.03)

    return event_msg


def _do_reproduce(r, target_id, residents, grid, tick, next_id):
    target = None
    for res in residents:
        if res.id == target_id and res.alive:
            target = res
            break
    if not target:
        return None, next_id
    if r.energy < REPRODUCTION_COST or target.energy < REPRODUCTION_COST:
        return None, next_id
    if abs(r.x - target.x) + abs(r.y - target.y) > 1:
        return None, next_id

    r.energy -= REPRODUCTION_COST
    target.energy -= REPRODUCTION_COST
    r.children += 1
    target.children += 1

    next_id += 1
    child = _spawn(next_id, grid, tick, parent=r, partner=target)
    residents.append(child)
    return f'{child.name} born to {r.name} & {target.name} (gen {child.generation})', next_id


def _do_raid(r, target_id, residents, tick):
    target = None
    for res in residents:
        if res.id == target_id and res.alive:
            target = res
            break
    if not target or abs(r.x - target.x) + abs(r.y - target.y) > 1:
        return None

    r_power = r.traits.strength * random.uniform(0.6, 1.4)
    t_power = target.traits.strength * random.uniform(0.6, 1.4)

    if r_power > t_power:
        stolen = min(target.energy * 0.4, 600)
        target.energy -= stolen
        r.energy = min(MAX_ENERGY, r.energy + stolen * 0.8)
        target.health -= random.uniform(5, 18)
        if target.id in r.bonds:
            r.bonds[target.id].quality = max(-1, r.bonds[target.id].quality - 0.5)
        if r.id in target.bonds:
            target.bonds[r.id].quality = max(-1, target.bonds[r.id].quality - 0.5)
        return f'{r.name} raided {target.name} — stole {stolen:.0f} food'
    else:
        r.health -= random.uniform(10, 28)
        if r.id in target.bonds:
            target.bonds[r.id].quality = max(-1, target.bonds[r.id].quality - 0.5)
        return f'{r.name} tried to raid {target.name} — defeated (-{28:.0f}hp)'


# ── Main Simulation ──

class Simulation:
    def __init__(self, seed=None):
        self.seed = seed or random.randint(0, 999999)
        random.seed(self.seed)
        self.grid = generate_world(self.seed)
        self.residents: list[Resident] = []
        self.tick_count = 0
        self.events: list[dict] = []
        self.all_events: list[dict] = []
        self.metrics_history: list[dict] = []
        self.running = False
        self.speed = 5
        self.total_births = 0
        self.total_deaths = 0
        self.lock = threading.Lock()
        self._next_id = 0

        self.ai = AIEngine()

        for _ in range(INITIAL_POPULATION):
            self._next_id += 1
            self.residents.append(_spawn(self._next_id, self.grid, 0))

    def tick(self):
        with self.lock:
            self._tick()

    def _tick(self):
        self.tick_count += 1
        tick = self.tick_count
        evts = []

        season = SEASONS[(tick // SEASON_LENGTH) % 4]

        # Environment: biomass regrowth (zone-dependent season multiplier, cultivated land
        # regrows faster — scaled further by whatever agricultural technology tier that
        # specific plot has ratcheted up to: crop/livestock archetype, irrigation,
        # selective breeding, fertilizer)
        for row in self.grid:
            for c in row:
                m = c.season_mult(season)
                if c.biomass < c.biomass_cap:
                    cultivation_bonus = 1.0 + c.cultivation * CULTIVATION_MAX_BONUS * c.ag_tech_mult
                    c.biomass = min(c.biomass_cap, c.biomass + TERRAIN[c.terrain]['regrow'] * m * cultivation_bonus)
                # Untended land slowly reverts to wild (Law 10 Entropy) — cultivation LEVEL
                # lapses, but ag_tech_mult (the technique itself) does not un-happen
                if c.cultivation > 0:
                    c.cultivation = max(0.0, c.cultivation - CULTIVATION_DECAY)
                # Leftover food decays (rots, eaten by scavengers, stolen by non-residents)
                if c.leftover > 0:
                    c.leftover = max(0.0, c.leftover - c.leftover * 0.05 * m)

        living = [r for r in self.residents if r.alive]
        random.shuffle(living)

        # Carrying capacity based on annual average food production per zone
        # (cultivated land raises the effective ceiling, same as it raises regrowth)
        total_regrow = 0
        for row in self.grid:
            for c in row:
                if c.passable():
                    zone_cfg = CLIMATE_ZONES[c.climate]
                    avg_m = sum(zone_cfg[s] for s in SEASONS) / 4
                    cultivation_bonus = 1.0 + c.cultivation * CULTIVATION_MAX_BONUS * c.ag_tech_mult
                    total_regrow += TERRAIN[c.terrain]['regrow'] * avg_m * cultivation_bonus
        # total_regrow is in biomass units; convert to kcal at the same base rate used when
        # biomass is actually foraged (see _do_forage) before comparing against per-person
        # daily kcal need, so this ratio stays dimensionally consistent with the energy model
        carrying_cap = max(10, (total_regrow * 38.0) / (BASELINE_ENERGY_COST * 8.0))
        pop = len(living)
        self._pressure = pop / max(1, carrying_cap)

        def _nearby_fn(r):
            return _nearby_residents(r.x, r.y, r.view_radius(), self.residents)

        self.ai.process_tick(self.residents, self.grid, _nearby_fn, tick)

        # Pre-compute crowd density per cell for disease calculation
        cell_pop = {}
        for r in living:
            cell_pop[(r.x, r.y)] = cell_pop.get((r.x, r.y), 0) + 1

        # Epidemic — distinct from the ordinary background disease roll below: a rarer,
        # far more severe event that ignites when local crowding crosses a threshold and
        # sweeps through everyone nearby at once, rather than rolling independently per
        # resident per tick. Mortality is modulated by each resident's heritable immunity
        # trait, so an outbreak leaves behind a population enriched for natural resistance
        # — the survivors are not chosen, they are the ones whose inherited immunity trait
        # happened to be high enough, and they pass that trait to their offspring.
        # Density is measured within a small radius (residents rarely share an exact cell
        # in an open map, but do cluster within a few cells of each other).
        best_density, hotspot_cell = 0, None
        for (cx, cy), _ in cell_pop.items():
            local_density = sum(c for (ox, oy), c in cell_pop.items() if abs(ox - cx) + abs(oy - cy) <= 2)
            if local_density > best_density:
                best_density, hotspot_cell = local_density, (cx, cy)
        if best_density >= EPIDEMIC_DENSITY_THRESHOLD and random.random() < EPIDEMIC_IGNITION_CHANCE:
            hx, hy = hotspot_cell
            affected = [r for r in living if abs(r.x - hx) + abs(r.y - hy) <= EPIDEMIC_RADIUS]
            deaths_from_epidemic = 0
            for r in affected:
                mortality_p = EPIDEMIC_BASE_MORTALITY * (1.0 - r.traits.immunity)
                if random.random() < mortality_p:
                    r.health -= EPIDEMIC_DMG
                    deaths_from_epidemic += 1
            evts.append({'tick': tick, 'type': 'epidemic',
                         'text': f'A disease outbreak sweeps a crowded area — {len(affected)} exposed, '
                                 f'{deaths_from_epidemic} gravely stricken',
                         'x': hx, 'y': hy})

        for r in living:
            if not r.alive:
                continue
            r.age += 1

            # Daily calorie ledger: one tick is one day (see the Energy Model comment at
            # the top of this file), so gross spend/intake this tick is exactly the daily
            # figures the sandbox/dashboard can show per resident. This is a primary-cost
            # approximation, not an exhaustive accounting: it captures upkeep plus whatever
            # single action this resident takes (foraging gain, movement/reproduction/raid
            # cost), but not being fed by someone else's action later in this same tick.
            r.energy_intake_today = 0.0
            r.energy_spent_today = 0.0
            _energy_before_upkeep = r.energy

            # Upkeep — one tick's day-night caloric burn, shaped by season, zone, and
            # whichever cold-mitigation technologies this resident knows. Day and night
            # loss are computed separately (see DAY_LOSS_FACTOR/NIGHT_LOSS_FACTOR) so fire
            # can target nighttime loss specifically while shelter blunts both uniformly.
            zone_cfg = CLIMATE_ZONES[climate_zone(r.y)]
            season_upkeep = zone_cfg[f'{season}_upkeep']
            storage_skill = r.skills.get('food_storage', 0) / 100.0
            clothing_skill = r.skills.get('clothing_making', 0) / 100.0
            shelter_skill = r.skills.get('shelter_building', 0) / 100.0
            fire_skill = r.skills.get('fire_making', 0) / 100.0

            effective_season_upkeep = season_upkeep * (1.0 - shelter_skill * SHELTER_UPKEEP_REDUCTION)
            day_mult = effective_season_upkeep * DAY_LOSS_FACTOR
            night_mult = effective_season_upkeep * NIGHT_LOSS_FACTOR * (1.0 - fire_skill * FIRE_NIGHT_REDUCTION)
            daily_mult = (day_mult + night_mult) / 2.0

            cost = r.upkeep() * daily_mult
            # Stored food and insulating clothing both reduce personal metabolic burn further
            cost *= (1.0 - storage_skill * 0.3) * (1.0 - clothing_skill * CLOTHING_UPKEEP_REDUCTION)
            r.energy -= cost
            if r.energy < 0:
                r.energy = 0
            r.energy_spent_today += _energy_before_upkeep - r.energy

            # Population pressure multiplier — mild below capacity, brutal above
            pressure_mult = max(1.0, self._pressure ** 2)

            # Malnutrition — everyone suffers when resources are overstretched
            if self._pressure > 1.0:
                malnutrition = 5.0 * (self._pressure - 1.0) ** 2
                r.health -= malnutrition
                if random.random() < (self._pressure - 1.0) * 0.1:
                    r.health -= random.uniform(10, 30)  # additional mortality risk due to overcrowding

            # Caloric health erosion — health erodes as a direct, graduated consequence of
            # the caloric reserve dropping through two real thresholds (3000 kcal baseline,
            # erosion below 2000, severe below 1500). There is no separate "cold damage":
            # cold works entirely through the upkeep multiplier above, which drives the
            # reserve down into these bands faster in harsh zones/seasons.
            in_crisis = r.energy < CALORIE_DEATH_ZONE
            recovering = r.energy > CALORIE_EROSION_THRESHOLD
            if r.energy < CALORIE_EROSION_THRESHOLD:
                deficit = (CALORIE_EROSION_THRESHOLD - r.energy) / CALORIE_EROSION_THRESHOLD
                r.health -= HEALTH_EROSION_RATE * deficit * pressure_mult
            if in_crisis:
                severe_deficit = (CALORIE_DEATH_ZONE - r.energy) / CALORIE_DEATH_ZONE
                r.health -= DEATH_ZONE_RATE * severe_deficit * pressure_mult

            # Winter: caloric crisis drives knowledge discovery and reinforcement — the
            # same physical state (severe caloric deficit) that food storage, shelter,
            # clothing, and fire all independently address, each in a different way.
            if season == 'winter':
                # Starvation discovery: residents in caloric crisis may learn from painful
                # experience, only if they don't already know
                if in_crisis and 'food_storage' not in r.known_knowledge:
                    if random.random() < 0.08:
                        _learn_knowledge(r, 'food_storage', {
                            'level': 0.2,
                            'source': 'desperate_winter_experience',
                            'tick_learned': tick
                        })
                        evts.append({'tick': tick, 'type': 'discovery',
                                     'text': f'{r.name} learned food storage through winter hardship',
                                     'x': r.x, 'y': r.y})
                elif recovering and 'food_storage' in r.known_knowledge and random.random() < 0.06:
                    _reinforce_knowledge(r, 'food_storage', 0.08)

                # Shelter discovery — Experiment pathway: repeated caloric crisis motivates
                # building windbreaks/shelter. Colder zones and seasons push residents into
                # crisis far more often, so shelter naturally emerges first where it matters.
                if (in_crisis and 'shelter_building' not in r.known_knowledge
                        and random.random() < SHELTER_DISCOVERY_CHANCE):
                    _learn_knowledge(r, 'shelter_building', {
                        'level': 0.2, 'source': 'caloric_crisis_experience', 'tick_learned': tick
                    })
                    evts.append({'tick': tick, 'type': 'discovery',
                                 'text': f'{r.name} learned to build shelter against the cold',
                                 'x': r.x, 'y': r.y})
                elif (recovering and 'shelter_building' in r.known_knowledge
                        and random.random() < 0.05):
                    _reinforce_knowledge(r, 'shelter_building', 0.04)

                # Clothing discovery — same Experiment pathway, independent invention from
                # shelter (a resident may find one, the other, or both over time)
                if (in_crisis and 'clothing_making' not in r.known_knowledge
                        and random.random() < CLOTHING_DISCOVERY_CHANCE):
                    _learn_knowledge(r, 'clothing_making', {
                        'level': 0.2, 'source': 'caloric_crisis_experience', 'tick_learned': tick
                    })
                    evts.append({'tick': tick, 'type': 'discovery',
                                 'text': f'{r.name} learned to make warm clothing',
                                 'x': r.x, 'y': r.y})
                elif (recovering and 'clothing_making' in r.known_knowledge
                        and random.random() < 0.05):
                    _reinforce_knowledge(r, 'clothing_making', 0.04)

                # Fire discovery — same Experiment pathway; effect specifically targets the
                # amplified nighttime loss (see upkeep above), distinguishing it from
                # shelter (blunts exposure generally) and clothing (personal insulation)
                if (in_crisis and 'fire_making' not in r.known_knowledge
                        and random.random() < FIRE_DISCOVERY_CHANCE):
                    _learn_knowledge(r, 'fire_making', {
                        'level': 0.2, 'source': 'caloric_crisis_experience', 'tick_learned': tick
                    })
                    evts.append({'tick': tick, 'type': 'discovery',
                                 'text': f'{r.name} learned to keep fire through the night',
                                 'x': r.x, 'y': r.y})
                elif (recovering and 'fire_making' in r.known_knowledge
                        and random.random() < 0.05):
                    _reinforce_knowledge(r, 'fire_making', 0.04)

            # Writing discovery — Experiment pathway: a resident who already has spoken
            # language, belongs to a larger organized group, is genuinely at their personal
            # long-term knowledge capacity ('disk', see Resident.knowledge_capacity — the
            # real memory deficit, not an arbitrary domain count), has energy surplus, and
            # whose society is pressing at or beyond its subsistence ceiling occasionally
            # devises a symbolic record to externalize what oral tradition alone keeps losing.
            if ('spoken_language' in r.known_knowledge and 'writing' not in r.known_knowledge
                    and len(r.known_knowledge) >= min(WRITING_COMPLEXITY_THRESHOLD, r.knowledge_capacity())
                    and len(r.bonds) >= WRITING_GROUP_SIZE
                    and r.energy > WRITING_ENERGY_THRESHOLD
                    and self._pressure > WRITING_PRESSURE_THRESHOLD):
                if random.random() < WRITING_DISCOVERY_CHANCE:
                    _learn_knowledge(r, 'writing', {
                        'level': 0.25,
                        'source': 'devised_symbolic_record',
                        'tick_learned': tick
                    })
                    evts.append({'tick': tick, 'type': 'discovery',
                                 'text': f'{r.name} devised a system of writing',
                                 'x': r.x, 'y': r.y})

            # Disease — base chance + crowding + pressure
            crowd = cell_pop.get((r.x, r.y), 1) - 1
            disease_p = (DISEASE_BASE_CHANCE + DISEASE_CROWD_BONUS * crowd) * pressure_mult
            if r.health < 40:
                disease_p *= 1.5
            if random.random() < disease_p:
                dmg = random.uniform(DISEASE_DMG_MIN, DISEASE_DMG_MAX)
                r.health -= dmg
                if dmg > 18:
                    evts.append({'tick': tick, 'type': 'disease',
                                 'text': f'{r.name} fell seriously ill',
                                 'x': r.x, 'y': r.y})

            # Infant mortality — the young are fragile
            if r.age < INFANT_AGE and random.random() < INFANT_MORTALITY_CHANCE:
                r.health -= random.uniform(8, 20)

            # Random accidents
            if random.random() < ACCIDENT_CHANCE * pressure_mult:
                dmg = random.uniform(ACCIDENT_DMG_MIN, ACCIDENT_DMG_MAX)
                r.health -= dmg

            # Nutritional history — irregular or insufficient food intake accumulates as
            # long-term stress, independent of momentary starvation damage above. A resident
            # who is chronically hungry (energy below threshold) builds up debt; one who is
            # reliably well-fed slowly recovers from past deficits. This is what makes
            # "feast or famine" foraging shorten lifespans even without acute starvation deaths.
            if r.energy < NUTRITION_STRESS_ENERGY:
                r.malnutrition_debt = min(NUTRITION_DEBT_CAP, r.malnutrition_debt + NUTRITION_DEBT_RATE)
            elif r.energy > NUTRITION_RECOVERY_ENERGY:
                r.malnutrition_debt = max(0.0, r.malnutrition_debt - NUTRITION_RECOVERY_RATE)

            # Age decline — onset and severity depend on nutritional history, not just raw
            # age. A well-fed resident's decline curve stretches toward MAX_AGE; a chronically
            # malnourished one (e.g. a pre-agriculture forager living hand-to-mouth) starts
            # declining sharply in their 30s regardless of chronological age remaining.
            if r.age > AGE_DECLINE_ONSET:
                base_progress = (r.age - AGE_DECLINE_ONSET) / AGE_DECLINE_SPAN
                nutrition_penalty = (r.malnutrition_debt / NUTRITION_DEBT_CAP) * 0.8
                p = min(0.5, (base_progress + nutrition_penalty) * 0.10)
                if random.random() < p:
                    r.health -= 5

            # Death check
            if r.health <= 0 or r.age > MAX_AGE:
                if r.age > MAX_AGE:
                    cause = 'old_age'
                elif r.energy <= 0:
                    cause = 'starvation'
                elif r.age < INFANT_AGE:
                    cause = 'infant_death'
                else:
                    cause = 'disease'
                r.alive = False
                r.death_tick = tick
                r.death_cause = cause
                self.total_deaths += 1
                evts.append({'tick': tick, 'type': 'death',
                             'text': f'{r.name} died ({cause}, age {r.age}, gen {r.generation})',
                             'x': r.x, 'y': r.y})
                continue

            # Memory decay
            if r.memory and random.random() < 0.02:
                r.memory.pop(random.randint(0, len(r.memory) - 1))

            # Slow tier override or fast tier decision
            ai_action, ai_text = self.ai.get_override(r.id)
            if ai_action:
                action, tx, ty, tid = ai_action
                evts.append({'tick': tick, 'type': 'ai',
                             'text': f'[AI] {r.name}: {ai_text[:80] if ai_text else "decided"}',
                             'x': r.x, 'y': r.y})
            else:
                action, tx, ty, tid = decide(r, self.grid, self.residents, tick, self._pressure)

            msg = None
            _energy_before_action = r.energy
            if action == 'move':
                msg = _do_move(r, tx, ty, self.grid)
            elif action == 'forage':
                msg = _do_forage(r, self.grid, tick, self.residents)
            elif action == 'rest':
                r.health = min(MAX_HEALTH, r.health + 2.5 * r.traits.endurance)
            elif action == 'interact':
                msg = _do_interact(r, tid, self.residents, tick, self._pressure)
            elif action == 'raid':
                msg = _do_raid(r, tid, self.residents, tick)
            elif action == 'scavenge':
                msg = _do_scavenge(r, self.grid)
            elif action == 'reproduce':
                msg, self._next_id = _do_reproduce(r, tid, self.residents, self.grid, tick, self._next_id)

            _action_delta = r.energy - _energy_before_action
            if _action_delta >= 0:
                r.energy_intake_today += _action_delta
            else:
                r.energy_spent_today += -_action_delta

            if msg:
                evt_type = 'discovery' if msg.startswith(f'{r.name} discovered') else action
                evts.append({'tick': tick, 'type': evt_type, 'text': msg, 'x': r.x, 'y': r.y})

            # Update spatial memory
            cell = self.grid[r.y][r.x]
            found = False
            for me in r.memory:
                if me.x == cell.x and me.y == cell.y:
                    me.biomass, me.tick = cell.biomass, tick
                    found = True
                    break
            if not found:
                r.memory.append(MemEntry(cell.x, cell.y, cell.biomass, tick))
                cap = r.brain_capacity()
                if len(r.memory) > cap:
                    r.memory.sort(key=lambda m: m.tick, reverse=True)
                    r.memory = r.memory[:cap]

        # Metrics
        living = [r for r in self.residents if r.alive]
        n = len(living)
        births = sum(1 for e in evts if e['type'] == 'reproduce')
        deaths = sum(1 for e in evts if e['type'] == 'death')
        self.total_births += births

        gini = 0.0
        if n > 1:
            es = sorted(r.energy for r in living)
            s = sum(es)
            if s > 0:
                gini = sum((2*i - n + 1) * e for i, e in enumerate(es)) / (n * s)

        # Clustering: avg number of residents within radius 2
        cluster = 0.0
        if n > 0:
            for r in living:
                cluster += sum(1 for r2 in living if r2.id != r.id
                               and abs(r2.x - r.x) + abs(r2.y - r.y) <= 2)
            cluster /= n

        # Knowledge statistics
        storage_holders = sum(1 for r in living if 'food_storage' in r.known_knowledge)
        avg_storage_skill = 0.0
        if storage_holders > 0:
            avg_storage_skill = sum(r.skills.get('food_storage', 0) for r in living if 'food_storage' in r.known_knowledge) / storage_holders

        farmer_holders = sum(1 for r in living if 'crop_cultivation' in r.known_knowledge)
        herder_holders = sum(1 for r in living if 'animal_husbandry' in r.known_knowledge)
        avg_farm_skill = 0.0
        if farmer_holders > 0:
            avg_farm_skill = sum(r.skills.get('crop_cultivation', 0) for r in living if 'crop_cultivation' in r.known_knowledge) / farmer_holders
        avg_herd_skill = 0.0
        if herder_holders > 0:
            avg_herd_skill = sum(r.skills.get('animal_husbandry', 0) for r in living if 'animal_husbandry' in r.known_knowledge) / herder_holders

        cultivated_cells = sum(1 for row in self.grid for c in row if c.cultivation > 0.05)

        language_holders = sum(1 for r in living if 'spoken_language' in r.known_knowledge)
        writing_holders = sum(1 for r in living if 'writing' in r.known_knowledge)
        shelter_holders = sum(1 for r in living if 'shelter_building' in r.known_knowledge)
        clothing_holders = sum(1 for r in living if 'clothing_making' in r.known_knowledge)
        fire_holders = sum(1 for r in living if 'fire_making' in r.known_knowledge)

        irrigation_holders = sum(1 for r in living if 'irrigation' in r.known_knowledge)
        breeding_holders = sum(1 for r in living if 'selective_breeding' in r.known_knowledge)
        fertilizer_holders = sum(1 for r in living if 'fertilizer' in r.known_knowledge)
        crop_type_counts: dict[str, int] = {}
        for r in living:
            ct = r.known_knowledge.get('crop_cultivation', {}).get('crop_type')
            if ct:
                crop_type_counts[ct] = crop_type_counts.get(ct, 0) + 1
        livestock_type_counts: dict[str, int] = {}
        for r in living:
            lt = r.known_knowledge.get('animal_husbandry', {}).get('crop_type')
            if lt:
                livestock_type_counts[lt] = livestock_type_counts.get(lt, 0) + 1
        avg_ag_tech_mult = round(sum(c.ag_tech_mult for row in self.grid for c in row) / (GRID_W * GRID_H), 3)

        metrics = {
            'tick': tick,
            'season': season,
            'year': tick // (SEASON_LENGTH * 4),
            'pop': n,
            'avg_energy': round(sum(r.energy for r in living) / max(1, n), 1),
            'avg_health': round(sum(r.health for r in living) / max(1, n), 1),
            'births': births,
            'deaths': deaths,
            'total_births': self.total_births,
            'total_deaths': self.total_deaths,
            'avg_age': round(sum(r.age for r in living) / max(1, n)),
            'max_gen': max((r.generation for r in living), default=0),
            'gini': round(gini, 3),
            'cluster': round(cluster, 2),
            'pressure': round(getattr(self, '_pressure', 0), 2),
            'carrying_cap': round(carrying_cap),
            'knowledge_holders': storage_holders,  # People who know food storage
            'avg_storage_skill': round(avg_storage_skill, 1),
            'knowledge_ratio': round(storage_holders / max(1, n), 3),
            'farmer_holders': farmer_holders,
            'avg_farm_skill': round(avg_farm_skill, 1),
            'herder_holders': herder_holders,
            'avg_herd_skill': round(avg_herd_skill, 1),
            'cultivated_cells': cultivated_cells,
            'language_holders': language_holders,
            'writing_holders': writing_holders,
            'shelter_holders': shelter_holders,
            'clothing_holders': clothing_holders,
            'fire_holders': fire_holders,
            'avg_immunity': round(sum(r.traits.immunity for r in living) / max(1, n), 3),
            'irrigation_holders': irrigation_holders,
            'breeding_holders': breeding_holders,
            'fertilizer_holders': fertilizer_holders,
            'crop_types': crop_type_counts,
            'livestock_types': livestock_type_counts,
            'avg_ag_tech_mult': avg_ag_tech_mult,
            'avg_intelligence': round(sum(r.traits.intelligence for r in living) / max(1, n), 3),
            'avg_brain_capacity': round(sum(r.brain_capacity() for r in living) / max(1, n), 1),
            'avg_knowledge_capacity': round(sum(r.knowledge_capacity() for r in living) / max(1, n), 1),
            'avg_knowledge_domains': round(sum(len(r.known_knowledge) for r in living) / max(1, n), 2),
            'avg_energy_intake': round(sum(r.energy_intake_today for r in living) / max(1, n), 1),
            'avg_energy_spent': round(sum(r.energy_spent_today for r in living) / max(1, n), 1),
        }
        self.metrics_history.append(metrics)
        if len(self.metrics_history) > 5000:
            self.metrics_history = self.metrics_history[-5000:]

        self.events = evts
        self.all_events.extend(evts)
        if len(self.all_events) > 2000:
            self.all_events = self.all_events[-2000:]

    # ── Serialization ──

    def get_state(self):
        with self.lock:
            living = [r for r in self.residents if r.alive]
            terrain = []
            biomass = []
            leftover = []
            cultivation = []
            for row in self.grid:
                for c in row:
                    terrain.append(c.terrain)
                    biomass.append(round(c.biomass, 1))
                    leftover.append(round(c.leftover, 1))
                    cultivation.append(round(c.cultivation, 3))

            res_data = [{
                'id': r.id, 'name': r.name, 'x': r.x, 'y': r.y,
                'age': r.age, 'energy': round(r.energy, 1),
                'health': round(r.health, 1), 'gen': r.generation,
                'parent_id': r.parent_id,
                'str': round(r.traits.strength, 2),
                'spd': round(r.traits.speed, 2),
                'per': round(r.traits.perception, 2),
                'end': round(r.traits.endurance, 2),
                'soc': round(r.traits.sociability, 2),
                'risk': round(r.traits.risk_tolerance, 2),
                'iq': round(r.traits.intelligence, 2),
                'usable_iq': round(r.usable_intelligence(), 2),
                'brain_capacity': r.brain_capacity(),
                'knowledge_capacity': r.knowledge_capacity(),
                'energy_intake_today': round(r.energy_intake_today, 1),
                'energy_spent_today': round(r.energy_spent_today, 1),
                'bonds': len(r.bonds),
                'children': r.children,
                'skills': {k: round(v, 1) for k, v in r.skills.items()},
                'knowledge': {k: round(v.get('level', 0), 3) for k, v in r.known_knowledge.items()},
            } for r in living]

            m = self.metrics_history[-1] if self.metrics_history else {}
            zone_boundary = GRID_H // 3
            return {
                'gw': GRID_W, 'gh': GRID_H,
                'terrain': terrain, 'biomass': biomass, 'leftover': leftover, 'cultivation': cultivation,
                'residents': res_data,
                'metrics': m,
                'history': self.metrics_history[-300:],
                'events': self.all_events[-80:],
                'running': self.running, 'speed': self.speed,
                'seed': self.seed,
                'colors': {k: v['color'] for k, v in TERRAIN.items()},
                'ai': self.ai.get_stats(),
                'climate_zones': {
                    'boundary': zone_boundary,
                    'names': ['cold', 'temperate', 'tropical'],
                },
            }

    # ── Control ──

    def start(self):
        if self.running:
            return
        self.running = True
        threading.Thread(target=self._loop, daemon=True).start()

    def pause(self):
        self.running = False

    def set_speed(self, s):
        self.speed = max(1, min(50, s))

    def _loop(self):
        while self.running:
            self.tick()
            living = sum(1 for r in self.residents if r.alive)
            if living == 0:
                self.running = False
                break
            time.sleep(1.0 / self.speed)
