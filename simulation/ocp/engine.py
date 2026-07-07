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

GRID_W = 120
GRID_H = 80
# Founding population: seeded as multiple geographically-separated clusters, not one single
# origin point -- this is what actually guarantees genuinely unrelated lineages exist from
# tick 0, rather than hoping FISSION eventually creates them (verified via extensive live
# testing that emergent fission alone isn't fast/reliable enough to keep incest avoidance from
# collapsing the population -- see INCEST_AVOIDANCE_ENABLED below). Cluster centers are placed
# as far apart as GRID_W allows (near the map's two edges) since the average resident
# interaction radius (~45 cells, up to 65) is large relative to even the doubled map width --
# full isolation isn't achievable, but this maximizes the fraction of each cluster that starts
# out of interaction range of the other, per RFC-0011's "partial, porous isolation is enough"
# principle (total isolation is explicitly not required).
NUM_FOUNDING_CLUSTERS = 2
CLUSTER_POPULATION = 120  # per cluster (up from the old single-cluster INITIAL_POPULATION=55,
                           # then 70/cluster -- raised further per user request for a larger
                           # founding population, which also means more initial genetic
                           # diversity within each cluster before inbreeding load can accumulate)
INITIAL_POPULATION = NUM_FOUNDING_CLUSTERS * CLUSTER_POPULATION  # kept for anything reading a
                                                                    # total-population constant
CLUSTER_SPAWN_MARGIN = 15  # each cluster's founders spawn within its own center +/- this --
                             # tighter than the old single-cluster margin (30) so clusters stay
                             # spatially distinct from each other rather than spreading into
                             # the gap between them
MAX_AGE = 100  # theoretical ceiling; nutritional history determines who actually approaches it
REPRODUCTION_AGE = 13
STATE_CACHE_TTL = 0.4  # seconds; see Simulation.get_state — absorbs rapid/concurrent polling
# Founding population age stagger (see _spawn) -- founders start at a spread of ages (young
# adult through late-middle-age) rather than all at age 0, so their eventual old-age deaths
# spread across a wide window instead of colliding in one synchronized generational crash.
FOUNDING_AGE_MIN = 13
FOUNDING_AGE_MAX = 55

# ── Energy Model (kcal) ──
# `energy` is a resident's caloric reserve, modeled in real kilocalorie units so mortality
# thresholds are physically interpretable rather than an abstract 0-100 scale. A tick
# represents one full day-night cycle; each tick deducts one day's net caloric loss.
MAX_ENERGY = 3000.0             # full caloric reserve — "well-fed" baseline
REPRODUCTION_ENERGY = 1300.0    # lowered from 1800 (60% of max) -- live data showed only ~15%
                                  # of reproduction-age adults ever reached the old threshold,
                                  # making low reproduction ELIGIBILITY (not fertility rolls or
                                  # malnutrition) the dominant bottleneck on total births. Paired
                                  # with OFFSPRING_ENERGY_PARENT_SCALE below so a marginal
                                  # (barely-eligible) pairing still produces a viable but weaker
                                  # newborn, while well-fed parents produce a stronger one --
                                  # quality scales with real parental surplus instead of the
                                  # eligibility gate alone rationing who can reproduce at all.
# NOTE: an earlier, DIFFERENT experiment (a separately lower FEMALE_REPRODUCTION_ENERGY=1200,
# reverted) let low-energy females attempt reproduction more readily while REPRODUCTION_COST
# (750, deducted from BOTH parents) pushed them straight into malnutrition-crisis territory
# (below NUTRITION_STRESS_ENERGY=900) immediately after, making female mortality WORSE (avg
# death age dropped from 48 to ~27). This is different: FEMALE_REPRODUCTION_COST is now only
# 300 (not 750), so a female at the new lower REPRODUCTION_ENERGY=1300 threshold still keeps
# 1000 energy after paying it, above the malnutrition-stress line -- the earlier failure mode
# doesn't apply the same way here.
REPRODUCTION_COST = 750.0       # reserve spent per parent per birth
FEMALE_REPRODUCTION_COST = 300.0  # lowered further from 550 -- female energy income is
                                    # already reduced (FEMALE_FORAGE_MULT), so childbirth itself
                                    # shouldn't cost her the same flat amount as a male
OFFSPRING_ENERGY = 600.0        # newborn starting reserve -- baseline, at parents right at
                                  # REPRODUCTION_ENERGY threshold (see OFFSPRING_ENERGY_PARENT_SCALE)
OFFSPRING_ENERGY_PARENT_SCALE = 0.3  # fraction of parents' average post-birth energy surplus
                                       # (above REPRODUCTION_ENERGY) converted into extra newborn
                                       # starting energy -- well-fed parents produce a stronger
                                       # newborn, marginal (barely-eligible) parents still produce
                                       # a viable one at the OFFSPRING_ENERGY baseline
# Postpartum recovery (see Resident.last_birth_tick, _is_fertile) -- deliberately set to 0
# (no minimum spacing) per explicit strategy: while unclaimed land/energy is available, the
# population should be able to reproduce as fast as energy allows, front-loading total
# population size before the founding generation's synchronized old-age die-off (see the
# founding-cohort synchronized aging analysis) -- growth speed while resources are abundant
# matters more here than realistic birth spacing. Kept as a real mechanism (not deleted) in
# case a later phase wants to reintroduce spacing once the population is past this bootstrap
# window.
POSTPARTUM_RECOVERY_TICKS = 0
# Reproduction prefers an existing bond over the nearest stranger (see decide()'s REPRODUCE
# block) — this is what makes population structure into real kin-based groups.
REPRODUCTION_BOND_THRESHOLD = 0.1   # matches LANGUAGE_BOND_THRESHOLD's scale: a real if modest relationship
STRANGER_REPRODUCTION_CHANCE = 0.7  # reproducing with a totally unbonded stranger (exogamy) --
                                     # raised from an original 0.15 once incest avoidance (see
                                     # INCEST_AVOIDANCE_ENABLED below) made exogamy the ONLY
                                     # reproductive path for most individuals: with the marriage
                                     # mechanic (spouse_id) concentrating each couple's children
                                     # into full siblings of each other, nearby same-generation
                                     # candidates are almost always either full-siblings (blocked)
                                     # or true strangers (0.0) -- there is little middle ground of
                                     # half-siblings for the incest threshold to meaningfully
                                     # exempt. A low exogamy rate compounds with that already-thin
                                     # pool and collapses the population; real small societies
                                     # commonly rely on exogamy at high, sometimes near-mandatory,
                                     # rates for exactly this reason (village/clan exogamy norms).
# Incest avoidance (RFC-0011 Inbreeding and Mate Exclusion) — NOT a behavioral prohibition.
# Reproduction between kin is never blocked outright (a population must always be ABLE to
# reproduce, even when isolated) — instead, genetics does the limiting: offspring of related
# parents carry a real, cumulative, compounding cost (see inbreeding_load on Resident and
# Traits.blend) that degrades intelligence/immunity/endurance and shortens expected lifespan
# (see the age-decline penalty in Simulation._tick), while a genuine outcross with a low-load
# partner (fresh genetic diversity, e.g. from another founding cluster or a later fission
# splinter) produces offspring that are measurably BETTER than either parent's own lineage --
# hybrid vigor/heterosis, not just a return to baseline. This matches real population biology
# far better than a hard block: a hard block (tried earlier this session, at multiple
# thresholds) repeatedly caused severe population collapse in this simulation's small,
# still-dispersing population, because there is often no non-kin candidate within reach at all
# -- but real isolated populations do NOT go extinct from lack of unrelated partners, they
# persist at reduced quality (documented island/founder-population genetics) until diversity
# arrives. INCEST_AVOIDANCE_ENABLED is kept as a toggle for the hard-block CODE PATH (now
# unused/inert) in case a future scenario wants it back; the real mechanism is the load below.
INCEST_RELATEDNESS_THRESHOLD = 0.3
INCEST_AVOIDANCE_ENABLED = False
# Inbreeding load accumulation (see inbreeding_load on Resident) — how much a single generation
# of related mating adds to the COMPOUNDING load passed to the next generation (on top of the
# average of both parents' own loads, which is what naturally produces dilution/heterosis when
# one parent's load is much lower than the other's). This is deliberately a strong penalty
# ("增加惩罚" -- increase the penalty) so sustained within-lineage mating visibly degrades
# population quality within a few generations, not merely at the moment of a single close-kin
# pairing.
INBREEDING_LOAD_ACCUMULATION = 0.25
# Inbreeding depression (see Traits.blend) — scales the offspring's mutation variance up and
# applies a direct penalty to the most fitness-relevant traits (intelligence, immunity,
# endurance), scaled by the CHILD'S OWN inbreeding_load (the compounding, multi-generation
# metric), not just the immediate parents' one-off relatedness. First-pass values below were
# tuned down from an initial harsher pass that caused a fitness death-spiral (offspring too
# degraded to survive long enough for outcrossing to ever dilute the load) -- verify holder
# quality degrades visibly under sustained isolation without outright collapsing population.
INBREEDING_MUTATION_MULT = 2.0     # at load=0.25, mutation stddev is multiplied by
                                     # (1 + 0.25*2.0) = 1.5x -- more genetic instability, not a
                                     # directional "always worse" rule
INBREEDING_FITNESS_PENALTY = 0.35  # at load=0.25, intelligence/immunity/endurance are
                                     # multiplied by (1 - 0.25*0.35) = 0.91 -- a real but modest
                                     # fitness cost; at load=1.0 (sustained multi-generation
                                     # isolation) this reaches 0.65x, clearly degraded
INBREEDING_HEALTH_PENALTY = 0.25   # newborn starting health multiplier: at load=0.25, health is
                                     # 0.94x of MAX_HEALTH; models real inbreeding depression's
                                     # documented effect on birth/developmental health
INBREEDING_AGING_PENALTY = 0.25    # added to the age-decline probability alongside the existing
                                     # malnutrition penalty (see Simulation._tick) -- models
                                     # shortened expected lifespan from accumulated genetic load
# Sex-based division of labor (see _do_forage) — females retain a real, if reduced, foraging
# contribution rather than zero; see the note at the gain calculation for why zero failed.
FEMALE_FORAGE_MULT = 0.5
# Mate provisioning reliability (see decide()'s MATE PROVISIONING block and _do_interact) --
# live data showed females dying at roughly half the male lifespan (avg death age 48 vs 83),
# overwhelmingly from malnutrition-driven health decline, because a male's own 1800-energy
# trigger required him to be at essentially full reproductive-level surplus before ever sharing
# -- needlessly high, since the share formula's own floor already capped what he'd give away.
# Lowering both the trigger and the post-share floor lets males help with a more modest,
# realistic surplus rather than only when fully comfortable.
MATE_PROVISIONING_ENERGY_THRESHOLD = 1400.0   # was an implicit 1800
MATE_PROVISIONING_SHARE_FLOOR = 1000.0        # was an implicit 1500 (giver's post-share floor);
                                                # still above NUTRITION_STRESS_ENERGY (900) so
                                                # helping a mate doesn't itself trigger the
                                                # giver's own malnutrition stress
# Migration (see the MIGRATE (general) block in decide()) is a costly last resort, not a
# default response to hunger — it requires a real energy surplus to spend on the journey.
MIGRATION_ENERGY_SURPLUS_MIN = 1800.0  # 60% of max; deliberately at REPRODUCTION_ENERGY's level —
                                        # migrating is something a comfortable resident does, not a starving one
MIGRATION_CHANCE = 0.3                 # per qualifying tick, once local competition has already failed
# Fission (see FISSION block in decide()) -- band-level group splitting (Service 1962,
# "Primitive Social Organization"): bands fracture when low-status members, who have no
# following/investment to lose, peel off toward unclaimed territory once local competition
# (raiding, ordinary migration) has already failed. This is what lets the population actually
# diverge into multiple, geographically- and bond-graph-distinct clusters over time, instead of
# the single group MIGRATE(general)'s short local search radius always converges back toward.
FISSION_PRESSURE_THRESHOLD = 1.3   # a sibling response to MIGRATION under the same pressure
                                    # regime, not an easier-to-trigger escape valve
FISSION_ENERGY_SURPLUS_MIN = 1800.0  # a long journey needs real surplus, same logic as migration
FISSION_CHANCE = 0.05    # much rarer than MIGRATION_CHANCE -- most low-standing residents under
                          # pressure still try ordinary local migration/raiding first (those
                          # branches run first and return before this is reached); this only
                          # fires for the residual pressure even wide local search couldn't resolve
FISSION_MIN_DISTANCE = 25   # cells -- genuinely long-distance, several times MIGRATE(general)'s
                             # local radius+4 search, so it actually produces a second, spatially
                             # distinct cluster rather than a shifted version of the same one
FISSION_SEARCH_RADIUS = 8   # sample radius around a far-flung probe point (see
                             # _find_fission_target) -- cheap, independent of population size
BASELINE_ENERGY_COST = 60.0     # baseline daily metabolic burn before season/technology modifiers
# Carrying capacity ceiling (see Simulation._tick's carrying_cap calculation) -- raised so the
# founding generation and its descendants have enough headroom to coexist rather than the young
# generation's growth crowding directly against the aging founders for the same fixed-size
# resource pie (the founding-cohort synchronized die-off crashed a large fraction of total
# population precisely because total population was already pinned near the old, tighter cap).
CARRYING_CAPACITY_MULT = 1.6
PERCEPTION_BASE_RADIUS = 20
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
DISEASE_BASE_CHANCE = 0.0015  # lowered further from 0.003 (originally 0.005) -- live data
                                # showed 'disease' still the dominant death cause (80%+) even
                                # after the earlier reduction and immunity wiring, hitting all
                                # ages broadly (32% of disease deaths were under 30, before
                                # age-decline even applies) -- re-calibrated for population
                                # booms now regularly reaching 500+ (vs 200-300 when these
                                # constants were last tuned), where crowding compounds baseline risk
DISEASE_CROWD_BONUS = 0.005    # halved from 0.01, same re-calibration for higher population
DISEASE_DMG_MIN = 10
DISEASE_DMG_MAX = 35
DISEASE_LOW_HEALTH_MULT = 1.25  # lowered from 1.5 -- softens the low-health death-spiral
                                  # (once health<40, higher disease risk further lowers health,
                                  # raising risk again); still a real penalty, less self-reinforcing
# Immunity previously had NO effect on ordinary disease risk (only the separate, rarer Epidemic
# mechanic below used it), so high- and low-immunity residents faced identical everyday disease
# odds -- meaning inbreeding depression's penalty on immunity (see INBREEDING_FITNESS_PENALTY)
# had no real consequence for the dominant cause of death. immunity=0.5 (species mean, see
# TRAIT_MEANS) leaves risk at baseline; below/above the mean scales it up/down accordingly.
IMMUNITY_DISEASE_MULT = 2.0
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
# Female biological profile (see Resident.upkeep) — real women have a lower basal metabolic
# rate/energy requirement than men, not just reduced foraging output (FEMALE_FORAGE_MULT). This
# is what should make the sexes' NET energy balance (income - expense) comparable rather than
# uniformly worse for females: same reduced income, but also reduced baseline need, plus
# correspondingly lower nutrition-stress/recovery thresholds since less energy represents less
# real deficit for her. Combined with real human longevity data (women statistically outlive
# men in most populations), this is deliberately a distinct female profile, not a strict
# handicap: lower strength/energy budget, but lower need and better resilience per unit of
# energy -- this is what should let surviving females anchor a population over a longer horizon
# rather than being a uniformly weaker version of the male profile.
FEMALE_UPKEEP_MULT = 0.75          # 25% lower baseline metabolic burn
FEMALE_NUTRITION_THRESHOLD_MULT = 0.75  # her stress/recovery energy points scale down to match
FEMALE_MAX_AGE_BONUS = 15  # real human females statistically outlive males -- her effective
                            # ceiling (see MAX_AGE) and decline curve (see AGE_DECLINE_SPAN)
                            # both stretch by this many extra years
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

# River + island (see _carve_river, called at the end of generate_world) -- a deliberate
# large-scale geographic feature layered on top of the noise-based terrain bands, rather than
# left to noise alone. 'river' is already a sanctioned terrain class (RFC-0003); this just gives
# it real north-south continuity plus a large mid-channel island the river splits around.
RIVER_WIDTH = 2            # cells either side of center -- a real, crossable-but-costly channel
RIVER_WALK_STEP = 1        # gentle per-row wander, not a straight line
RIVER_CENTER_MARGIN = 0.2  # river center stays within [margin, 1-margin] * GRID_W, i.e. roughly
                            # central, never wandering off toward either map edge
ISLAND_RADIUS_X = 6
ISLAND_RADIUS_Y = 10
ISLAND_TERRAIN = 'plains'  # fertile, full-regrow, low move-cost -- a deliberately attractive
                            # mid-river settling spot (real river islands/floodplains are
                            # historically prized farmland)
BRIDGE_TERRAIN = 'plains'  # the single-row land crossing connecting the island to both
                            # mainlands (see _carve_river) -- same terrain as the island itself,
                            # just a narrow crossing, not a distinct terrain type

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
                  'grazing_suitability': 1.0, 'farming_suitability': 0.1, 'mining_suitability': 1.0},
    'temperate': {'spring': 1.4, 'summer': 1.0, 'autumn': 0.55, 'winter': 0.02,
                  'spring_upkeep': 0.9, 'summer_upkeep': 1.0, 'autumn_upkeep': 1.05, 'winter_upkeep': 1.8,
                  'grazing_suitability': 0.25, 'farming_suitability': 1.0, 'mining_suitability': 0.3},
    'tropical':  {'spring': 1.2, 'summer': 1.0, 'autumn': 0.75, 'winter': 0.05,
                  'spring_upkeep': 0.9, 'summer_upkeep': 1.05, 'autumn_upkeep': 1.0, 'winter_upkeep': 1.3,
                  'grazing_suitability': 0.0, 'farming_suitability': 0.0, 'mining_suitability': 0.0},
}

# Terrain suitability for domestication (physical property of the land, like biomass_cap)
# Cold zone pasture-grade terrain suits grazing; temperate arable terrain suits crop cultivation.
# Tropical zone's zone-level suitability above is 0, so terrain suitability never activates there.
TERRAIN_GRAZING = {'plains': 0.8, 'mountain': 1.0, 'desert': 0.3}
TERRAIN_FARMING = {'plains': 1.0, 'river': 0.7, 'forest': 0.2}
# Mining is cold-zone-dominant real geology (coal/iron/oil concentrate in specific rock
# formations, not arable land) — mountain terrain is the primary source, same physical-property
# pattern as grazing/farming suitability above.
TERRAIN_MINING = {'mountain': 1.0, 'desert': 0.4}

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
    'wheat':        {'energy_density_mult': 1.4,  'zone_weights': {'temperate': 3.0, 'tropical': 0.1, 'cold': 0.0}},
    'rice':         {'energy_density_mult': 1.3,  'zone_weights': {'temperate': 2.0, 'tropical': 0.2, 'cold': 0.0}},
    'soybean':      {'energy_density_mult': 1.15, 'zone_weights': {'temperate': 1.5, 'tropical': 0.1, 'cold': 0.0}},
    'fruit':        {'energy_density_mult': 1.0,  'zone_weights': {'tropical': 3.0, 'temperate': 0.2, 'cold': 0.0}},
    'sweet_potato': {'energy_density_mult': 0.55, 'zone_weights': {'cold': 1.0, 'temperate': 0.0, 'tropical': 0.0}},
    'corn':         {'energy_density_mult': 0.6,  'zone_weights': {'cold': 1.0, 'temperate': 0.0, 'tropical': 0.0}},
}
LIVESTOCK_ARCHETYPES = {
    'grazer': {'energy_density_mult': 1.1, 'zone_weights': {'cold': 3.0, 'temperate': 1.0, 'tropical': 0.3}},
    'browser': {'energy_density_mult': 0.95, 'zone_weights': {'tropical': 2.0, 'temperate': 1.0, 'cold': 0.2}},
}

# Mineral resources — non-food, tradeable/raidable goods rather than a caloric energy source.
# Cold-zone-dominant real geology (coal seams, iron-bearing rock, oil deposits concentrate in
# specific formations, not arable temperate/tropical land), discovered through the same
# Experiment pathway as crop/livestock domestication (see `mining` knowledge below).
MINERAL_ARCHETYPES = {
    'coal':     {'zone_weights': {'cold': 3.0, 'temperate': 0.3, 'tropical': 0.0}},
    'iron_ore': {'zone_weights': {'cold': 2.0, 'temperate': 0.4, 'tropical': 0.0}},
    'oil':      {'zone_weights': {'cold': 1.5, 'temperate': 0.2, 'tropical': 0.0}},
}
MINING_DISCOVERY_CHANCE = 0.0025  # per qualifying forage tick, same order as DOMESTICATION_DISCOVERY_CHANCE
MINING_YIELD_PER_TICK = 0.8       # base quantity added to a miner's stockpile per working tick
CROP_SURPLUS_CONVERSION = 0.02    # kcal-of-excess-harvest -> tradeable crop-resource units
RESOURCE_STOCKPILE_DECAY = 0.01   # per-tick fractional decay on held resources (spoilage/consumption by others)

# Trade — see _maybe_trade. Opportunistic, individual, probabilistic exchange during an
# ordinary interaction; not a scripted allocation or trade-route algorithm (RFC-0007 Non-Goals).
TRADE_CHANCE = 0.2               # per qualifying interaction
TRADE_SURPLUS_FLOOR = 2.0        # must hold at least this much of a good before considering a gift
TRADE_GIFT_FRACTION = 0.25       # fraction of the surplus given away per successful trade

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
# Chemical fertilizer and mechanized agriculture historically followed industrial inputs
# (steel, coal-powered machinery), not just written record-keeping — requiring the resident
# hold some minimum accumulated iron_ore or coal grounds "fertilizer needs the industrial
# revolution first" as a literal resource dependency rather than only a knowledge gate.
FERTILIZER_INDUSTRIAL_INPUT_MIN = 5.0

# ── Caloric Health Model ──
# Cold, hunger, and technology are unified through a single physical quantity: how many
# kcal a resident has in reserve. There is no separate "cold damage" formula — cold works
# entirely by raising caloric burn rate (below), and health only erodes as a direct,
# graduated consequence of the caloric reserve itself dropping through two real thresholds.
CALORIE_EROSION_THRESHOLD = 2000.0  # below this, health begins to erode (graduated) -- baseline
                                      # for age 40+ (see _calorie_thresholds); live data showed
                                      # 98% of the population chronically living below this
                                      # baseline once REPRODUCTION_ENERGY was lowered to 1300,
                                      # meaning nearly everyone was constantly eroding health
                                      # regardless of age -- the real fix is age/sex-dependent
                                      # tolerance, not a single fixed number for the whole population
CALORIE_DEATH_ZONE = 1500.0         # below this, erosion becomes severe -- baseline for age 40+
HEALTH_EROSION_RATE = 1.5           # health/tick at full deficit within the erosion band (2000->0)
DEATH_ZONE_RATE = 8.0               # additional health/tick at full deficit within the death band (1500->0)
# Age/sex-dependent caloric tolerance (see _calorie_thresholds) -- young adults (10-40) run
# leaner metabolically and tolerate a lower reserve before real erosion sets in; young females
# tolerate even less (consistent with FEMALE_UPKEEP_MULT/FEMALE_NUTRITION_THRESHOLD_MULT); past
# 40, metabolic resilience declines and the same energy level represents more real risk than it
# did at 25, so the threshold rises above baseline instead.
YOUNG_ADULT_AGE_MAX = 40
YOUNG_CALORIE_TOLERANCE_MULT = 0.75        # age 10-40, male
YOUNG_FEMALE_CALORIE_TOLERANCE_MULT = 0.6  # age 10-40, female -- lower than male
OLDER_CALORIE_TOLERANCE_MULT = 1.15        # age 40+, either sex

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

# Chief/priest standing (see Resident.chief_standing/priest_standing) -- first-pass thresholds,
# tune 1.5x up/down if resulting holder counts land outside a rough 1-10% of population target.
CHIEF_STANDING_THRESHOLD = 3000   # ~4 full mate-provisioning shares (up to 500 kcal each) given
                                    # away to a bonded partner over a lifetime, weighted up by a
                                    # real following -- reachable by a genuinely generous, well-
                                    # bonded adult, not by everyone
PRIEST_STANDING_THRESHOLD = 8      # ~8 successful first-time-teaching events, weighted up by
                                    # breadth of what they know -- a real, if modest, teaching
                                    # career, not a single lucky transmission


def _pick_archetype(archetypes, zone):
    """Weighted-random selection of a crop/livestock archetype for the given climate zone —
    which specific staple a population ends up with is a random outcome of what was
    available to experiment with locally, not a designed choice."""
    names = list(archetypes.keys())
    weights = [archetypes[n]['zone_weights'].get(zone, 0.1) for n in names]
    return random.choices(names, weights=weights, k=1)[0]


def _relatedness(a, b):
    """Kinship via mother_id/father_id (RFC-0011 dual-parent lineage) — parent-child and full
    siblings share both parents' contribution (Wright's coefficient of relationship, 0.5); half
    siblings share exactly one parent (0.25); everyone else 0. A single-parent graph (the old
    `parent_id`-only approximation) cannot distinguish full from half siblings or catch a
    parent-child pair from the non-calling side — this is why RFC-0011 requires dual-parent
    lineage. Used by raiding (Hamilton's rule stranger-preference), social/reproductive
    familiarity bias, AND incest avoidance (see decide()'s REPRODUCE block) — kin and existing
    bonds are what makes group-like clustering emerge without an authored Group object
    (RFC-0004 Group Behavior)."""
    if a.id == b.id:
        return 1.0
    a_parents = {p for p in (a.mother_id, a.father_id) if p is not None}
    b_parents = {p for p in (b.mother_id, b.father_id) if p is not None}
    if a.id in b_parents or b.id in a_parents:
        return 0.5  # parent-child
    shared = a_parents & b_parents
    if len(shared) >= 2:
        return 0.5   # full siblings — both parents shared
    if len(shared) == 1:
        return 0.25  # half siblings — exactly one parent shared
    return 0.0


def _is_fertile(r, tick):
    """Postpartum recovery gate (see POSTPARTUM_RECOVERY_TICKS) -- males have no birth-spacing
    constraint, only whoever actually bears the child does."""
    if r.sex != 'female' or r.last_birth_tick is None:
        return True
    return (tick - r.last_birth_tick) >= POSTPARTUM_RECOVERY_TICKS


def _reproduction_cost(r):
    """Sex-specific reproduction energy cost (see FEMALE_REPRODUCTION_COST) -- female energy
    income is already reduced (FEMALE_FORAGE_MULT), so childbirth itself shouldn't cost her the
    same flat amount as a male."""
    return FEMALE_REPRODUCTION_COST if r.sex == 'female' else REPRODUCTION_COST


def _calorie_thresholds(r):
    """Age/sex-dependent caloric erosion thresholds (see YOUNG_CALORIE_TOLERANCE_MULT etc.) --
    returns (erosion_threshold, death_zone) scaled for this resident's age/sex rather than a
    single fixed pair for the whole population."""
    if r.age <= YOUNG_ADULT_AGE_MAX:
        mult = YOUNG_FEMALE_CALORIE_TOLERANCE_MULT if r.sex == 'female' else YOUNG_CALORIE_TOLERANCE_MULT
    else:
        mult = OLDER_CALORIE_TOLERANCE_MULT
    return CALORIE_EROSION_THRESHOLD * mult, CALORIE_DEATH_ZONE * mult


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


def _transmission_fidelity(speaker, pressure=0.0):
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


# Regression to the mean (quantitative genetics: offspring trait = species_mean +
# heritability*(midparent - species_mean), since no single trait is fully determined by
# genetics alone) -- this is what keeps population trait averages fluctuating around the
# species baseline across generations rather than ratcheting monotonically weaker (from
# accumulated inbreeding depression, see INBREEDING_FITNESS_PENALTY) or stronger (from repeated
# lucky blends) without bound. A single inbred generation's damage doesn't automatically
# propagate forever once diluted by a later, unrelated pairing. Calibrated from a worked
# example: two UNRELATED parents at 0.4 and 0.5 immunity naively average to 0.45, but should
# regress to 0.48 -- solving mean + h*(midparent-mean) = 0.48 with mean=0.5 gives h = 0.4.
TRAIT_HERITABILITY = 0.4
TRAIT_MEANS = {  # species-typical baseline per trait -- the midpoint of Traits.random()'s range
    'strength': 1.0, 'speed': 1.0, 'perception': 1.0, 'endurance': 1.0,
    'sociability': 0.5, 'risk_tolerance': 0.5, 'immunity': 0.5, 'intelligence': 1.0,
}


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

    def mutate(self, scale=1.0):
        def m(v, lo, hi):
            return max(lo, min(hi, v + random.gauss(0, TRAIT_MUTATION * scale)))
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

    def blend(self, other, inbreeding_load=0.0):
        """Blend two parents' traits (with regression to the mean, see TRAIT_HERITABILITY),
        then mutate — inbreeding_load (the CHILD's own compounding genetic load, see
        Resident.inbreeding_load, not just the immediate parents' one-off relatedness) scales
        the mutation variance up and applies a direct fitness penalty to intelligence/immunity/
        endurance (see INBREEDING_MUTATION_MULT/INBREEDING_FITNESS_PENALTY) ON TOP of the
        regressed value, modeling real inbreeding depression as a genetics-level cost rather
        than a behavioral prohibition (see RFC-0011 Inbreeding and Mate Exclusion)."""
        def regress(midparent, mean):
            return mean + TRAIT_HERITABILITY * (midparent - mean)
        blended = Traits(
            strength=regress((self.strength + other.strength) / 2, TRAIT_MEANS['strength']),
            speed=regress((self.speed + other.speed) / 2, TRAIT_MEANS['speed']),
            perception=regress((self.perception + other.perception) / 2, TRAIT_MEANS['perception']),
            endurance=regress((self.endurance + other.endurance) / 2, TRAIT_MEANS['endurance']),
            sociability=regress((self.sociability + other.sociability) / 2, TRAIT_MEANS['sociability']),
            risk_tolerance=regress((self.risk_tolerance + other.risk_tolerance) / 2, TRAIT_MEANS['risk_tolerance']),
            immunity=regress((self.immunity + other.immunity) / 2, TRAIT_MEANS['immunity']),
            intelligence=regress((self.intelligence + other.intelligence) / 2, TRAIT_MEANS['intelligence']),
        )
        if inbreeding_load > 0:
            fitness_mult = max(0.1, 1.0 - inbreeding_load * INBREEDING_FITNESS_PENALTY)
            blended.immunity *= fitness_mult
            blended.endurance *= fitness_mult
            blended.intelligence *= fitness_mult
        mutation_scale = 1.0 + inbreeding_load * INBREEDING_MUTATION_MULT
        return blended.mutate(mutation_scale)


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
    resources: dict = field(default_factory=lambda: {})  # resource_name (crop/mineral archetype) -> held quantity;
                                                            # physical goods distinct from energy/knowledge, tradeable
                                                            # or raidable (see CROP_ARCHETYPES, MINERAL_ARCHETYPES)
    sex: str = 'female'  # 'male' | 'female'; categorical, not blended like Traits — always set
                          # explicitly at spawn (see _spawn), this default is never actually used
    spouse_id: Optional[int] = None  # exclusive pair-bond, formed at first shared reproduction
                                       # (see _do_reproduce) — concentrates provisioning on one
                                       # partner rather than diffusing across every bonded female
                                       # (Lovejoy 1981 provisioning model of pair-bond evolution)
    malnutrition_debt: float = 0.0  # cumulative nutritional stress; drives aging independent of raw age
    energy_intake_today: float = 0.0  # gross kcal gained this tick (foraging, harvest, being fed)
    energy_spent_today: float = 0.0   # gross kcal spent this tick (upkeep + whatever action was taken)
    # RFC-0011 dual-parent lineage: `parent_id` above is kept as-is for backward compatibility
    # (still set to whichever resident called _do_reproduce), but real kinship analysis (incest
    # avoidance, sibling detection, see _relatedness) needs BOTH parents, distinguished by sex,
    # since a one-parent graph cannot tell full siblings from half siblings or detect a
    # parent-child pair from the non-calling side. Both None for the founding population.
    mother_id: Optional[int] = None
    father_id: Optional[int] = None
    # RFC-0011 protocol surface for future work: language and culture are NOT the same thing
    # as genetics/kinship and must stay separable (see RFC-0011 First Principle). These are
    # placeholders only -- no drift/divergence logic reads or writes them yet.
    spoken_language_id: Optional[str] = None  # future: dialect/language-cluster identity,
                                                # distinct from the boolean known_knowledge
                                                # 'spoken_language' entry (see RFC-0011 Language Drift)
    script_id: Optional[str] = None           # future: writing-system identity, since a
                                                # language and the script used to write it are
                                                # independent (RFC-0011 Writing Divergence)
    cultural_profile: dict = field(default_factory=lambda: {})  # future: transmissible, mutable
                                                                   # norms (marriage exclusivity,
                                                                   # inheritance bias, etc. -- see
                                                                   # RFC-0011 Culture Drift), distinct
                                                                   # from both genetics and language
    # Chief/priest standing (see chief_standing/priest_standing below) -- pure event counters,
    # not a capability grant (RFC-0007: detection, not design). energy_given_away tracks
    # Sahlins' Big Man model (1963): status through redistribution, not accumulation.
    # students_taught tracks Henrich & Gil-White's prestige model (2001): status accrues to
    # whoever others successfully learn from.
    energy_given_away: float = 0.0
    students_taught: int = 0
    last_birth_tick: Optional[int] = None  # postpartum recovery tracking (females only, see
                                             # POSTPARTUM_RECOVERY_TICKS) -- without this,
                                             # reproduction cadence was purely energy-gated,
                                             # measured live at an average ~17 ticks between a
                                             # mother's successive births with no real minimum
    # Cumulative inbreeding load (0.0 = fresh outside genetics, higher = generations of
    # within-lineage mating) -- NOT reset by an unrelated pairing, but DILUTED by one, since a
    # child's load is the average of both parents' plus whatever the immediate pairing itself
    # added (see _spawn). This is what lets population quality degrade gradually under sustained
    # isolation (real inbreeding depression compounding across generations) while a genuine
    # outcross with a low-load partner (fresh genetic diversity, e.g. from another founding
    # cluster) measurably improves the next generation -- hybrid vigor/heterosis, not just a
    # return to baseline. See INBREEDING_LOAD_ACCUMULATION and Traits.blend.
    inbreeding_load: float = 0.0

    def view_radius(self):
        return max(1, int((PERCEPTION_BASE_RADIUS + self.traits.sociability * 6 + 2) * self.traits.perception * 1.5) + 4 + int(self.traits.perception * 2)) + 2

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
        base = BASELINE_ENERGY_COST / self.traits.endurance + THINKING_ENERGY_COST * self.traits.intelligence
        return base * FEMALE_UPKEEP_MULT if self.sex == 'female' else base

    def chief_standing(self):
        """Big Man standing (Sahlins 1963): status through redistribution, scaled by a real
        following (bond count) -- pure readout over existing state, confers no capability of
        its own (RFC-0007: detection, not design)."""
        return self.energy_given_away * (1 + 0.1 * len(self.bonds))

    def priest_standing(self):
        """Prestige standing (Henrich & Gil-White 2001): status through successful cultural
        transmission, scaled by breadth of knowledge actually held (a teacher needs something
        to teach) -- pure readout, confers no capability of its own."""
        return self.students_taught * (1 + 0.15 * len(self.known_knowledge))

    def has_chief_standing(self):
        return self.chief_standing() >= CHIEF_STANDING_THRESHOLD and self.age > REPRODUCTION_AGE

    def has_priest_standing(self):
        return self.priest_standing() >= PRIEST_STANDING_THRESHOLD and self.age > REPRODUCTION_AGE


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
    _carve_river(grid)
    return grid


def _carve_river(grid):
    """Post-process pass: carves a wandering north-south river across the full y-range, with
    a large island in the middle that the river splits around. Runs after climate-banded
    terrain generation so it can freely override already-assigned cells -- river/lake are
    already RFC-0003-sanctioned terrain classes, this just gives the river deliberate
    large-scale continuity instead of only the scattered noise-based patches climate banding
    alone produces. The river MUST stay a single continuous obstacle splitting the map into two
    halves -- within the island's vertical span, RIVER_WIDTH (a single channel's width) is
    narrower than ISLAND_RADIUS_X (the island itself), so a naive single centered channel would
    simply vanish into the island rather than flow around it; instead the channel braids into
    two separate channels that flank the island's actual local half-width at each row, meeting
    back into one channel again above/below the island."""
    center_x = GRID_W // 2
    island_cy = GRID_H // 2
    lo = int(GRID_W * RIVER_CENTER_MARGIN)
    hi = int(GRID_W * (1 - RIVER_CENTER_MARGIN))
    river_props = TERRAIN['river']
    island_cx = center_x
    centers_by_y = {}
    for y in range(GRID_H):
        center_x += random.randint(-RIVER_WALK_STEP, RIVER_WALK_STEP)
        center_x = max(lo, min(hi, center_x))
        centers_by_y[y] = center_x
        if y == island_cy:
            island_cx = center_x  # capture the channel's position where the island actually
                                    # sits, not wherever the walk ends up by the last row

    def carve_channel(cx, y):
        for w in range(-RIVER_WIDTH, RIVER_WIDTH + 1):
            x = cx + w
            if not (0 <= x < GRID_W):
                continue
            cell = grid[y][x]
            cell.terrain = 'river'
            cell.water = river_props['water']
            cell.biomass_cap = river_props['cap']
            cell.biomass = river_props['cap'] * random.uniform(0.4, 0.9)

    for y in range(GRID_H):
        dy_frac = (y - island_cy) / max(1, ISLAND_RADIUS_Y)
        if abs(dy_frac) <= 1.0:
            # Braid around the island's actual footprint at this row (an ellipse's local
            # half-width shrinks toward 0 near its top/bottom, so the two branches naturally
            # converge back toward a single channel right at the island's vertical edges).
            island_half_width = ISLAND_RADIUS_X * math.sqrt(max(0.0, 1.0 - dy_frac * dy_frac))
            branch_offset = int(island_half_width) + RIVER_WIDTH + 1
            carve_channel(island_cx - branch_offset, y)
            carve_channel(island_cx + branch_offset, y)
        else:
            carve_channel(centers_by_y[y], y)
    island_props = TERRAIN[ISLAND_TERRAIN]
    for y in range(max(0, island_cy - ISLAND_RADIUS_Y), min(GRID_H, island_cy + ISLAND_RADIUS_Y + 1)):
        for x in range(GRID_W):
            dx_frac = (x - island_cx) / max(1, ISLAND_RADIUS_X)
            dy_frac = (y - island_cy) / max(1, ISLAND_RADIUS_Y)
            if dx_frac * dx_frac + dy_frac * dy_frac <= 1.0:
                cell = grid[y][x]
                cell.terrain = ISLAND_TERRAIN
                cell.water = island_props['water']
                cell.biomass_cap = island_props['cap']
                cell.biomass = island_props['cap'] * random.uniform(0.6, 0.95)  # fertile --
                                                                                  # bias high

    # Bridges — one single-row land crossing over each flanking channel (at the island's
    # vertical center, where the channels are furthest apart), connecting the island to both
    # mainlands. Deliberately only one row tall (not the whole channel's length), so a future
    # boat/river-travel mechanic can still pass through the channel freely at any other row —
    # this is a bridge, not a second dam.
    bridge_y = island_cy
    bridge_branch_offset = ISLAND_RADIUS_X + RIVER_WIDTH + 1  # matches the channel offset at
                                                                # dy_frac=0 in the braid above
    bridge_props = TERRAIN[BRIDGE_TERRAIN]
    for cx in (island_cx - bridge_branch_offset, island_cx + bridge_branch_offset):
        for w in range(-RIVER_WIDTH, RIVER_WIDTH + 1):
            x = cx + w
            if not (0 <= x < GRID_W):
                continue
            cell = grid[bridge_y][x]
            cell.terrain = BRIDGE_TERRAIN
            cell.water = bridge_props['water']
            cell.biomass_cap = bridge_props['cap']
            cell.biomass = bridge_props['cap'] * random.uniform(0.4, 0.7)


def _rand_name():
    return ''.join(random.choice(SYLLABLES) for _ in range(random.randint(2, 3))).capitalize()


def _spawn(rid, grid, tick, parent=None, partner=None, spawn_center_x=None):
    if parent:
        x, y = parent.x, parent.y
        # Inbreeding load (see Resident.inbreeding_load) compounds across generations: the
        # child's load is the average of both parents' own accumulated load, plus whatever
        # this specific pairing's relatedness adds on top -- this is what lets an outcross with
        # a low-load partner (fresh diversity) dilute/improve on a high-load lineage (heterosis),
        # rather than every within-cluster pairing resetting to the same fixed penalty.
        if partner:
            child_inbreeding_load = ((parent.inbreeding_load + partner.inbreeding_load) / 2
                                       + _relatedness(parent, partner) * INBREEDING_LOAD_ACCUMULATION)
            traits = parent.traits.blend(partner.traits, child_inbreeding_load)
        else:
            child_inbreeding_load = parent.inbreeding_load
            traits = parent.traits.mutate()
        gen = parent.generation + 1
        pid = parent.id
        # Newborn starting energy scales with real parental surplus (see
        # OFFSPRING_ENERGY_PARENT_SCALE) -- a marginal, barely-eligible pairing still produces a
        # viable newborn at the OFFSPRING_ENERGY baseline, but well-fed parents produce a
        # stronger one, rather than every birth costing the same eligibility floor being the
        # only thing separating who can reproduce from who can't.
        if partner:
            avg_parent_energy = (parent.energy + partner.energy) / 2
        else:
            avg_parent_energy = parent.energy
        energy_surplus = max(0.0, avg_parent_energy - REPRODUCTION_ENERGY)
        nrg = OFFSPRING_ENERGY + energy_surplus * OFFSPRING_ENERGY_PARENT_SCALE
        # RFC-0011 dual-parent lineage: distinguish mother/father by sex, not by which resident
        # happened to call _do_reproduce -- kinship analysis (incest avoidance, sibling
        # detection, see _relatedness) needs this distinction regardless of calling order.
        if partner:
            mother_id = parent.id if parent.sex == 'female' else partner.id
            father_id = parent.id if parent.sex == 'male' else partner.id
        else:
            mother_id = parent.id if parent.sex == 'female' else None
            father_id = parent.id if parent.sex == 'male' else None
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
        # RFC-0011 Phase 1: high-order culture (spoken language, writing) MUST NOT be inherited
        # at birth like a biological trait -- a newborn starts without them and acquires them
        # the same way its parents originally did, through real social exposure after birth
        # (see _maybe_discover_language and the generic teaching mechanism in _do_interact), not
        # as a free birthright. Practical/technical skills (farming, fire-making, etc.) stay
        # inheritable at reduced fidelity as before -- only these two domains are excluded.
        for cultural_domain in ('spoken_language', 'writing'):
            inherited_knowledge.pop(cultural_domain, None)
    else:
        # Founding population spawns within a bounded x-band around its own cluster center
        # (see NUM_FOUNDING_CLUSTERS/CLUSTER_SPAWN_MARGIN and Simulation.__init__, which calls
        # this once per cluster with a different spawn_center_x) rather than across the whole
        # map -- each cluster needs to start as one coherent, bondable group, geographically
        # separated from the other clusters (real, independent lineages from tick 0, rather
        # than hoping later dispersal creates them).
        cx = spawn_center_x if spawn_center_x is not None else GRID_W // 2
        lo_x = max(0, cx - CLUSTER_SPAWN_MARGIN)
        hi_x = min(GRID_W - 1, cx + CLUSTER_SPAWN_MARGIN)
        while True:
            x, y = random.randint(lo_x, hi_x), random.randint(0, GRID_H-1)
            if grid[y][x].passable():
                break
        traits = Traits.random()
        gen, pid = 0, None
        mother_id, father_id = None, None
        child_inbreeding_load = 0.0
        nrg = random.uniform(1950, 2700)
        inherited_knowledge = {}

    # Inbreeding depression's effect on birth/developmental health (see
    # INBREEDING_HEALTH_PENALTY) -- a newborn's starting health is reduced proportional to its
    # own compounding genetic load, on top of the trait-level penalties already applied in
    # Traits.blend.
    birth_health = MAX_HEALTH * max(0.1, 1.0 - child_inbreeding_load * INBREEDING_HEALTH_PENALTY)
    # Founding population age stagger (see FOUNDING_AGE_MIN/MAX) -- a real newborn always
    # starts at age 0, but seeding the founders themselves all at age 0 meant they all aged and
    # crossed into high age-decline-mortality territory in the same narrow tick window,
    # crashing the whole population in a single synchronized die-off no matter how much surplus
    # population or carrying capacity existed. A real founding group already includes people of
    # varied ages, not a single cohort of newborns -- spreading their ages spreads their
    # eventual deaths across a much wider window instead of one cliff.
    starting_age = random.randint(FOUNDING_AGE_MIN, FOUNDING_AGE_MAX) if not parent else 0
    child = Resident(rid, _rand_name(), x, y, starting_age, nrg, birth_health, traits,
                    True, pid, gen, [], {}, tick)
    child.mother_id = mother_id
    child.father_id = father_id
    child.inbreeding_load = child_inbreeding_load
    child.sex = random.choice(('male', 'female'))  # independent 50/50 each birth, not inherited
    if parent:
        # Parent-child (and, if present, partner) bonds are inherent from birth — a family
        # relationship doesn't need to be "discovered" through a chance social encounter the
        # way a stranger's does. Quality starts at a real, meaningful baseline (comparable to
        # a couple of successful cooperative acts), not zero; interactions start at 0 and grow
        # naturally as the child actually spends time with its parent(s) (see decide()'s SOCIAL
        # familiarity bias, which already treats kin as "familiar" targets).
        child.bonds[parent.id] = Bond(parent.id, 0.3, tick)
        parent.bonds[child.id] = Bond(child.id, 0.3, tick)
        if partner:
            child.bonds[partner.id] = Bond(partner.id, 0.3, tick)
            partner.bonds[child.id] = Bond(child.id, 0.3, tick)
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


def _find_fission_target(r, grid):
    """Pick a far-away, viable relocation target for band fission (see FISSION in decide()) --
    cheap sampling, not a population-density scan (O(1) probes x O(radius^2) cell check each,
    independent of population size). Biases toward unclaimed high-biomass terrain: a handful of
    random long-distance probe points are sampled, then the best-biomass passable cell found
    near any of them wins -- no attempt to compute true population density at range, which
    would require an O(n) or worse scan over all residents; this mirrors the same locality-only
    perception model _nearby_cells already uses everywhere else."""
    best_cell, best_score = None, -1
    for _ in range(5):
        angle = random.uniform(0, 2 * math.pi)
        dist = random.uniform(FISSION_MIN_DISTANCE, FISSION_MIN_DISTANCE + 15)
        px = int(r.x + math.cos(angle) * dist)
        py = int(r.y + math.sin(angle) * dist)
        px = max(0, min(GRID_W - 1, px))
        py = max(0, min(GRID_H - 1, py))
        for c, d in _nearby_cells(px, py, FISSION_SEARCH_RADIUS, grid):
            if c.passable() and c.biomass_cap > best_score:
                best_cell, best_score = c, c.biomass_cap
    return best_cell


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
    radius = r.view_radius() + int(r.traits.sociability * 2)
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
    # Resource scarcity (holding none of any mineral at all) sharpens the raid incentive once
    # already at the hunger-driven trigger below — same Malthusian release-valve logic as
    # above, extended to named goods rather than only calories.
    if pressure > 1.0 and not any(m in r.resources for m in MINERAL_ARCHETYPES):
        raid_base += 0.15

    if r.energy < 540 and here.biomass < 3 and here.leftover < 2:
        adjacent = [(res, d) for res, d in near_res if d <= 1 and res.energy > 900]
        if adjacent and random.random() < raid_base:
            # Hamilton's rule: prefer raiding strangers over genetic relatives (see _relatedness)
            strangers = [(res, d) for res, d in adjacent
                         if (res.id not in r.bonds or r.bonds[res.id].quality <= 0)
                         and _relatedness(r, res) < 0.25]
            # Below extreme pressure, prefer seizing from strangers over one's own
            # established relationships or kin; only true crisis (pressure >= 2.0) erodes that
            # Raise pressure threshold for raiding relatives (kin discount per Hamilton's rule)
            pool = strangers if (strangers and pressure < 1.5) else adjacent
            if pool is adjacent:
                # Even among all adjacent, prefer lower-relatedness targets when pressure is moderate
                pool.sort(key=lambda x: _relatedness(r, x[0]))
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

    # MIGRATE (general): the last resort in the Malthusian release-valve chain — population
    # pressure has already made local resource competition (raiding, above) the first
    # response; only when there is no one nearby worth raiding AND the immediate area is
    # genuinely scarce does relocating make sense. Migration itself costs real energy every
    # step (_do_move), so it requires a surplus to spend on the journey, not triggering
    # exactly when already energy-poor (which previously sent residents wandering while
    # running on empty, and — combined with this branch outranking SOCIAL below — starved
    # bond formation almost entirely under the sustained pressure this simulation settles into).
    if pressure > 1.3 and r.energy > MIGRATION_ENERGY_SURPLUS_MIN:
        local_scarce = here.biomass < 10 and here.leftover < 5
        raidable_nearby = any(d <= 1 and res.energy > 900 for res, d in near_res)
        if local_scarce and not raidable_nearby and random.random() < MIGRATION_CHANCE:
            wide_cells = _nearby_cells(r.x, r.y, radius + 4, grid)
            far_candidates = [(c, d) for c, d in wide_cells if d > radius and c.biomass > 15]
            if far_candidates:
                target_cell = max(far_candidates, key=lambda x: x[0].biomass)[0]
                return _step_toward(r.x, r.y, target_cell.x, target_cell.y, grid)

    # FISSION: band-level group splitting (Service 1962, "Primitive Social Organization") —
    # under sustained pressure, once local competition (raiding, above) AND ordinary local
    # relocation (MIGRATE general, above) are both unavailable/exhausted, a LOW-standing
    # resident (someone without a following/teaching investment to lose, unlike a chief/priest
    # who has followers depending on them) may undertake a genuinely long-distance relocation
    # toward unclaimed territory — this is what lets the population actually split into
    # geographically distinct, bond-graph-distinct clusters over time, rather than the single
    # homogeneous group MIGRATE(general)'s short local search always converges back toward
    # (RFC-0007: emergent group divergence via individual relocation, no authored Tribe object).
    if (pressure > FISSION_PRESSURE_THRESHOLD and r.energy > FISSION_ENERGY_SURPLUS_MIN
            and not r.has_chief_standing() and not r.has_priest_standing()
            and r.age > REPRODUCTION_AGE):
        local_scarce = here.biomass < 10 and here.leftover < 5
        raidable_nearby = any(d <= 1 and res.energy > 900 for res, d in near_res)
        wide_scarce = not any(d > radius and c.biomass > 15 for c, d in _nearby_cells(r.x, r.y, radius + 4, grid))
        if local_scarce and not raidable_nearby and wide_scarce and random.random() < FISSION_CHANCE:
            target_cell = _find_fission_target(r, grid)
            if target_cell:
                return _step_toward(r.x, r.y, target_cell.x, target_cell.y, grid)

    # CRITICAL / HUNGRY: find food
    if r.energy < 1200:
        if here.biomass > 3:
            return ('forage', None, None, None)
        best = _best_food(cells)
        if best:
            return _step_toward(r.x, r.y, best.x, best.y, grid)
        return _random_move(r, grid)

    # INJURED: rest heals `2.5 * endurance` health/tick, but sustained population pressure
    # drains health continuously via malnutrition (below) — a resident with below-average
    # endurance can lose that race indefinitely once health dips under 50, getting stuck
    # resting forever under exactly the pressure range (>1.0) this simulation settles into,
    # never reaching REPRODUCE/SOCIAL below. Same "well-intentioned priority becomes a trap
    # under steady-state conditions" issue MIGRATE (general) had above. Below a hard floor
    # (25) resting is the only real option — genuinely incapacitated; between 25-50 it's a
    # strong preference, not an absolute one, leaving real room for other needs.
    if r.health < 25 and r.energy > 600:
        return ('rest', None, None, None)
    if r.health < 50 and r.energy > 600 and random.random() < 0.5:
        return ('rest', None, None, None)

    # REPRODUCE — fertility drops under Malthusian pressure; additionally, chronic malnutrition
    # (measured by malnutrition_debt) directly suppresses individual fecundity even when energy
    # is momentarily sufficient, reflecting real physiological depletion from past caloric stress.
    if r.energy > REPRODUCTION_ENERGY and r.age > REPRODUCTION_AGE and _is_fertile(r, tick):
        fertility = max(0.0, 1.0 - (pressure - 1.0) * 0.5)
        # Malnutrition debt reduces fertility: a resident at full debt (100.0) has fertility halved
        # Additionally, if malnutrition debt exceeds a critical threshold, reproduction is impossible
        if r.malnutrition_debt > 60.0:
            fertility = 0.0
        else:
            fertility *= max(0.5, 1.0 - (r.malnutrition_debt / NUTRITION_DEBT_CAP) * 0.5)
        if random.random() < fertility:
            # Reproduction prefers an already-bonded partner — real, if modest, relationship
            # required (REPRODUCTION_BOND_THRESHOLD) — over the nearest qualifying stranger.
            # This is what makes population structure into real kin-based groups rather than
            # everyone blending into one undifferentiated pool regardless of history (RFC-0004
            # Group Behavior: groups emerge from repeated interaction + kinship, not proximity
            # alone). Not an absolute gate — reproducing with a completely unbonded stranger
            # still happens sometimes (STRANGER_REPRODUCTION_CHANCE), real exogamy exists too.
            # RFC-0011 incest avoidance: every candidate list is additionally filtered by real
            # lineage (_relatedness), not just bond quality — kin are frequently bonded (see
            # birth-bonds in _spawn) without that making reproduction between them acceptable.
            # If no non-kin candidate exists at all, this resident simply doesn't reproduce this
            # tick (falls through) rather than falling back to an unconditional stranger.
            spouse_nearby = [(res, d) for res, d in near_res
                              if r.spouse_id is not None and res.id == r.spouse_id
                              and res.energy > REPRODUCTION_ENERGY and res.age > REPRODUCTION_AGE
                              and _is_fertile(res, tick)
                              and (not INCEST_AVOIDANCE_ENABLED or _relatedness(r, res) < INCEST_RELATEDNESS_THRESHOLD)]
            bonded = [(res, d) for res, d in near_res
                      if res.energy > REPRODUCTION_ENERGY and res.age > REPRODUCTION_AGE
                      and res.sex != r.sex
                      and _is_fertile(res, tick)
                      and res.id in r.bonds and r.bonds[res.id].quality > REPRODUCTION_BOND_THRESHOLD
                      and (not INCEST_AVOIDANCE_ENABLED or _relatedness(r, res) < INCEST_RELATEDNESS_THRESHOLD)]
            if spouse_nearby:
                partners = spouse_nearby
            elif bonded:
                partners = bonded
            elif random.random() < STRANGER_REPRODUCTION_CHANCE:
                # Exogamy searches a WIDER radius than ordinary local candidates, not just the
                # same near_res pool — a small, spatially clustered population is exactly the
                # case where everyone nearby quickly becomes kin (RFC-0011: incest avoidance is
                # only survivable alongside a real path to genuinely unrelated partners). Real
                # small societies solve this by seeking spouses from beyond the immediate local
                # group specifically because the local group is inbred-risk; a fixed local-only
                # stranger search would otherwise leave this branch permanently empty once a few
                # generations pass, since STRANGER_REPRODUCTION_CHANCE succeeding doesn't help if
                # there is no actual unrelated candidate within reach.
                exogamy_pool = _nearby_residents(r.x, r.y, radius * 2, residents)
                partners = [(res, d) for res, d in exogamy_pool
                            if res.energy > REPRODUCTION_ENERGY and res.age > REPRODUCTION_AGE
                            and res.sex != r.sex
                            and _is_fertile(res, tick)
                            and (not INCEST_AVOIDANCE_ENABLED or _relatedness(r, res) < INCEST_RELATEDNESS_THRESHOLD)]
            else:
                partners = []
            if partners:
                p = min(partners, key=lambda x: x[1])[0]
                if abs(p.x - r.x) + abs(p.y - r.y) <= 1:
                    return ('reproduce', None, None, p.id)
                return _step_toward(r.x, r.y, p.x, p.y, grid)

    # MATE PROVISIONING — a male with real surplus checks on a bonded female partner
    # unconditionally (not gated on population pressure like SOCIAL below), since she
    # produces no personal energy from foraging at all (see _do_forage) and providing for
    # a mate/family is a base survival behavior, not a luxury that only shows up once the
    # environment is stressed. Without this separate, higher-priority path, provisioning
    # would depend on SOCIAL's `pressure > 1.0` gate, which early-game (population still
    # below carrying capacity) can leave unmet for a long stretch — exactly when founding
    # females are most exposed, having no accumulated reserve yet.
    if r.sex == 'male' and r.energy > MATE_PROVISIONING_ENERGY_THRESHOLD:
        if r.spouse_id is not None:
            # Married: provisioning concentrates on the actual spouse, not diffused across
            # every bonded female — this is the whole point of the exclusive pair-bond.
            needy_mates = [(res, d) for res, d in near_res
                           if res.id == r.spouse_id and res.energy < 2200]
        else:
            needy_mates = [(res, d) for res, d in near_res
                           if res.sex == 'female' and res.id in r.bonds
                           and r.bonds[res.id].quality > REPRODUCTION_BOND_THRESHOLD
                           and res.energy < 2200]
        if needy_mates:
            mate = min(needy_mates, key=lambda x: x[1])[0]
            if abs(mate.x - r.x) + abs(mate.y - r.y) <= 1:
                return ('interact', None, None, mate.id)
            return _step_toward(r.x, r.y, mate.x, mate.y, grid)

    # SOCIAL — prefer approaching someone already familiar (bonded or kin) over a genuine
    # stranger, mirroring real intergroup wariness: repeated trust builds within an existing
    # circle, contact with true outsiders stays comparatively rare (see RAID/_maybe_trade for
    # where outsider contact actually resolves — as conflict or exchange, not casual bonding).
    if r.traits.sociability > 0.5 and near_res and pressure > 1.0 and random.random() < 0.5:
        familiar = [res for res, d in near_res if res.id in r.bonds or _relatedness(r, res) > 0]
        t = random.choice(familiar) if familiar and random.random() < 0.8 else random.choice(near_res)[0]
        if abs(t.x - r.x) + abs(t.y - r.y) <= 1:
            return ('interact', None, None, t.id) if r.age > 5 and random.random() < (1.0 / (1 + r.traits.sociability * 2)) * 1.5 or random.random() < 0.1 else ('rest', None, None, None)

    # FORAGE if not full
    if r.energy < 2400 and here.biomass > 10 and random.random() < (1.0 - (pressure - 1.0) * 0.2):
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
    mine_suit = TERRAIN_MINING.get(cell.terrain, 0) * zone_cfg['mining_suitability']

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
    if mine_suit > 0 and 'mining' not in r.known_knowledge:
        if random.random() < MINING_DISCOVERY_CHANCE * mine_suit:
            mineral_type = _pick_archetype(MINERAL_ARCHETYPES, cell.climate)
            _learn_knowledge(r, 'mining', {
                'level': 0.15, 'source': 'experimented_with_extraction', 'tick_learned': tick,
                'crop_type': mineral_type,
            })
            discovery_msg = f'{r.name} discovered how to mine {mineral_type}'

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
            and (r.resources.get('iron_ore', 0) > FERTILIZER_INDUSTRIAL_INPUT_MIN
                 or r.resources.get('coal', 0) > FERTILIZER_INDUSTRIAL_INPUT_MIN)
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

    # Mining — extraction adds directly to the miner's personal resource stockpile rather
    # than energy; minerals are goods to trade or have raided, not food.
    if mine_suit > 0 and 'mining' in r.known_knowledge:
        mineral_type = r.known_knowledge['mining'].get('crop_type')
        if mineral_type:
            skill = r.skills.get('mining', 0) / 100.0
            yield_amount = MINING_YIELD_PER_TICK * (0.5 + skill) * mine_suit
            r.resources[mineral_type] = r.resources.get(mineral_type, 0.0) + yield_amount
        if random.random() < 0.03:
            _reinforce_knowledge(r, 'mining', 0.02)

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
        # Sex-based division of labor: reproduction/childcare responsibilities reduce, but
        # do not zero out, a female's foraging output — real hunter-gatherer ethnography
        # (e.g. Hadza gathering studies) shows women's gathering reliably contributes a
        # large share of calories, just typically less than men's higher-risk/higher-return
        # foraging. A hard zero was tried first and caused total economic collapse (halving
        # aggregate production while consumption stayed the same, for both sexes) — this
        # keeps genuine asymmetry and real dependency on mate provisioning (_do_interact)
        # without making the population's energy math structurally unsolvable.
        sex_mult = 1.0 if r.sex == 'male' else FEMALE_FORAGE_MULT
        gain = harvest * conversion * sex_mult
        pre_cap_energy = r.energy + gain - effort
        r.energy = min(MAX_ENERGY, pre_cap_energy)
        r.food_total += harvest

        # Surplus beyond what a farmer can personally consume becomes a tradeable/raidable
        # stockpile rather than being wasted at the energy cap — only real, sustained surplus
        # (a well-fed farmer producing more than they can eat), not routine foraging gain.
        if farm_suit > 0 and 'crop_cultivation' in r.known_knowledge and pre_cap_energy > MAX_ENERGY:
            crop_type = r.known_knowledge['crop_cultivation'].get('crop_type')
            if crop_type:
                surplus = (pre_cap_energy - MAX_ENERGY) * CROP_SURPLUS_CONVERSION
                r.resources[crop_type] = r.resources.get(crop_type, 0.0) + surplus

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
    if 'spoken_language' in r.known_knowledge:
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


def _maybe_trade(r, target, tick):
    """Opportunistic exchange of surplus resources (crops/minerals) between two residents who
    happen to meet — not a scripted trade route (RFC-0007 explicitly forbids that), just
    individual reciprocity extended to named goods the same way food-sharing already works for
    calories. A resident with real surplus of something the other visibly lacks may give some
    away; this is a one-off gift-style exchange, not a negotiated barter."""
    if not r.resources or random.random() >= TRADE_CHANCE:
        return None
    candidates = [
        name for name, qty in r.resources.items()
        if qty > TRADE_SURPLUS_FLOOR and target.resources.get(name, 0.0) < qty * 0.3
    ]
    if not candidates:
        return None
    good = random.choice(candidates)
    gift = r.resources[good] * TRADE_GIFT_FRACTION
    r.resources[good] -= gift
    target.resources[good] = target.resources.get(good, 0.0) + gift
    r.bonds[target.id].quality = min(1.0, r.bonds[target.id].quality + 0.15)
    target.bonds[r.id].quality = min(1.0, target.bonds[r.id].quality + 0.15)
    return f'{r.name} traded {good} with {target.name}'


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

    # Mate provisioning — since females produce no personal energy from foraging (see
    # _do_forage), a bonded male reliably shares surplus with her rather than this depending
    # on the generic share below (which is gated on sociability and only fires once she's
    # already critical) — real pair-bonded provisioning is closer to a biological imperative
    # than a personality trait, and needs to be proactive, not just emergency triage.
    if (r.sex == 'male' and target.sex == 'female'
            and target.id in r.bonds and r.bonds[target.id].quality > REPRODUCTION_BOND_THRESHOLD
            and r.energy > MATE_PROVISIONING_ENERGY_THRESHOLD and target.energy < 2200):
        share = min(500, max(0, r.energy - MATE_PROVISIONING_SHARE_FLOOR))
        r.energy -= share
        r.energy_given_away += share  # Big Man standing readout, see chief_standing
        target.energy = min(MAX_ENERGY, target.energy + share * 0.9)
        r.bonds[target.id].quality = min(1.0, r.bonds[target.id].quality + 0.15)
        target.bonds[r.id].quality = min(1.0, target.bonds[r.id].quality + 0.2)
        lang_msg = _maybe_discover_language(r, target, tick, pressure, cooperative=True)
        return lang_msg or f'{r.name} provisioned {target.name}'

    # Share food if one is hungry — this is the highest-signal cooperative act available:
    # a real payoff exchanged between two individuals, not just proximity or small talk.
    if r.energy > 1800 and target.energy < 900 and r.traits.sociability > 0.4:
        share = min(450, r.energy - 1500)
        r.energy -= share
        r.energy_given_away += share  # Big Man standing readout, see chief_standing
        target.energy = min(MAX_ENERGY, target.energy + share * 0.9)
        r.bonds[target.id].quality = min(1.0, r.bonds[target.id].quality + 0.2)
        target.bonds[r.id].quality = min(1.0, target.bonds[r.id].quality + 0.3)
        lang_msg = _maybe_discover_language(r, target, tick, pressure, cooperative=True)
        return lang_msg or f'{r.name} shared food with {target.name}'

    # Trade — same emergent, individual-level pattern as food-sharing above, but for named
    # crop/mineral resources rather than calories; see _maybe_trade.
    trade_msg = _maybe_trade(r, target, tick)
    if trade_msg:
        return trade_msg

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
            r.students_taught += 1  # prestige standing readout, see priest_standing --
                                      # first-time transmission only, not reinforcement
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
    if INCEST_AVOIDANCE_ENABLED and _relatedness(r, target) >= INCEST_RELATEDNESS_THRESHOLD:
        # RFC-0011 hard guard: decide()'s candidate filtering already excludes kin, but this
        # is checked again here so reproduction between parent-child/full/half siblings can
        # never actually execute even if a stale or externally-supplied target_id slips through.
        return None, next_id
    if r.energy < _reproduction_cost(r) or target.energy < _reproduction_cost(target):
        return None, next_id
    if abs(r.x - target.x) + abs(r.y - target.y) > 1:
        return None, next_id
    if not (_is_fertile(r, tick) and _is_fertile(target, tick)):
        # Postpartum recovery hard guard (see POSTPARTUM_RECOVERY_TICKS) -- decide()'s candidate
        # filtering already excludes a mother still recovering, checked again here so a stale
        # target_id can't bypass the minimum birth spacing.
        return None, next_id

    r.energy -= _reproduction_cost(r)
    target.energy -= _reproduction_cost(target)
    r.children += 1
    target.children += 1
    if r.sex == 'female':
        r.last_birth_tick = tick
    if target.sex == 'female':
        target.last_birth_tick = tick

    # First shared reproduction establishes an exclusive pair-bond (if neither already has
    # one) — concentrates future provisioning/reproduction on this one partner rather than
    # diffusing across every bonded relationship (see decide()'s MATE PROVISIONING/REPRODUCE).
    if r.spouse_id is None and target.spouse_id is None:
        r.spouse_id = target.id
        target.spouse_id = r.id

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

        # A raid also seizes whatever named resource the raider is most short of, if the
        # victim actually holds any — resource conflict riding the same win/lose resolution
        # as the energy theft above, not a separate mechanic.
        resource_msg = ''
        if target.resources:
            held_by_raider = set(r.resources.keys())
            lacking = [name for name in target.resources if name not in held_by_raider]
            steal_target = random.choice(lacking) if lacking else max(target.resources, key=target.resources.get)
            steal_amount = target.resources[steal_target] * 0.5
            if steal_amount > 0.01:
                target.resources[steal_target] -= steal_amount
                if target.resources[steal_target] < 0.01:
                    del target.resources[steal_target]
                r.resources[steal_target] = r.resources.get(steal_target, 0.0) + steal_amount
                resource_msg = f' and {steal_amount:.1f} {steal_target}'
        return f'{r.name} raided {target.name} — stole {stolen:.0f} food{resource_msg}'
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
        self._state_cache = None
        self._state_cache_time = 0.0

        self.ai = AIEngine()

        # Multiple founding clusters (see NUM_FOUNDING_CLUSTERS/CLUSTER_SPAWN_MARGIN), pushed as
        # close to the map's two edges as the margin allows to maximize separation -- guarantees
        # genuinely unrelated candidates exist for exogamy/incest avoidance without depending
        # on emergent fission to eventually create that separation (verified via extensive
        # testing that fission alone isn't fast/reliable enough on its own).
        if NUM_FOUNDING_CLUSTERS == 1:
            cluster_centers = [GRID_W // 2]
        else:
            span = GRID_W - 2 * CLUSTER_SPAWN_MARGIN
            cluster_centers = [
                CLUSTER_SPAWN_MARGIN + int(i * span / (NUM_FOUNDING_CLUSTERS - 1))
                for i in range(NUM_FOUNDING_CLUSTERS)
            ]
        for center_x in cluster_centers:
            cluster_residents = []
            for _ in range(CLUSTER_POPULATION):
                self._next_id += 1
                r = _spawn(self._next_id, self.grid, 0, spawn_center_x=center_x)
                cluster_residents.append(r)
                self.residents.append(r)

            # Founding couples: the initial population has no parents to inherit birth-bonds
            # from (see _spawn), so without this, seed-generation females have zero path to
            # mate provisioning until a bond happens to form through ordinary interaction —
            # in practice too slow, since they produce no personal energy from foraging at all
            # (see _do_forage) and were observed starving before any bond could form. Real
            # founding populations of a settlement already include paired mates, not
            # unattached strangers, so pair up opposite-sex members within THIS cluster only —
            # pairing across clusters would defeat the point of seeding separate lineages.
            males = [r for r in cluster_residents if r.sex == 'male']
            females = [r for r in cluster_residents if r.sex == 'female']
            for m, f in zip(males, females):
                m.bonds[f.id] = Bond(f.id, 0.3, 0)
                f.bonds[m.id] = Bond(m.id, 0.3, 0)

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
        carrying_cap = max(10, (total_regrow * 38.0 * CARRYING_CAPACITY_MULT) / (BASELINE_ENERGY_COST * 8.0))
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

            # Held resources (crops/minerals) decay slowly — spoilage, personal consumption,
            # or informal give-away not otherwise modeled — same entropy principle as leftover
            # food on the ground (RFC-0001 Law 10), so stockpiles don't grow unbounded.
            if r.resources:
                for res_name in list(r.resources.keys()):
                    r.resources[res_name] *= (1.0 - RESOURCE_STOCKPILE_DECAY)
                    if r.resources[res_name] < 0.01:
                        del r.resources[res_name]

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
            erosion_threshold, death_zone = _calorie_thresholds(r)
            in_crisis = r.energy < death_zone
            recovering = r.energy > erosion_threshold
            if r.energy < erosion_threshold:
                deficit = (erosion_threshold - r.energy) / erosion_threshold
                r.health -= HEALTH_EROSION_RATE * deficit * pressure_mult
            if in_crisis:
                severe_deficit = (death_zone - r.energy) / death_zone
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

            # Disease — base chance + crowding + pressure, tempered by immunity (see
            # IMMUNITY_DISEASE_MULT) -- a resident at the species-mean immunity (0.5) sees
            # baseline risk/damage unchanged; above/below that scales both down/up.
            immunity_mult = max(0.2, IMMUNITY_DISEASE_MULT * (1.0 - r.traits.immunity))
            crowd = cell_pop.get((r.x, r.y), 1) - 1
            disease_p = (DISEASE_BASE_CHANCE + DISEASE_CROWD_BONUS * crowd) * pressure_mult * immunity_mult
            if r.health < 40:
                disease_p *= DISEASE_LOW_HEALTH_MULT
            if random.random() < disease_p:
                dmg = random.uniform(DISEASE_DMG_MIN, DISEASE_DMG_MAX) * immunity_mult
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
            # Thresholds scale down for females (see FEMALE_NUTRITION_THRESHOLD_MULT) to match
            # their lower baseline energy need (see Resident.upkeep) -- the same absolute energy
            # level represents less real deficit for her than for a male.
            stress_threshold = NUTRITION_STRESS_ENERGY * (FEMALE_NUTRITION_THRESHOLD_MULT if r.sex == 'female' else 1.0)
            recovery_threshold = NUTRITION_RECOVERY_ENERGY * (FEMALE_NUTRITION_THRESHOLD_MULT if r.sex == 'female' else 1.0)
            if r.energy < stress_threshold:
                r.malnutrition_debt = min(NUTRITION_DEBT_CAP, r.malnutrition_debt + NUTRITION_DEBT_RATE)
            elif r.energy > recovery_threshold:
                r.malnutrition_debt = max(0.0, r.malnutrition_debt - NUTRITION_RECOVERY_RATE)

            # Age decline — onset and severity depend on nutritional history, not just raw
            # age. A well-fed resident's decline curve stretches toward MAX_AGE; a chronically
            # malnourished one (e.g. a pre-agriculture forager living hand-to-mouth) starts
            # declining sharply in their 30s regardless of chronological age remaining.
            # Female longevity (see FEMALE_MAX_AGE_BONUS) -- her decline curve stretches
            # proportionally further, not just her hard ceiling, so she doesn't hit the same
            # decline severity at the same raw age as a male despite living longer overall.
            female_age_decline_span = AGE_DECLINE_SPAN + FEMALE_MAX_AGE_BONUS
            effective_max_age = MAX_AGE + FEMALE_MAX_AGE_BONUS if r.sex == 'female' else MAX_AGE
            effective_decline_span = female_age_decline_span if r.sex == 'female' else AGE_DECLINE_SPAN
            if r.age > AGE_DECLINE_ONSET:
                base_progress = (r.age - AGE_DECLINE_ONSET) / effective_decline_span
                nutrition_penalty = (r.malnutrition_debt / NUTRITION_DEBT_CAP) * 0.8
                # Inbreeding load shortens expected lifespan (RFC-0011: a genetics-level cost,
                # not a behavioral prohibition) -- same mechanism as the malnutrition penalty,
                # since both represent accumulated biological stress accelerating decline.
                inbreeding_penalty = r.inbreeding_load * INBREEDING_AGING_PENALTY
                p = min(0.5, (base_progress + nutrition_penalty + inbreeding_penalty) * 0.10)
                if random.random() < p:
                    r.health -= 5

            # Death check
            if r.health <= 0 or r.age > effective_max_age:
                if r.age > effective_max_age:
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
                if r.spouse_id is not None:
                    # Widowhood — free the surviving spouse to remarry rather than staying
                    # permanently bonded to a dead partner (see _do_reproduce's pair-bond gate).
                    for other in self.residents:
                        if other.id == r.spouse_id:
                            other.spouse_id = None
                            break
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

        # Group-count: periodic (not every-tick) union-find over the bond graph -- connected
        # components of residents linked by any positive-quality bond. This is a pure detection
        # pass (RFC-0007: computing metrics over populations is explicitly permitted; the engine
        # never creates a Tribe/Group object, this is read-only observability). O(n + edges) via
        # union-find with path compression, run once per season rather than every tick since
        # group structure changes slowly relative to a single day-tick.
        if tick % SEASON_LENGTH == 0 or not hasattr(self, '_last_group_count'):
            parent = {r.id: r.id for r in living}

            def find(i):
                while parent[i] != i:
                    parent[i] = parent[parent[i]]
                    i = parent[i]
                return i

            def union(a, b):
                ra, rb = find(a), find(b)
                if ra != rb:
                    parent[ra] = rb

            for r in living:
                for bond_id, bond in r.bonds.items():
                    if bond.quality > 0 and bond_id in parent:
                        union(r.id, bond_id)
            groups = {}
            for r in living:
                root = find(r.id)
                groups[root] = groups.get(root, 0) + 1
            self._last_group_count = len(groups)
            self._last_largest_group = max(groups.values(), default=0)
        group_count = self._last_group_count
        largest_group_size = self._last_largest_group

        gini = 0.0
        if n > 1:
            es = sorted(r.energy for r in living)
            s = sum(es)
            if s > 0:
                gini = sum((2*i - n + 1) * e for i, e in enumerate(es)) / (n * s)

        # Clustering: avg number of residents within radius 2 — bucketed by grid cell for
        # O(n) instead of the previous O(n^2) all-pairs distance check, which became the
        # dominant per-tick cost as population grew (1292 residents was ~1.67M comparisons
        # every single tick, measured live at 15+ second API response times).
        cluster = 0.0
        if n > 0:
            buckets: dict[tuple, list] = {}
            for r in living:
                buckets.setdefault((r.x, r.y), []).append(r)
            total = 0
            for r in living:
                for dx in range(-2, 3):
                    max_dy = 2 - abs(dx)
                    for dy in range(-max_dy, max_dy + 1):
                        for r2 in buckets.get((r.x + dx, r.y + dy), ()):
                            if r2.id != r.id:
                                total += 1
            cluster = total / n

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
        chief_holders = sum(1 for r in living if r.has_chief_standing())
        priest_holders = sum(1 for r in living if r.has_priest_standing())
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

        mining_holders = sum(1 for r in living if 'mining' in r.known_knowledge)
        mineral_type_counts: dict[str, int] = {}
        for r in living:
            mt = r.known_knowledge.get('mining', {}).get('crop_type')
            if mt:
                mineral_type_counts[mt] = mineral_type_counts.get(mt, 0) + 1
        resource_totals: dict[str, float] = {}
        for r in living:
            for res_name, qty in r.resources.items():
                resource_totals[res_name] = resource_totals.get(res_name, 0.0) + qty

        # Sex-split energy — females produce no personal calories (see _do_forage) and
        # depend on mate provisioning (_do_interact), so this is the key health check for
        # whether that provisioning is actually keeping up, not just an average.
        males = [r for r in living if r.sex == 'male']
        females = [r for r in living if r.sex == 'female']
        avg_energy_male = round(sum(r.energy for r in males) / max(1, len(males)), 1)
        avg_energy_female = round(sum(r.energy for r in females) / max(1, len(females)), 1)

        metrics = {
            'tick': tick,
            'season': season,
            'year': tick // (SEASON_LENGTH * 4),
            'pop': n,
            'avg_energy': round(sum(r.energy for r in living) / max(1, n), 1),
            'avg_energy_male': avg_energy_male,
            'avg_energy_female': avg_energy_female,
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
            'chief_holders': chief_holders,
            'priest_holders': priest_holders,
            'group_count': group_count,
            'largest_group_size': largest_group_size,
            'shelter_holders': shelter_holders,
            'clothing_holders': clothing_holders,
            'fire_holders': fire_holders,
            'avg_immunity': round(sum(r.traits.immunity for r in living) / max(1, n), 3),
            'avg_inbreeding_load': round(sum(r.inbreeding_load for r in living) / max(1, n), 3),
            'irrigation_holders': irrigation_holders,
            'breeding_holders': breeding_holders,
            'fertilizer_holders': fertilizer_holders,
            'crop_types': crop_type_counts,
            'livestock_types': livestock_type_counts,
            'avg_ag_tech_mult': avg_ag_tech_mult,
            'mining_holders': mining_holders,
            'mineral_types': mineral_type_counts,
            'resource_totals': {k: round(v, 1) for k, v in resource_totals.items()},
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
        # Short-TTL cache: this recomputes derived per-resident values (usable_intelligence,
        # brain_capacity, knowledge_capacity) for every living resident on every call, which
        # got measurably expensive as population and per-resident state grew (500+ residents,
        # 8+ second responses observed live). A cache hit also skips self.lock entirely, so it
        # doesn't queue up behind an in-progress tick — the actual dominant cost at high speed.
        # The returned dict is a read-only snapshot; callers must not mutate it in place.
        now = time.time()
        if self._state_cache is not None and (now - self._state_cache_time) < STATE_CACHE_TTL:
            return self._state_cache
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
                'parent_id': r.parent_id, 'mother_id': r.mother_id, 'father_id': r.father_id,
                'sex': r.sex, 'spouse_id': r.spouse_id,
                'spoken_language_id': r.spoken_language_id, 'script_id': r.script_id,
                'cultural_profile': r.cultural_profile,
                'energy_given_away': round(r.energy_given_away, 1), 'students_taught': r.students_taught,
                'inbreeding_load': round(r.inbreeding_load, 3),
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
                'resources': {k: round(v, 1) for k, v in r.resources.items()},
            } for r in living]

            m = self.metrics_history[-1] if self.metrics_history else {}
            zone_boundary = GRID_H // 3
            state = {
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
            self._state_cache = state
            self._state_cache_time = now
            return state

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
