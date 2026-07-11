"""
OCP Phase 1 Simulation Engine
Minimal world tick runner implementing RFC-0001 through RFC-0007.
"""

from dataclasses import dataclass, field, fields, asdict
from typing import Optional
from pathlib import Path
import random
import math
import time
import threading
import json
import os
from .ai import AIEngine

# ── Configuration ──

# Snapshot persistence (see Simulation.save_snapshot/load_or_create) -- a redeploy previously
# meant killing and respawning the process, which always started a brand-new Simulation from
# tick 0 (see run_forever.sh's respawn behavior throughout this project's deploy history).
# Periodically saving live state and loading it back on the next startup means a routine code
# deploy no longer discards the current run. Path lives next to settings.json (same
# Path(__file__).resolve().parent.parent pattern as ai.py's SETTINGS_PATH), i.e. outside the
# `ocp/` package directory that actually gets overwritten on deploy, and is never committed to
# git (runtime state, not source).
SNAPSHOT_PATH = Path(__file__).resolve().parent.parent / "snapshot.json"
SNAPSHOT_INTERVAL_SECONDS = 600  # 10 minutes

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
FOUNDING_HERDER_COUNT = 5  # per cluster -- see the founding-herders block in Simulation.__init__
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
REPRODUCTION_COST = 200.0       # reserve spent per parent per birth -- lowered from 750 (via an
                                  # intermediate 550/300 split); instrumented live testing found
                                  # 96.6% of ALL health-loss events came from caloric erosion,
                                  # confirming an aggregate energy deficit, not a disease problem
                                  # -- reproduction cost was a real, frequent drain on that budget
                                  # once postpartum spacing was removed (births happen often)
FEMALE_REPRODUCTION_COST = 200.0  # unified with the male cost now that the base is already low
                                    # enough not to need a separate, further-reduced female value
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
# A version of exogamy that boosted STRANGER_REPRODUCTION_CHANCE by the resident's own
# inbreeding_load, and preferred the lowest-inbreeding_load exogamy candidate over the nearest
# one, was tried and reverted -- see the REPRODUCE block in decide() for what happened (real
# population decline from the same "re-targets a distant candidate fresh every tick, rarely
# closes the distance" failure pattern as the reverted territorial-retreat mechanic).
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
INBREEDING_LOAD_CAP = 1.0          # every penalty above is calibrated against "load=1.0 ==
                                     # sustained multi-generation isolation" as its worst case
                                     # (see INBREEDING_FITNESS_PENALTY's own comment), but the
                                     # accumulation formula (average of parents' loads + a positive
                                     # increment whenever they're related) has no ceiling -- in a
                                     # population that bottlenecks down to one small closed group
                                     # (no unrelated partner ever available, see group_count),
                                     # every generation adds more with nothing to remove it. Live
                                     # data caught this directly: avg_inbreeding_load reached 3.5-3.8
                                     # (3.5-8x past the documented design ceiling) during a slow
                                     # extinction where pressure stayed near 0 and avg_energy stayed
                                     # healthy the entire time -- a purely genetic death spiral, not
                                     # a resource one. Capping restores the ceiling the rest of the
                                     # mechanic already assumes; it does not add a new penalty.
# Opportunistic raiding (see the OPPORTUNISTIC RAID block in decide(), right after the
# desperation-triggered RAID above it) — the existing raid trigger requires real desperation
# (r.energy < 540 AND local biomass < 3 AND local leftover < 2), which is close to a Malthusian
# last resort; once a population is well-fed (this session's carrying-capacity/output fixes),
# that condition rarely fires at all. Live data confirmed it: 0 raid events out of 80 recent
# events despite population spread across nearly the full map width in many small, spatially
# adjacent clusters. This adds a second, independent trigger: a comfortable, physically stronger
# resident can also raid a nearby weaker stranger purely because the power gap makes it
# profitable, not because either party is starving -- still Hamilton's-rule stranger-preferring,
# still an individual-level decision using only _capability (no authored war/territory object,
# RFC-0007).
OPPORTUNISTIC_RAID_ENERGY_MIN = 1400.0  # raider needs real comfort/surplus -- this is a
                                          # profit-seeking choice, not another desperation valve
OPPORTUNISTIC_RAID_POWER_RATIO = 1.5    # must be clearly the stronger party, not just willing
OPPORTUNISTIC_RAID_CHANCE = 0.08        # scaled further by risk_tolerance AND the payoff_ratio
                                          # (see decide()) -- rare and opportunistic, not routine
# Territorial defense (see TERRITORIAL DEFENSE in decide()) -- a chief-only raid trigger against
# a nearby resource-competing stranger (someone farming/herding right next door, not trading),
# independent of OPPORTUNISTIC_RAID's profit-driven gate. Lower power bar than
# OPPORTUNISTIC_RAID_POWER_RATIO -- a chief defending a resource base takes more risk than an
# opportunistic profiteer would.
TERRITORIAL_DEFENSE_CHANCE = 0.15
TERRITORIAL_DEFENSE_POWER_RATIO = 1.2
# Nomadic winter raid (see NOMADIC WINTER RAID in decide()) -- displaced cold-zone pastoralists
# (proven by knowing animal_husbandry, now cold-zone-exclusive) raiding agricultural outsiders
# during winter. Real historical pattern (Mongol/Hunnic/Scythian-style incursions), higher
# chance and lower power bar than ordinary OPPORTUNISTIC_RAID -- a herder whose own pastures
# just failed for the season has more at stake than an ordinary opportunist.
NOMADIC_WINTER_RAID_CHANCE = 0.2
NOMADIC_WINTER_RAID_POWER_RATIO = 1.1
# Horse range extension (see LIVESTOCK_ARCHETYPES) -- a nomad who specifically domesticated a
# horse (not sheep/cattle) can reach beyond immediate adjacency for the same nomadic-winter
# opportunity above. Deliberately travels toward the NEAREST valid target within range, not the
# "best" one by any quality metric (energy, standing, etc.) -- nearest is what a resident
# actually converges toward as they approach (distance to it can only shrink each step), which
# is what makes this safe; chasing the best-by-quality candidate across a re-evaluated pool
# every tick is exactly the persistent-re-targeting shape that collapsed the reverted
# territorial-retreat and inbreeding-aware-exogamy attempts (see Hierarchies, RFC-0007). Once
# adjacent, resolves exactly like the existing d<=1 case (same capability/power-ratio gate) --
# this only changes how far a horse owner will travel to find that adjacency, not what happens
# once there. Reaching a non-hostile resident (e.g. a merchant) this way doesn't itself trade --
# it just puts the horse owner in range for the ordinary SOCIAL block to pick it up next tick,
# same as any other proximity -- no new trade-seeking logic needed.
HORSE_RAID_RANGE = 8
# Coercion (see coerced_by on Resident, _do_raid's win branch, and _tick's forage-tribute
# block) — population as a resource, RFC-0007 compliant: this is a per-individual relationship
# field like spouse_id/bonds, not an authored "Slave" class or group object. An overwhelming
# raid win against a target nobody is bonded strongly enough to defend can turn a one-off theft
# into ongoing labor extraction — the coerced resident keeps deciding and acting for themselves
# (forages, socializes, can still reproduce), only a share of their foraging surplus is
# involuntarily redirected each tick, exactly the same "surplus flows to someone else" pattern
# mate provisioning already uses, just coerced instead of chosen. Never stacks (one controller
# at a time) and never permanent (RFC-0007: collapse/regression must stay possible) — ends when
# the controller dies or via a small standing per-tick escape chance.
COERCION_POWER_RATIO = 1.6         # raid win must be decisive, not a close fight
COERCION_MAX_TARGET_BOND = 0.3     # target has no bond strong enough to imply someone would
                                     # defend them
COERCION_CHANCE = 0.15             # most decisive raid wins still stay simple one-off theft;
                                     # only some escalate to ongoing control
COERCION_TRIBUTE_SHARE = 0.4       # share of each forage energy gain redirected to the
                                     # controller
COERCION_ESCAPE_CHANCE = 0.005     # small per-tick chance to break free even while the
                                     # controller is alive -- coercion is a standing risk, not
                                     # a guaranteed permanent lock
# Follower tribute (see _tick's forage-tribute block, and FOLLOW STRONGER in decide()) -- the
# material counterpart of FOLLOW STRONGER, which already has bonded residents physically
# gravitate toward a more capable ally. Once a resident is bonded to a chief-standing ally
# (Sahlins' Big Man, see Resident.chief_standing), a modest voluntary share of their own forage
# surplus flows to that leader -- a real, if small, tribute economy, but built entirely from an
# ordinary bond plus an existing status readout, not an authored "Follower" role. Deliberately
# smaller than COERCION_TRIBUTE_SHARE: this is chosen support, not forced extraction, and
# doesn't touch the chief's own energy_given_away (receiving tribute must not itself inflate
# the redistribution-based standing that made them a chief in the first place).
FOLLOWER_TRIBUTE_SHARE = 0.15
# Leadership succession (see the death-check block in Simulation._tick) -- inherited capital,
# not an inherited title (chief_standing itself can never be assigned, only earned by the
# heir's own future behavior). Half, not all: real inheritance rarely transfers a decedent's
# full estate to one heir cleanly, and this keeps the boost meaningful without being a full
# free ride to chief_standing.
HEIR_ENERGY_INHERITANCE = 0.5
# Sex-based division of labor (see _do_forage) — females retain a real, if reduced, foraging
# contribution rather than zero; see the note at the gain calculation for why zero failed.
FEMALE_FORAGE_MULT = 0.7  # raised from 0.5 -- with instrumented testing showing the population's
                            # aggregate energy supply chronically running a real deficit (96.6%
                            # of health-loss events from caloric erosion, not disease), 0.5 was
                            # too conservative now that so much else has changed since it was set
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
# Territorial retreat (Hawk-Dove/Bourgeois asymmetric-contest framing) was attempted and
# reverted -- see the comment in decide() where it used to live for what was tried and why it
# didn't hold up across four rounds of local testing (real population decline toward
# near-extinction and worsening inbreeding_load, not fixable by threshold tuning alone).
# Gifted scouts (see Resident.is_gifted_scout) -- rare individuals whose intelligence,
# perception, strength, AND speed all happen to be exceptional simultaneously, purely from the
# existing continuous trait system (RFC-0004: emergence from combinations of simpler traits,
# not a new hardcoded "leadership" category). They see farther and can lead bonded followers to
# a distant target they alone found (see FISSION), an emergent form of leadership rather than
# an authored Leader role.
GIFTED_SCOUT_TRAIT_THRESHOLD = 1.15  # calibrated live: at 1.3, ~0/1000 population ever
                                       # qualified (too strict given regression-to-the-mean
                                       # pulls trait blends back toward 1.0); at 1.15, roughly
                                       # 0.2-0.5% of a population qualifies -- genuinely rare
                                       # but actually occurs at population scales of a few hundred+
GIFTED_SCOUT_CELL_CAP = 30           # expanded terrain-scan radius, vs PERCEPTION_CELL_CAP for
                                       # everyone else -- rare enough this doesn't reintroduce
                                       # the performance problem that cap was fixing
MERCHANT_CELL_CAP = 40               # see Resident.is_merchant -- "sees ten times further" (vs
                                       # PERCEPTION_CELL_CAP=4), same rarity-based performance
                                       # reasoning as GIFTED_SCOUT_CELL_CAP above
GIFTED_SCOUT_SEARCH_RADIUS = 12      # wider _find_fission_target sampling radius for scouts
GIFTED_SCOUT_HUNT_BONUS = 1.4        # forage output multiplier in cold/tropical zones (low
                                       # farming suitability, where hunting/gathering skill
                                       # matters more than cultivation) -- see _do_forage
GIFTED_SCOUT_CROWD_RADIUS = 6        # in _explore, a scout in a temperate zone treats any
                                       # other resident within this radius as "crowded" and
                                       # downweights that direction, preferring genuinely
                                       # unclaimed land over already-contested territory
GIFTED_SCOUT_DANGER_SENSE_RADIUS = 3 # radius within which a gifted scout can spot a real
                                       # raid threat (high risk_tolerance, no/weak bond) before
                                       # it happens, and lead bonded kin away from it
# FOLLOW STRONGER (see _capability, decide()) -- not exclusive to gifted scouts: ANY bonded
# resident who is meaningfully more capable is worth staying near, since proximity is what
# lets existing food-share/provisioning mechanics actually help. Margin avoids everyone
# constantly chasing everyone over trivial trait noise -- must be a real, not marginal, gap.
CAPABILITY_FOLLOW_MARGIN = 1.5
BASELINE_ENERGY_COST = 60.0     # baseline daily metabolic burn before season/technology modifiers
# Carrying capacity ceiling (see Simulation._tick's carrying_cap calculation) -- raised so the
# founding generation and its descendants have enough headroom to coexist rather than the young
# generation's growth crowding directly against the aging founders for the same fixed-size
# resource pie (the founding-cohort synchronized die-off crashed a large fraction of total
# population precisely because total population was already pinned near the old, tighter cap).
CARRYING_CAPACITY_MULT = 1.6
PERCEPTION_BASE_RADIUS = 20
PERCEPTION_CELL_CAP = 4    # lowered further from 12 per direct request -- 81 cells/call is
                           # plenty for local foraging/movement decisions.
                           # hard cap on the radius used for _nearby_cells specifically (see
                           # decide()) -- view_radius() itself can reach 60-65 at high
                           # perception/sociability, and _nearby_cells is an O(radius^2) grid
                           # scan (not bucketable the way resident lookups are), so leaving it
                           # uncapped made a single call ~17,000 cell checks -- profiled as ~70%
                           # of total tick time once population grew into the many hundreds.
                           # Resident-search radius (near_res, social/reproduction range) is
                           # unaffected -- only the terrain/food-cell scan is capped.
COLD_ZONE_FORAGE_CELL_CAP = 9  # wider terrain-scan radius for anyone standing in the cold zone
                           # (see cell_radius in decide()), same mechanism already used for
                           # merchants/gifted scouts (MERCHANT_CELL_CAP/GIFTED_SCOUT_CELL_CAP)
                           # applied to a whole zone instead of a rare trait. Direct request: real
                           # wild game is genuinely present across the cold zone (just sparser per
                           # cell than a temperate farm plot), so a forager there should be able to
                           # search further to find it rather than being capped to the same tight
                           # local radius as someone standing on cultivated temperate farmland.
                           # Deliberately just widens the EXISTING _best_food/CRITICAL-HUNGRY
                           # search-a-cell-then-_step_toward-it pattern (cells don't move, so this
                           # carries none of the persistent-re-targeting risk a resident-chasing
                           # mechanic would) -- not a new mechanic, not a regrow-rate change (see
                           # the reverted winter-regrow attempt's RNG-divergence postmortem).
HORSE_FORAGE_CELL_CAP = 12  # wider still than COLD_ZONE_FORAGE_CELL_CAP, for a resident who
                           # specifically domesticated a horse (see LIVESTOCK_ARCHETYPES) -- a
                           # mount extends how far it's worth searching for food, same real-world
                           # logic as HORSE_RAID_RANGE, just for the existing _best_food terrain
                           # scan instead of the nomadic-raid target search. First tried at 16
                           # (paired with HORSE_MOVE_COST_MULT=0.4 below): each bonus verified
                           # safe in isolation, but the COMBINATION caused a real, reproducible
                           # extinction in one test seed (confirmed via separate single-variable
                           # A/B controls, not RNG-chaos noise) -- cheap movement plus a much
                           # wider search radius compounds into far more aggressive wandering
                           # than either alone. Both values narrowed together.
HORSE_MOVE_COST_MULT = 0.6  # see _do_move -- a mount makes the direct kcal cost of a single
                           # movement step cheaper, since the horse does the physical work a
                           # human otherwise would. Direct request ("活动时能量消耗很低"). See
                           # HORSE_FORAGE_CELL_CAP's comment -- narrowed from 0.4 alongside it
                           # after the pair's combined effect caused a real extinction that
                           # neither constant caused alone.
# Comprehensive horse-owner power-up, direct request, tried together at the literally-requested
# magnitudes first (per this session's established practice of testing the actual ask before
# guessing at safer starting values) -- given HORSE_FORAGE_CELL_CAP+HORSE_MOVE_COST_MULT above
# already showed a 2-variable combination can be individually-safe but jointly lethal, a 5-way
# simultaneous stack (carry, move cost, speed, perception, combat) needs especially rigorous
# testing and should be expected to likely need narrowing.
HORSE_CARRY_MULT = 5.0            # _add_resource: horse owner's effective carrying_capacity
                                    # ceiling (see Resident.is_merchant) is multiplied 5x.
HORSE_MOVE_COST_NEAR_ZERO = 0.05  # replaces HORSE_MOVE_COST_MULT for this request specifically
                                    # ("移动的能量消耗接近0") -- not literally 0 to avoid a
                                    # genuinely free, unlimited-distance action.
HORSE_SPEED_MULT = 20              # _step_toward: a horse owner covers up to this many tiles
                                    # in a single move action instead of 1 (checking each
                                    # intermediate tile's passability, stopping at the first
                                    # obstacle or the target, whichever comes first) --
                                    # architecturally new: every other travel mechanic this
                                    # session (FOLLOW STRONGER, MERCHANT SEEK CHIEF, HORSE_RAID_
                                    # RANGE, MIGRATE, EXPLORE) was built and verified assuming
                                    # 1-tile-per-action movement; this changes that invariant for
                                    # horse owners specifically, so it's the highest-risk single
                                    # piece of this request.
HORSE_PERCEPTION_MULT = 10         # terrain/food cell-scan radius only (replaces the ordinary
                                    # PERCEPTION_CELL_CAP baseline with a 10x multiplier for a
                                    # horse owner) -- deliberately NOT applied to the separate
                                    # resident-detection radius (`radius`) that near_res uses,
                                    # since that already reaches 60-65 at high perception/
                                    # sociability; reach for other residents stays governed by
                                    # the already-tested HORSE_RAID_RANGE instead.
HORSE_COMBAT_MULT = 5.0            # applied to _capability() specifically at raid-related power-
                                    # ratio comparisons (OPPORTUNISTIC/TERRITORIAL/NOMADIC_WINTER
                                    # raid gates) and to the actual strength-based win/loss roll
                                    # in _do_raid -- deliberately NOT applied to the FOLLOW
                                    # STRONGER capability comparison (a food-provisioning
                                    # gravitation, not a military one) since the request was
                                    # specifically "武力值" (combat/martial power), not general
                                    # capability.
# Horse's own energy pool (direct follow-up request): the horse itself now needs upkeep, not
# just the rider's own energy -- a real grazing constraint on how far the power-up above can be
# exploited. Deterministic, no random() calls anywhere in this mechanic, so unlike most of this
# session's probability-threshold changes it carries none of the RNG-divergence-chaos risk.
# Net change per tick is replenish - consumption: exactly 0 in the cold zone (the horse's native
# range, LIVESTOCK_ARCHETYPES), a steady -50/tick everywhere else -- so a horse maintains
# indefinitely near cold-zone grazing but runs down over roughly 60 ticks of continuous
# non-cold operation. See Simulation._tick for the update and _horse_bonus_scale for how it
# feeds back into HORSE_CARRY_MULT/HORSE_SPEED_MULT/HORSE_COMBAT_MULT (the three the user
# explicitly named -- not HORSE_MOVE_COST_NEAR_ZERO or HORSE_PERCEPTION_MULT, which stay
# constant for as long as animal_husbandry(horse) is known at all, matching the original
# request's own list of what should degrade).
HORSE_ENERGY_MAX = 3000.0                  # mirrors MAX_ENERGY's "full caloric reserve" scale
HORSE_ENERGY_REPLENISH_COLD = 500.0        # "在寒带基本不会消耗...每天可以补充500卡路里"
HORSE_ENERGY_REPLENISH_OTHER = 450.0       # "进入温带,每个tick补充的卡路里只有450" -- the
                                             # request only named temperate explicitly; tropical
                                             # is treated the same (non-cold) since horses are a
                                             # cold-zone-exclusive archetype in the first place
                                             # (LIVESTOCK_ARCHETYPES) and have no natural range
                                             # in either warm zone.
HORSE_ENERGY_CONSUMPTION = 500.0           # "消耗也是500卡路里" -- constant regardless of zone
HORSE_ENERGY_DEGRADE_THRESHOLD = 1500.0    # bonuses are full-strength at or above this (half of
                                             # HORSE_ENERGY_MAX); below it they fade linearly to
                                             # zero (not negative -- an exhausted horse is worth
                                             # no more than walking, never worse) as horse_energy
                                             # approaches 0. First-pass value: ~30 ticks of grace
                                             # before fading starts, ~30 more to fully fade.
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
COLD_ZONE_DISEASE_MULT = 0.5    # real historical pattern: cold, dry climates suppress pathogen
                                  # survival/transmission better than warm humid ones. Added
                                  # after a cold-zone survival diagnostic found disease (not
                                  # starvation) was the dominant cause of death there (384 vs 133
                                  # over a 2000-tick sample) -- the calorie-erosion health cost of
                                  # a harsh winter was compounding with DISEASE_LOW_HEALTH_MULT
                                  # into a death spiral before anyone could establish a stable
                                  # pastoral economy. Deliberately doesn't touch winter food
                                  # production/upkeep at all (see the reverted winter-regrow
                                  # attempt's RNG-divergence chaos postmortem) -- this targets the
                                  # actual dominant death cause directly instead.
# A TROPICAL_ZONE_DISEASE_MULT (the real-world counterpart to COLD_ZONE_DISEASE_MULT -- warm,
# humid climates support pathogen survival/transmission far better than cold, dry ones) was
# tried and reverted. First at 1.6: a 10-seed test found 1 real extinction (seed 6), confirmed
# via same-seed A/B control as a direct causal effect (963 healthy with the multiplier off, 0
# with it on) -- not RNG-chaos noise. Narrowed to 1.3 on the assumption a smaller number would
# be safer, same pattern that worked for the horse-bonus interaction earlier -- it wasn't:
# narrowing INCREASED the failure count to 2 (the same seed 6 still died, plus a new one, seed
# 9, that had been fine at 1.6). A smaller multiplier causing MORE failures than a larger one
# rules out a simple dose-dependent relationship -- unlike COLD_ZONE_DISEASE_MULT, which only
# ever touched a tiny population share, tropical typically holds a large share of the whole
# population (winter migration alone pushes a lot of people there every year), so a disease-
# probability change there shifts the shared global RNG stream's secondary-random-call timing
# for a much bigger, less predictable slice of the population -- chaos-divergence risk that
# doesn't shrink monotonically with the multiplier's magnitude the way a real causal effect
# would. Reverted entirely; giving tropical its own disease/decay identity needs either a much
# smaller, more targeted mechanism (not a population-wide probability multiplier) or the
# per-resident/per-domain RNG stream fix flagged elsewhere as the actual root cause of this
# whole class of chaos-divergence issue.
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
CULTIVATED_LAND_CONFLICT_THRESHOLD = 0.3  # see the cultivation-driven branch of _do_forage's
                                            # resource-conflict block -- real investment in a
                                            # plot (not just any nonzero cultivation), so a first
                                            # visit before the land is actually developed doesn't
                                            # already count as trespassing
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
# Sex-differentiated end-of-productivity design (replaces an earlier "female lives 15 years
# longer, same shape" version): a female's real productive/reproductive window is bounded, and
# past it she is deliberately made to decline FAST rather than linger for decades consuming
# food without contributing energy or children -- a real resource-allocation logic, not just
# "women live longer." A male's productive window instead fades gradually: he keeps foraging
# but at declining efficiency, rather than a hard cutoff.
FEMALE_FERTILITY_MAX_AGE = 60   # reproduction eligibility ends here (see decide()'s REPRODUCE
                                  # block) -- 15-60 is her full productive/reproductive window
FEMALE_POST_FERTILITY_DECLINE = 12.0  # flat health loss/tick once past FEMALE_FERTILITY_MAX_AGE
                                        # -- steep and roughly age-independent past this point,
                                        # by design a fast decline (~8-10 ticks to death), not a
                                        # gradual one -- "quickly dies, stops costing food"
MALE_FORAGE_DECLINE_ONSET = 50  # a male's foraging efficiency starts fading past this age
MALE_FORAGE_DECLINE_RATE = 0.02  # fraction of forage output lost per year past onset (linear),
                                    # floored at MALE_FORAGE_DECLINE_FLOOR so he never drops to
                                    # zero -- he keeps contributing, just less over time
MALE_FORAGE_DECLINE_FLOOR = 0.4  # minimum forage efficiency multiplier at advanced age
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
ISLAND_FISH_RADIUS = 16    # cells (see Cell.near_island) -- a bit past the island's own
                             # footprint (ISLAND_RADIUS_Y=10) so it covers the flanking river
                             # channels too, not just the island's dry land

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
# Zone specialization: cold is grazing-dominant, temperate is farming-only (grazing_suitability
# 0.0 there, no exception) -- a real economic reason for exchange to matter, not just "one is
# better at X". A small (0.15) farming fallback for the cold zone was tried, on the theory that
# the fully farming-free version (0.0) was creating a bootstrapping trap (near-zero winter
# regrow + 2.8x winter upkeep meant nobody survived long enough to ever discover
# animal_husbandry). Reverted: 3-seed local comparison showed farming_suitability=0.15
# consistently produced LOWER total population than 0.0 (652/224/991 vs 787/706/1129 across
# seeds 1-3) -- domestication discovery for crop_cultivation and animal_husbandry are
# independent random rolls, and cold-zone crops are the two weakest archetypes in
# CROP_ARCHETYPES (sweet_potato/corn, ~0.55-0.6x energy density vs wheat's 1.4x), so a cold-zone
# resident unlucky enough to roll the farming discovery first likely burns a knowledge-capacity
# slot and effort on a genuinely weak option instead of the much more valuable herding path --
# worse than having no fallback at all, not better. The actual bottleneck (survival to ever
# attempt animal_husbandry discovery) needs a different fix, e.g. softening winter's regrow/
# upkeep multipliers directly, not adding a competing weaker discovery path.
CLIMATE_ZONES = {
    'cold':      {'spring': 1.1, 'summer': 0.8, 'autumn': 0.35, 'winter': 0.005,
                  'spring_upkeep': 0.95, 'summer_upkeep': 1.0, 'autumn_upkeep': 1.1, 'winter_upkeep': 2.8,
                  'grazing_suitability': 1.0, 'farming_suitability': 0.0, 'mining_suitability': 1.0},
    'temperate': {'spring': 1.4, 'summer': 1.0, 'autumn': 0.55, 'winter': 0.02,
                  'spring_upkeep': 0.9, 'summer_upkeep': 1.0, 'autumn_upkeep': 1.05, 'winter_upkeep': 1.8,
                  'grazing_suitability': 0.0, 'farming_suitability': 1.0, 'mining_suitability': 0.3},
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
# Fishing (see 'fishing' knowledge in _do_forage) -- any water tile is fishable, but coastal
# water is the richest real fishery (river/lake fish density is real but far lower per unit
# area), further boosted near the island (Cell.near_island, ISLAND_FISH_RADIUS) so it's a
# genuinely distinct specialty rather than "farming, but for water tiles."
TERRAIN_FISHING = {'river': 0.5, 'lake': 0.4, 'coast': 1.0}
NEAR_ISLAND_FISHING_MULT = 2.5

DOMESTICATION_DISCOVERY_CHANCE = 0.0025  # per qualifying forage tick, before suitability scaling
HUSBANDRY_DISCOVERY_MULT = 3.0  # animal_husbandry-specific multiplier on top of the shared
                                  # DOMESTICATION_DISCOVERY_CHANCE above (crop_cultivation/fishing
                                  # discovery are unaffected) -- the cold zone is now
                                  # grazing-only (see CLIMATE_ZONES) with a brutal winter
                                  # (regrow ~0, upkeep 2.8x), so almost nobody was surviving
                                  # long enough to stumble into the herding knowledge that would
                                  # actually let them survive it: a bootstrapping trap, not a
                                  # matter of the population lacking some "nomadic" trait.
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
# Named cold-zone livestock (replacing the generic 'grazer'/'browser' abstraction), same pattern
# as CROP_ARCHETYPES above -- which specific animal a herder ends up with is a weighted-random
# outcome of local suitability, not an authored choice (see _pick_archetype). Real historical
# domestication-order weighting: sheep were domesticated earliest and most widely (hardiest on
# marginal grazing land), cattle need richer pasture but yield the most meat per animal, horses
# were a later, rarer, more prized domesticate. All three are cold-zone-exclusive under the
# current zone exclusivity (CLIMATE_ZONES: only 'cold' has grazing_suitability > 0), so
# temperate/tropical weights are left at the _pick_archetype default (0.1) rather than
# hand-tuned -- they're currently unreachable regardless, same as the 'grazer'/'browser' table
# this replaces already was for temperate/tropical (dead weight since the zone-exclusivity
# change). Tropical livestock (a separate ask, not yet implemented) would need tropical's own
# grazing_suitability raised above 0 first -- a real, currently-open zone-exclusivity change,
# not just another archetype table entry.
LIVESTOCK_ARCHETYPES = {
    'sheep':  {'energy_density_mult': 0.9, 'zone_weights': {'cold': 3.0}},
    'cattle': {'energy_density_mult': 1.3, 'zone_weights': {'cold': 2.5}},
    'horse':  {'energy_density_mult': 0.85, 'zone_weights': {'cold': 2.5}},  # raised from 1.5 on
                # direct request -- now that established herders actually stay put (see
                # COLD_ZONE_HERDER_MIGRATION_THRESHOLD), the horse-specific transportation
                # bonuses (HORSE_FORAGE_CELL_CAP, HORSE_MOVE_COST_MULT, HORSE_RAID_RANGE) have
                # real material to work with, but live data showed 100% of current cold-zone
                # herders had rolled cattle -- horse was the rarest of the three archetypes and
                # had never actually appeared. Matches cattle's weight now instead of trailing
                # both other options; _pick_archetype's random.choices call always consumes the
                # same amount of randomness regardless of which weight wins, so this doesn't
                # carry the RNG-divergence chaos risk that probability-THRESHOLD changes
                # (disease, migration triggers) have shown this session -- a pure weight
                # reallocation among already-equally-likely-to-fire outcomes.
}

# Dietary diversity (see recent_food_types on Resident and _do_forage) -- real nutrition: a
# calorie-sufficient but monotonous diet (one staple crop/livestock type over and over) is
# missing nutrients a varied diet provides, and shows up as reduced foraging/working capacity,
# not just an abstract stat. Modeled as a multiplier on the same forage `gain` calculation
# every other bonus already goes through (sex_mult, ag_tech_mult, GIFTED_SCOUT_HUNT_BONUS),
# not a new independent system -- a single-staple region isn't starved outright, it's capped
# below what genuine variety would let it produce, which is what should eventually make trading
# for a different staple (see the food-exchange/trade work planned next) a real, felt incentive
# rather than a cosmetic option.
DIET_DIVERSITY_WINDOW = 30          # ticks -- a food type eaten this recently still counts
                                      # toward the diversity score
# Three real food categories -- crop, meat, fish (salt is tracked and multiplied entirely
# separately, see SALT_FOOD_BONUS_MULT/SALT_DEFICIT_MULT, since it isn't a calorie source of
# its own) -- rather than a generic "how many distinct archetypes" count. A specific crop_type
# (wheat vs rice) or livestock_type (sheep vs cattle vs horse) doesn't functionally differ
# enough to matter here; what matters is whether the actual food GROUP varies. Foraging wild
# biomass (no cultivation/husbandry/fishing knowledge) counts as its own single category, same
# tier as any one staple -- it's still just one food source, not zero.
FOOD_CATEGORY = {
    'wheat': 'crop', 'rice': 'crop', 'soybean': 'crop', 'sweet_potato': 'crop',
    'corn': 'crop', 'fruit': 'crop',
    'sheep': 'meat', 'cattle': 'meat', 'horse': 'meat',
    'fish': 'fish',
}
DIET_CATEGORY_MULT = {1: 0.7, 2: 1.2, 3: 1.5}  # keyed by count of distinct categories eaten
                                                  # recently (crop/meat/fish/wild, capped at 3
                                                  # real categories -- wild doesn't add a 4th
                                                  # tier on top, see _do_forage).
                                                  # Deepening this (making dietary imbalance
                                                  # sting harder) was tried twice on direct
                                                  # request and reverted both times:
                                                  #   0.55 -> 2 of 3 seeds fully extinct (tick
                                                  #   295, tick 873), third pinned at 79-250 pop.
                                                  #   0.6  -> 1 of 3 seeds fully extinct (tick
                                                  #   1171, confirmed via same-seed A/B control:
                                                  #   that exact seed survives fine to pop 648 at
                                                  #   0.7, so the extinction is caused by the
                                                  #   0.6 change, not a fragile-seed artifact),
                                                  #   the other two seeds also ran measurably
                                                  #   below the healthy 300-900 baseline range.
                                                  # The single-category tier is most residents'
                                                  # baseline forage rate much of the time (not a
                                                  # rare edge case), so it compounds directly
                                                  # into the population's core energy budget --
                                                  # a FLAT deepening has very little safe headroom
                                                  # below 0.7. See DIET_IMBALANCE_PRESSURE_* below
                                                  # for a pressure-gated version instead (only
                                                  # penalize harder once the population is
                                                  # actually crowded, not from the founding ticks).
DIET_IMBALANCE_PRESSURE_THRESHOLD = 1.0  # below this pressure (see Simulation._pressure), the
                                           # single-category tier stays at the safe flat 0.7 --
                                           # a small/founding population is never hit by the
                                           # extra penalty, only a population actually pressing
                                           # on its carrying ceiling is.
DIET_IMBALANCE_MAX_EXTRA_PENALTY = 0.2   # additional multiplicative penalty, fully phased in by
                                           # DIET_IMBALANCE_PRESSURE_RAMP above the threshold --
                                           # deliberately the same magnitude as the flat 0.55
                                           # attempt that failed catastrophically at ALL pressure
                                           # levels (see above); gating it to only fire once
                                           # pressure is already elevated is the actual
                                           # hypothesis under test, not a smaller number. A
                                           # further deepening to 0.2 was drafted but not shipped.
                                           #
                                           # A hard per-tick kcal ceiling on single-category gain
                                           # (SINGLE_CATEGORY_ENERGY_CAP, meant to stop a strong
                                           # forager from just out-harvesting the multiplicative
                                           # penalty in absolute terms) was also tried at 400, then
                                           # recalibrated to 700 after 400 measurably tanked 2 of 3
                                           # local test seeds, and shipped -- then reverted after a
                                           # seed NOT in that 3-seed suite (42, long-used and
                                           # otherwise stable) went fully extinct under it, isolated
                                           # via bisection to be the cap and only the cap (see
                                           # _do_forage's gain calculation for the full postmortem).
                                           # A flat ceiling acts as a persistent tax specifically on
                                           # the population's strongest/most productive foragers --
                                           # their traits.strength is fixed for life, so if their
                                           # typical harvest already exceeds the cap, EVERY
                                           # single-category tick gets clipped, not an occasional
                                           # outlier -- which is exactly backwards, since those
                                           # individuals' surplus is what the rest of the group's
                                           # provisioning economy depends on. Any future version of
                                           # this idea needs to scale with the individual's own
                                           # capability (e.g. relative to their own diverse-diet
                                           # ceiling), not a single population-wide flat number.
DIET_IMBALANCE_PRESSURE_RAMP = 1.0       # pressure units over which the extra penalty phases in
                                           # (linear from 0 at the threshold to full at
                                           # threshold + ramp)

# Mineral resources — non-food, tradeable/raidable goods rather than a caloric energy source.
# Cold-zone-dominant real geology (coal seams, iron-bearing rock, oil deposits concentrate in
# specific formations, not arable temperate/tropical land), discovered through the same
# Experiment pathway as crop/livestock domestication (see `mining` knowledge below).
MINERAL_ARCHETYPES = {
    'coal':     {'zone_weights': {'cold': 3.0, 'temperate': 0.3, 'tropical': 0.0}},
    'iron_ore': {'zone_weights': {'cold': 2.0, 'temperate': 0.4, 'tropical': 0.0}},
    'oil':      {'zone_weights': {'cold': 1.5, 'temperate': 0.2, 'tropical': 0.0}},
}
# Salt (see the dedicated salt-discovery block in _do_forage, separate from the generic
# zone-weighted mineral pick above) -- real evaporite geology concentrates at any standing or
# flowing water, not just one climate band, so this is a location suitability (any water tile),
# not a MINERAL_ARCHETYPES zone-weight entry. The island is a real salt-pan-grade concentration,
# ten times any ordinary water tile elsewhere -- rare but not exclusive, so trade for it is a
# strong incentive without making everyone off the island permanently locked out of ever finding
# their own.
SALT_WATER_SUITABILITY = 0.08
SALT_ISLAND_SUITABILITY = 0.8
MINING_DISCOVERY_CHANCE = 0.0025  # per qualifying forage tick, same order as DOMESTICATION_DISCOVERY_CHANCE
MINING_YIELD_PER_TICK = 1.5       # base quantity added to a miner's stockpile per working tick.
                                     # Raised from 0.8 on direct request: live data showed only
                                     # 45/232 merchants held any resources at all and most
                                     # holdings were tiny (0.1-1.4) -- lowering TRADE_SURPLUS_
                                     # FLOOR alone didn't fix trade frequency in local testing
                                     # because residents rarely accumulate enough stock in the
                                     # first place, so the actual bottleneck is production/
                                     # retention, not the trade-candidate threshold.
CROP_SURPLUS_CONVERSION = 0.05    # kcal-of-excess-harvest -> tradeable crop-resource units.
                                     # Raised from 0.02, same reasoning as above -- this only
                                     # fires once a farmer's energy already exceeds MAX_ENERGY
                                     # (a real, if narrow, well-fed condition), so raising the
                                     # conversion rate makes each occurrence count for more
                                     # without inventing a new, more frequent trigger.
                                     #
                                     # Diagnostic follow-up found this still wasn't the real
                                     # bottleneck: a trade-funnel trace on live data showed 96.5%
                                     # of a population knows crop_cultivation, but only 1.7%
                                     # held any resources at all -- of 741 trade attempts sampled
                                     # over 3000 ticks, 705 (95%) had genuinely empty
                                     # r.resources. The gate itself (pre_cap_energy > MAX_ENERGY)
                                     # is the problem: average population energy runs 900-1300,
                                     # so a single tick's harvest actually exceeding the full
                                     # 3000 energy ceiling is a rare spike, not a routine
                                     # "well-fed" state -- raising the conversion RATE doesn't
                                     # help a trigger that almost never fires.
                                     #
                                     # Two fixes were tried together on direct request: lowering
                                     # this trigger threshold (CROP_SURPLUS_ENERGY_THRESHOLD_
                                     # FRACTION, kept, see below), and giving farming its own
                                     # small unconditional per-tick yield mirroring how mining
                                     # already works (reverted -- see the threshold constant's
                                     # comment for why: it destabilizes the shared global RNG
                                     # stream by flipping most residents' r.resources from empty
                                     # to non-empty, which _maybe_trade's short-circuit check
                                     # treats as a real behavioral change regardless of amount;
                                     # a 10-seed test found real extinctions from this that
                                     # shrinking the per-tick amount 5x did not fix).
CROP_SURPLUS_ENERGY_THRESHOLD_FRACTION = 0.65  # fraction of MAX_ENERGY above which excess
                                     # harvest converts to stockpile -- lowered from requiring
                                     # the full MAX_ENERGY (implicitly 1.0) so this can actually
                                     # fire for a farmer having a good tick, not only an extreme
                                     # outlier one. Verified safe alone across 10 seeds (no
                                     # extinctions) -- unlike the unconditional-yield idea above,
                                     # this only changes how much a farmer gets when the existing
                                     # rare surplus event fires, never whether r.resources exists
                                     # at all for the rest of the population.
RESOURCE_STOCKPILE_DECAY = 0.005  # per-tick fractional decay on held resources (spoilage/
                                     # consumption by others). Halved from 0.01 so whatever a
                                     # resident does accumulate persists long enough to compound
                                     # toward TRADE_SURPLUS_FLOOR instead of eroding away between
                                     # the rare production events above.

# Trade — see _maybe_trade. Opportunistic, individual, probabilistic exchange during an
# ordinary interaction; not a scripted allocation or trade-route algorithm (RFC-0007 Non-Goals).
TRADE_CHANCE = 0.2               # per qualifying interaction
TRADE_SURPLUS_FLOOR = 0.5        # must hold at least this much of a good before considering a gift.
                                    # Lowered from 2.0 on direct request after live data showed
                                    # the real bottleneck on merchant activity: only 45/232 live
                                    # merchants held ANY resources at all, and most of those
                                    # holdings (0.1-1.4) sat below the old 2.0 floor -- crop
                                    # surplus only converts to storable resources in the narrow
                                    # window where a farmer's energy exceeds MAX_ENERGY, and
                                    # RESOURCE_STOCKPILE_DECAY erodes it 1%/tick after that, so
                                    # most residents never accumulated enough to even become a
                                    # trade candidate. This only changes what counts as "worth
                                    # offering" -- doesn't touch any population energy formula.
TRADE_GIFT_FRACTION = 0.25       # fraction of the surplus given away per successful trade

# Merchant profit redistribution (see is_merchant, RFC-0004) — a merchant who completes a real
# two-way barter (their own local surplus for the other party's, see _maybe_trade) earns a
# modest flat kcal margin on top of the physical goods exchanged, representing the practical
# value of matching a local glut against a local shortage -- comparable in size to a scavenge
# yield (observed live: 88-219 kcal), not a windfall. Per the same redistribution-not-
# accumulation stance as chief_standing/FOLLOWER_TRIBUTE_SHARE, the merchant doesn't keep this:
# most goes to a bonded chief-standing ally (identical voluntary-tribute pattern), the rest is
# split among the merchant's own living, bonded children (bonded, not just biological -- a
# merchant only provisions children they're still in contact with, same logic as any other
# bonded transfer in this engine). Both legs count toward the merchant's own
# energy_given_away, so a sufficiently successful merchant can build real chief_standing this
# way -- an emergent merchant-to-chief path, not an authored one. No currency/price object is
# introduced (see RFC-0007 Non-Goals) -- the "price" is just this flat margin plus the existing
# surplus/deficit-gated barter ratio already in _maybe_trade.
MERCHANT_TRADE_PROFIT_KCAL = 120.0
MERCHANT_PROFIT_CHIEF_SHARE = 0.65   # majority to the chief if bonded to one, remainder to children

# Agricultural technology ladder — each tier multiplies the land's energy-density ceiling
# further, mirroring the real historical trajectory (irrigation civilizations, then
# selective breeding of higher-yield varieties over generations, then industrial-era
# fertilizer/pesticides — the "Green Revolution," the single largest jump in yield per
# area in history). A cell's ag_tech_mult ratchets up to the best tier any farmer working
# it has achieved and never decreases — technique embedded in how a plot is worked doesn't
# un-happen, even though the plot's cultivation LEVEL can still lapse if untended.
# Real agricultural-revolution productivity jump (see _do_forage's conversion calculation) --
# raised from a much smaller skill-only bonus (20.0) after instrumented live testing showed the
# population's aggregate energy supply running a genuine, chronic deficit (96.6% of all
# health-loss events came from caloric erosion/death-zone, not disease).
CROP_CULTIVATION_BASE_BONUS = 30.0   # immediate boost just for having adopted farming at all
CROP_CULTIVATION_SKILL_BONUS = 90.0  # additional ceiling at full skill+suitability (was 20.0)
ANIMAL_HUSBANDRY_BASE_BONUS = 20.0   # smaller than farming's -- herding is a real but secondary
                                       # economy alongside cultivation, not the primary lever
ANIMAL_HUSBANDRY_SKILL_BONUS = 45.0  # (was 20.0)
COLD_ZONE_GRAZING_BONUS = 1.5  # nomadic pastoralism: the cold zone is meant to be a genuinely
                                 # thriving herding economy, not just the only zone where
                                 # grazing is viable at all -- see the cold-zone branch of
                                 # _do_forage's husbandry conversion bonus. Raised from an
                                 # initial 1.3 per direct request -- this only scales the
                                 # husbandry-specific ADD-ON term in the conversion formula, not
                                 # the whole forage gain multiplicatively, so it doesn't carry
                                 # the same compounding risk the salt-deficit widening did.
COLD_ZONE_WINTER_HUNT_BONUS = 10.0  # direct request: "哪怕冬季，都可以觅食动物来补充能量" --
                                 # wild game is genuinely still present in the cold zone during
                                 # winter (just sparser than other seasons, see the CLIMATE_ZONES
                                 # winter regrow multiplier, which this does NOT touch), so
                                 # opportunistic winter hunting adds a real conversion bonus for
                                 # anyone foraging in the cold zone in winter -- independent of
                                 # animal_husbandry knowledge (unlike COLD_ZONE_GRAZING_BONUS,
                                 # this is available to a resident who hasn't domesticated
                                 # anything yet, precisely the bootstrapping-phase pioneers this
                                 # is meant to help). Smaller than ANIMAL_HUSBANDRY_BASE_BONUS
                                 # (20.0) -- opportunistic hunting is real but secondary to actual
                                 # domesticated herding, not a replacement for it. Same
                                 # conversion-formula-additive pattern as every other bonus here
                                 # (not a regrow-rate change, not a global change) -- deliberately
                                 # avoids the RNG-divergence chaos class that sank the direct
                                 # winter-regrow attempt earlier this session.
COLD_ZONE_HERDER_MIGRATION_THRESHOLD = 400.0  # see MIGRATE (winter) in decide() -- an
                                 # established cold-zone herder tolerates real hardship (down to
                                 # this much lower energy level) before finally giving up and
                                 # migrating away, instead of the flat 900 threshold that applies
                                 # to everyone else, including a cold-zone resident who hasn't
                                 # domesticated anything and genuinely has nothing keeping them
                                 # there. Targets a specific, previously-untested hypothesis for
                                 # the "spikes then crashes back to zero" pattern every earlier
                                 # cold-zone fix left unresolved: population may be leaving via
                                 # ordinary winter emigration, not dying, so no amount of
                                 # improving survival/reproduction odds fixes a population that
                                 # walks away the moment conditions get merely uncomfortable.
FISHING_BASE_BONUS = 25.0            # between farming's and husbandry's -- a real, secondary
                                       # economy specific to water tiles, richest near the island
FISHING_SKILL_BONUS = 60.0
SALT_FOOD_BONUS_MULT = 1.15  # real historical role: salt is a preservative, not a calorie
                               # source itself (see MINERAL_ARCHETYPES -- minerals stay
                               # non-food/tradeable) -- holding any personally raises the
                               # effective value of food foraged this tick, on top of (not
                               # instead of) dietary diversity.
                               #
                               # A widened version (1.3/0.7, tried and reverted) collapsed the
                               # population in local testing -- births fell behind deaths from
                               # the very first checkpoint (tick 50) and never recovered, down
                               # to 18 residents by tick 800. Even with salt more broadly
                               # discoverable now (any water tile), most of the population still
                               # doesn't hold any at any given moment, so the deficit penalty is
                               # still effectively a near-universal tax, and it stacks
                               # multiplicatively with the diet-diversity multiplier (see
                               # DIET_CATEGORY_MULT, 0.7x for a single food category) and every
                               # other forage multiplier -- 0.7x was enough to tip the population's
                               # already-thin margin into a genuine death spiral. 1.15/0.85 is the
                               # calibrated ceiling until salt prevalence rises substantially
                               # further on its own.
SALT_DEFICIT_MULT = 0.85     # symmetric penalty for holding none -- see the note above. Also
                               # tried widened alone to 0.8 (bonus left at 1.15, isolating it
                               # from the earlier combined 1.3/0.7 attempt) on direct request:
                               # still unsafe -- seed 2 went fully extinct at tick 541, the same
                               # seed that also failed under two separate, unrelated
                               # diet-imbalance tightening attempts (DIET_CATEGORY_MULT[1] at
                               # 0.55 and 0.6) tried the same session. That seed is healthy under
                               # every current baseline value, so this isn't one fragile seed --
                               # it's a real signal that the population's margin for ANY
                               # additional tightening on the "eat well" energy budget is
                               # already thin right now, across multiple independent
                               # multipliers. Reverted; further attempts at a stronger
                               # imbalance penalty via broad forage multipliers should assume
                               # very little headroom exists and verify extensively (more than
                               # 3 seeds) before shipping, or use a different mechanism
                               # entirely rather than tightening an existing near-universal tax.
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
COLD_ZONE_EROSION_MULT = 0.6        # cold-zone-only reduction on both rates above -- this is the
                                      # actual root-cause pathway identified by the original
                                      # cold-zone survival diagnostic: harsh winter upkeep drives
                                      # energy into the erosion/death-zone bands, and THIS direct
                                      # health cost (not disease, which COLD_ZONE_DISEASE_MULT
                                      # already targets) sets the ~80-96-tick ceiling no cold-zone
                                      # resident has ever exceeded regardless of every other fix
                                      # tried (disease suppression, regional pressure, founding
                                      # herders, wider forage radius, horse bonuses). Deliberately
                                      # scoped to cold-zone residents only, same low-blast-radius
                                      # pattern as COLD_ZONE_DISEASE_MULT (a small population
                                      # share) rather than a global HEALTH_EROSION_RATE/
                                      # DEATH_ZONE_RATE change (which would carry the same
                                      # large-population chaos-divergence risk the reverted
                                      # TROPICAL_ZONE_DISEASE_MULT attempt just demonstrated) --
                                      # NOT the same lever as the reverted direct winter-regrow
                                      # attempt either (that changed food production/supply, this
                                      # changes how harshly a given deficit is punished).
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
FIDELITY_IMITATION = 0.15   # floor: watching + instinctive inheritance, no verbal exchange --
                              # lowered from 0.30 so language is a real, visible survival
                              # advantage rather than a mild convenience: live data showed a
                              # population of 2305 with only 7 language holders and 1 writing
                              # holder still reaching ~80-90% adoption of basic survival
                              # knowledge (fire/shelter/clothing) purely through imitation,
                              # which made language nearly irrelevant to outcomes
FIDELITY_ORAL = 0.85        # spoken language: explicit verbal teaching -- raised from 0.60,
                              # widening the imitation/oral gap from 2x to ~5.7x so a
                              # language-holding lineage should visibly out-learn an
                              # imitation-only one instead of language being a cosmetic stat
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
    """Postpartum recovery gate (see POSTPARTUM_RECOVERY_TICKS) plus the female fertility
    ceiling (see FEMALE_FERTILITY_MAX_AGE) -- males have neither a birth-spacing nor an age
    constraint on reproduction, only whoever actually bears the child does."""
    if r.sex != 'female':
        return True
    if r.age > FEMALE_FERTILITY_MAX_AGE:
        return False
    if r.last_birth_tick is None:
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
    near_island: bool = False  # set once in _carve_river -- boosts fishing suitability on
                                 # surrounding water and lets salt (see MINERAL_ARCHETYPES) be
                                 # found here even off mountain/desert terrain, so the island has
                                 # a real non-farming specialty rather than just being good
                                 # farmland like the mainland

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
    'carrying_capacity': 10.0,
}
# Carrying capacity (see Resident.is_merchant, MERCHANT_CAPACITY_THRESHOLD) -- how much
# personal resource stockpile a resident can physically hold at once (see the cap enforced in
# _add_resource), an ordinary heritable trait like strength/speed, not an authored "Merchant"
# role. Its scale (mean 10, occasional individuals well past 50) is a full order of magnitude
# wider than every other trait's ~0.3-1.8 range, so it needs its own mutation stddev
# (CARRYING_CAPACITY_MUTATION) rather than reusing TRAIT_MUTATION -- the same relative
# variability at 10x the scale.
CARRYING_CAPACITY_MUTATION = 6.0
MERCHANT_CAPACITY_THRESHOLD = 40.0  # ~4x the species mean -- rare, matching gifted_scout's
                                      # rough occurrence rate, not guaranteed at birth


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
    carrying_capacity: float = 10.0  # see MERCHANT_CAPACITY_THRESHOLD/is_merchant -- how much
                                       # personal resource stockpile this resident can carry

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
            carrying_capacity=random.uniform(8.0, 12.0),
        )

    def mutate(self, scale=1.0):
        def m(v, lo, hi):
            return max(lo, min(hi, v + random.gauss(0, TRAIT_MUTATION * scale)))
        def m_capacity(v):
            return max(5.0, min(150.0, v + random.gauss(0, CARRYING_CAPACITY_MUTATION * scale)))
        return Traits(
            strength=m(self.strength, 0.3, 1.8),
            speed=m(self.speed, 0.3, 1.8),
            perception=m(self.perception, 0.3, 1.8),
            endurance=m(self.endurance, 0.3, 1.8),
            sociability=m(self.sociability, 0.0, 1.0),
            risk_tolerance=m(self.risk_tolerance, 0.0, 1.0),
            immunity=m(self.immunity, 0.0, 1.0),
            intelligence=m(self.intelligence, 0.3, 1.8),
            carrying_capacity=m_capacity(self.carrying_capacity),
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
            carrying_capacity=regress((self.carrying_capacity + other.carrying_capacity) / 2, TRAIT_MEANS['carrying_capacity']),
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
    recent_food_types: dict = field(default_factory=dict)  # food_type -> last tick eaten (see
                                        # DIET_DIVERSITY_* and _do_forage) -- bounded by
                                        # construction to the fixed vocabulary of food types
                                        # (crop/livestock archetypes + 'wild'/'fish'), so unlike
                                        # self.residents this can never grow unboundedly
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
    scout_target: Optional[tuple] = None  # (x, y) of the best distant land a gifted scout has
                                            # found (see is_gifted_scout, FISSION in decide()) --
                                            # bonded followers migrate toward the same target
                                            # instead of each independently random-sampling
    coerced_by: Optional[int] = None  # id of whoever is forcibly extracting this resident's
                                        # labor (see COERCION_* constants, _do_raid, and the
                                        # forage-tribute block in Simulation._tick) -- not a
                                        # status/class, just who this individual's surplus is
                                        # currently, involuntarily, flowing to
    # Cumulative inbreeding load (0.0 = fresh outside genetics, higher = generations of
    # within-lineage mating) -- NOT reset by an unrelated pairing, but DILUTED by one, since a
    # child's load is the average of both parents' plus whatever the immediate pairing itself
    # added (see _spawn). This is what lets population quality degrade gradually under sustained
    # isolation (real inbreeding depression compounding across generations) while a genuine
    # outcross with a low-load partner (fresh genetic diversity, e.g. from another founding
    # cluster) measurably improves the next generation -- hybrid vigor/heterosis, not just a
    # return to baseline. See INBREEDING_LOAD_ACCUMULATION and Traits.blend.
    inbreeding_load: float = 0.0
    # Horse's own energy pool (see HORSE_ENERGY_MAX etc.) -- -1.0 sentinel means "not yet
    # initialized"; set to HORSE_ENERGY_MAX the first tick _has_horse(r) is true (see
    # Simulation._tick), which naturally covers both fresh invention and hereditary/taught
    # acquisition without needing to touch every acquisition call site individually.
    horse_energy: float = -1.0

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

    def is_gifted_scout(self):
        """Rare individuals whose intelligence, perception, strength, AND speed all happen to
        be exceptional simultaneously -- a pure readout over the existing continuous trait
        system (RFC-0004: emergence from combinations of simpler traits, not a new hardcoded
        'leadership' category). They see farther (see decide()'s cell-scan radius) and can lead
        bonded followers to a distant target they alone found (see FISSION/scout_target)."""
        t = self.traits
        return (t.intelligence > GIFTED_SCOUT_TRAIT_THRESHOLD and t.perception > GIFTED_SCOUT_TRAIT_THRESHOLD
                and t.strength > GIFTED_SCOUT_TRAIT_THRESHOLD and t.speed > GIFTED_SCOUT_TRAIT_THRESHOLD)

    def is_merchant(self):
        """Rare individuals born with a much larger carrying_capacity than the species mean --
        a pure readout over one continuous trait (RFC-0004: not a hardcoded 'Merchant' role).
        Can physically hold a much larger personal resource stockpile (see _add_resource) and
        see farther (see decide()'s cell-scan radius), matching real long-distance traders'
        actual advantages (pack capacity, route knowledge) rather than granting anything not
        derived from their own traits."""
        return self.traits.carrying_capacity > MERCHANT_CAPACITY_THRESHOLD


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

    # near_island marking (see Cell.near_island, ISLAND_FISH_RADIUS, TERRAIN_FISHING) -- a
    # simple bounding-box check, not exact distance, since this only needs to identify "close
    # enough to the island to fish/gather salt here," not a precise radius.
    for y in range(max(0, island_cy - ISLAND_FISH_RADIUS), min(GRID_H, island_cy + ISLAND_FISH_RADIUS + 1)):
        for x in range(max(0, island_cx - ISLAND_FISH_RADIUS), min(GRID_W, island_cx + ISLAND_FISH_RADIUS + 1)):
            if (x - island_cx) ** 2 + (y - island_cy) ** 2 <= ISLAND_FISH_RADIUS ** 2:
                grid[y][x].near_island = True


# ── Snapshot serialization (see SNAPSHOT_PATH) ──
# Plain dataclasses.asdict() round-trips fine for saving (it recurses through nested
# dataclasses/dicts/lists automatically), but loading needs explicit reconstruction: JSON has
# no tuple type (scout_target) and always stringifies dict keys (bonds is keyed by int
# resident id). Field lists are filtered against the CURRENT dataclass shape in both
# directions so a snapshot survives the schema changing between save and load (a stale extra
# key is dropped, a newly-added field just takes its dataclass default) -- this project's
# fields change most sessions, unlike a stable save-file format.

def _cell_to_dict(c):
    return asdict(c)


def _cell_from_dict(d):
    valid = {f.name for f in fields(Cell)}
    return Cell(**{k: v for k, v in d.items() if k in valid})


def _resident_to_dict(r):
    return asdict(r)


def _resident_from_dict(d):
    valid = {f.name for f in fields(Resident)}
    d = {k: v for k, v in d.items() if k in valid}
    trait_valid = {f.name for f in fields(Traits)}
    d['traits'] = Traits(**{k: v for k, v in d['traits'].items() if k in trait_valid})
    d['memory'] = [MemEntry(**m) for m in d.get('memory', [])]
    d['bonds'] = {int(k): Bond(**v) for k, v in d.get('bonds', {}).items()}
    if d.get('scout_target') is not None:
        d['scout_target'] = tuple(d['scout_target'])
    return Resident(**d)


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
            child_inbreeding_load = min(INBREEDING_LOAD_CAP,
                                         (parent.inbreeding_load + partner.inbreeding_load) / 2
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
    # Iterate the Manhattan-distance diamond directly (dx bounded by r-abs(dy)) instead of a
    # full (2r+1)^2 square filtered after the fact -- the square wastes ~40% of iterations on
    # cells outside the diamond for large r, and this was profiled as the single largest
    # per-tick cost once population grew large (see PERCEPTION_CELL_CAP).
    cells = []
    y_lo, y_hi = max(0, y - r), min(GRID_H - 1, y + r)
    for ny in range(y_lo, y_hi + 1):
        dy_abs = abs(ny - y)
        max_dx = r - dy_abs
        x_lo, x_hi = max(0, x - max_dx), min(GRID_W - 1, x + max_dx)
        row = grid[ny]
        for nx in range(x_lo, x_hi + 1):
            cells.append((row[nx], dy_abs + abs(nx - x)))
    return cells


RESIDENT_BUCKET_SIZE = 20  # see _tick's resident_buckets construction and _nearby_residents


def _nearby_residents(x, y, r, residents, buckets=None):
    """`buckets` (built once per tick, see Simulation._tick) turns this from an O(n) linear
    scan into an O(k) lookup where k is local density, not total population -- decide() calls
    this once per living resident every tick, so the unbucketed version was O(n^2) in aggregate
    per tick, which became the dominant cost once population grew into the many hundreds (the
    same bug class as the earlier O(n) 'cluster' metric fix, but on a much hotter path). Falls
    back to the old linear scan when no bucket index is supplied (e.g. one-off callers)."""
    if buckets is not None:
        bx, by = x // RESIDENT_BUCKET_SIZE, y // RESIDENT_BUCKET_SIZE
        span = r // RESIDENT_BUCKET_SIZE + 1
        result = []
        for dbx in range(-span, span + 1):
            for dby in range(-span, span + 1):
                for res in buckets.get((bx + dbx, by + dby), ()):
                    dist = abs(res.x - x) + abs(res.y - y)
                    if 0 < dist <= r:
                        result.append((res, dist))
        return result
    return [(res, abs(res.x-x)+abs(res.y-y))
            for res in residents
            if res.alive and 0 < abs(res.x-x)+abs(res.y-y) <= r]


def _find_fission_target(r, grid, search_radius=FISSION_SEARCH_RADIUS):
    """Pick a far-away, viable relocation target for band fission (see FISSION in decide()) --
    cheap sampling, not a population-density scan (O(1) probes x O(radius^2) cell check each,
    independent of population size). Biases toward unclaimed high-biomass terrain: a handful of
    random long-distance probe points are sampled, then the best-biomass passable cell found
    near any of them wins -- no attempt to compute true population density at range, which
    would require an O(n) or worse scan over all residents; this mirrors the same locality-only
    perception model _nearby_cells already uses everywhere else. `search_radius` is wider for
    gifted scouts (see GIFTED_SCOUT_SEARCH_RADIUS) -- their exceptional perception finds a
    genuinely better target than an ordinary resident's default search."""
    best_cell, best_score = None, -1
    for _ in range(5):
        angle = random.uniform(0, 2 * math.pi)
        dist = random.uniform(FISSION_MIN_DISTANCE, FISSION_MIN_DISTANCE + 15)
        px = int(r.x + math.cos(angle) * dist)
        py = int(r.y + math.sin(angle) * dist)
        px = max(0, min(GRID_W - 1, px))
        py = max(0, min(GRID_H - 1, py))
        for c, d in _nearby_cells(px, py, search_radius, grid):
            if c.passable() and c.biomass_cap > best_score:
                best_cell, best_score = c, c.biomass_cap
    return best_cell


def _capability(r):
    """Simple combined capability readout (intelligence+perception+strength+speed) -- a pure
    function of existing continuous traits, used to let ordinary residents gravitate toward
    bonded individuals who are meaningfully more capable providers (see FOLLOW STRONGER in
    decide()), not a new hardcoded trait."""
    t = r.traits
    return t.intelligence + t.perception + t.strength + t.speed


def _has_horse(r):
    return r.known_knowledge.get('animal_husbandry', {}).get('crop_type') == 'horse'


def _horse_bonus_scale(r):
    """0..1 scale from the horse's own energy pool (see HORSE_ENERGY_* and the per-tick update
    in Simulation._tick) -- 1.0 while the horse is well-maintained (energy at or above
    HORSE_ENERGY_DEGRADE_THRESHOLD), fading linearly toward 0.0 (no bonus, never a penalty
    below the pedestrian baseline) as the horse's energy runs out from too much non-cold-zone
    travel. Only feeds the three multipliers the user explicitly named as degrading (carry,
    speed, combat) -- HORSE_MOVE_COST_NEAR_ZERO and HORSE_PERCEPTION_MULT are unaffected."""
    if r.horse_energy < 0:
        return 1.0  # not yet initialized this tick (first tick with a horse) -- treat as full
    return max(0.0, min(1.0, r.horse_energy / HORSE_ENERGY_DEGRADE_THRESHOLD))


def _horse_mult(r, base_mult):
    """base_mult tapered toward 1.0 (no bonus) by _horse_bonus_scale, for horse-owners only."""
    if not _has_horse(r):
        return 1.0
    scale = _horse_bonus_scale(r)
    return 1.0 + (base_mult - 1.0) * scale


def _combat_capability(r):
    """_capability scaled by HORSE_COMBAT_MULT (tapered by the horse's own energy -- see
    _horse_mult) for horse-owners -- a mounted raider/defender is a real martial advantage
    (steppe cavalry precedent). Used only at the raid power-ratio comparisons below, never at
    FOLLOW STRONGER's plain capability comparison (that's about general provider quality, not
    combat)."""
    return _capability(r) * _horse_mult(r, HORSE_COMBAT_MULT)


def _is_outsider(r, res, group_root):
    """True if `res` should read as a genuine outsider for raid-desire purposes -- prefers real
    detected group membership (group_root, the per-resident union-find root from Simulation._tick,
    same pass that produces the group_count metric) over the cruder bond+relatedness proxy alone.
    Fission splits a population into real, distinct communities (RFC-0007), but two members of
    the SAME post-split community who simply haven't personally interacted yet would previously
    still read as mutual "strangers" under the pairwise-only check, which is exactly backwards --
    they're one of us, just not personally met. group_root fixes that: raid desire should track
    genuine outgroup status, not just "have we personally bonded." Falls back to the old
    bond+relatedness proxy when group data isn't available yet (very first tick) or a resident
    fell outside the last union-find pass (newly born since, or the pass hasn't run yet)."""
    if group_root and r.id in group_root and res.id in group_root:
        return group_root[r.id] != group_root[res.id]
    return (res.id not in r.bonds or r.bonds[res.id].quality <= 0) and _relatedness(r, res) < 0.25


def _add_resource(r, good, amount):
    """Adds to a resident's resource stockpile respecting their carrying_capacity (see
    Resident.is_merchant) -- total goods held (summed across every type) can't exceed what they
    can physically carry. Silently caps rather than rejecting outright (a farmer whose harvest
    exceeds capacity keeps what fits, not nothing) and returns the amount actually added, so
    callers that also deduct from a source (trade, raiding) only remove what really moved.

    A horse owner's effective ceiling is multiplied by HORSE_CARRY_MULT (direct request,
    "携带能力提高五倍"), tapered by the horse's own energy (see _horse_mult) -- a mount carries
    far more than a person alone, but a spent horse carries no more than a person."""
    if amount <= 0:
        return 0.0
    cap = r.traits.carrying_capacity * _horse_mult(r, HORSE_CARRY_MULT)
    total_held = sum(r.resources.values())
    room = max(0.0, cap - total_held)
    added = min(amount, room)
    if added > 0:
        r.resources[good] = r.resources.get(good, 0.0) + added
    return added


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


def _step_toward(rx, ry, tx, ty, grid, steps=1):
    """One or more tile-steps toward (tx, ty), stopping at the first impassable tile or once the
    target is reached, whichever comes first -- still returns a SINGLE ('move', ...) action to
    the farthest reachable tile (see _do_move, which charges cost/hazard once for that
    destination regardless of how many tiles were covered). `steps` > 1 is the horse-owner speed
    boost (HORSE_SPEED_MULT, direct request "移动速度增加20倍") -- every other caller passes the
    default of 1, unchanged from before this existed."""
    dx = max(-1, min(1, tx - rx))
    dy = max(-1, min(1, ty - ry))
    if dx == 0 and dy == 0:
        return ('rest', None, None, None)
    cx, cy = rx, ry
    for _ in range(steps):
        nx, ny = cx + dx, cy + dy
        if not (0 <= nx < GRID_W and 0 <= ny < GRID_H and grid[ny][nx].passable()):
            break
        cx, cy = nx, ny
        if (cx, cy) == (tx, ty):
            break
    if (cx, cy) == (rx, ry):
        return ('rest', None, None, None)
    return ('move', cx, cy, None)


def decide(r, grid, residents, tick, pressure=0.0, buckets=None, group_root=None, zone_pressure=None):
    radius = r.view_radius() + int(r.traits.sociability * 2)
    # _nearby_cells is O(radius^2) (a grid-cell bounding-box scan, not bucketable the same way
    # as residents) -- view_radius() can reach 60-65 at high perception/sociability, making a
    # single call ~17,000 cell checks; called once per living resident every tick, this became
    # the dominant per-tick cost once population grew into the many hundreds (profiled: ~70% of
    # total tick time). Real "nearby, worth walking to for food" doesn't need a 65-tile scan --
    # capped well below the full social/resident perception radius, which is unaffected.
    # Gifted scouts (see is_gifted_scout) get a genuinely larger scan radius, reflecting
    # exceptional perception/intelligence -- rare enough (all four traits must simultaneously
    # exceed GIFTED_SCOUT_TRAIT_THRESHOLD) that this doesn't reintroduce the perf problem
    # PERCEPTION_CELL_CAP fixed for the general population.
    has_horse = _has_horse(r)
    # HORSE_PERCEPTION_MULT (direct request "感知的范围扩大10倍") supersedes the flat
    # HORSE_FORAGE_CELL_CAP for the terrain/food cell scan -- 10x the ordinary
    # PERCEPTION_CELL_CAP baseline, not 10x the already cold-zone-boosted value, so this stays
    # the same order of magnitude as GIFTED_SCOUT_CELL_CAP/MERCHANT_CELL_CAP rather than
    # compounding two multipliers. Deliberately NOT applied to `radius` below (the resident-
    # detection radius near_res uses) -- radius already reaches 60-65 at high perception/
    # sociability, and a further 10x there would make near_res's candidate pool span nearly the
    # whole map for a horse owner, a much larger behavioral and performance risk than widening
    # the terrain scan; HORSE_RAID_RANGE remains the tested, bounded lever for "how far can a
    # horse owner reach other residents."
    scout_cap = GIFTED_SCOUT_CELL_CAP if r.is_gifted_scout() else (
        MERCHANT_CELL_CAP if r.is_merchant() else (
            PERCEPTION_CELL_CAP * HORSE_PERCEPTION_MULT if has_horse else (
                COLD_ZONE_FORAGE_CELL_CAP if climate_zone(r.y) == 'cold' else PERCEPTION_CELL_CAP)))
    cell_radius = min(radius, scout_cap)
    cells = _nearby_cells(r.x, r.y, cell_radius, grid)
    near_res = _nearby_residents(r.x, r.y, radius, residents, buckets)
    here = grid[r.y][r.x]
    horse_steps = max(1, round(_horse_mult(r, HORSE_SPEED_MULT)))  # direct request "移动速度
                                    # 增加20倍" -- see _step_toward's steps parameter; tapered by
                                    # the horse's own energy via _horse_mult (a spent horse
                                    # covers 1 tile like anyone else)

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
            return _step_toward(r.x, r.y, target_cell.x, target_cell.y, grid, horse_steps)

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
            strangers = [(res, d) for res, d in adjacent if _is_outsider(r, res, group_root)]
            # Below extreme pressure, prefer seizing from strangers over one's own
            # established relationships or kin; only true crisis (pressure >= 2.0) erodes that
            # Raise pressure threshold for raiding relatives (kin discount per Hamilton's rule)
            pool = strangers if (strangers and pressure < 1.5) else adjacent
            if pool is adjacent:
                # Even among all adjacent, prefer lower-relatedness targets when pressure is moderate
                pool.sort(key=lambda x: _relatedness(r, x[0]))
            target = max(pool, key=lambda x: x[0].energy)[0]
            return ('raid', None, None, target.id)

    # OPPORTUNISTIC RAID: see OPPORTUNISTIC_RAID_* constants -- a second, independent raid
    # trigger for a comfortable, physically stronger resident against a weaker nearby stranger,
    # separate from the desperation valve above (which needs real local scarcity to fire at all
    # and, empirically, almost never does once a population is well-fed).
    if r.energy > OPPORTUNISTIC_RAID_ENERGY_MIN:
        strangers_adjacent = [(res, d) for res, d in near_res
                               if d <= 1 and res.energy > 900 and _is_outsider(r, res, group_root)]
        if strangers_adjacent:
            # Chiefly rivalry: chief_standing is a scarce, contested status (see
            # FOLLOWER_TRIBUTE_SHARE) -- a chief targets a rival chief among the candidates
            # first when one is present, rather than treating every stranger as interchangeable
            # prey. Real Big Man societies show genuine rivalry between competing leaders, not
            # peaceful indifference; this reuses the existing raid resolution, no new duel
            # mechanic or authored rivalry object.
            rival_chiefs = ([(res, d) for res, d in strangers_adjacent if res.has_chief_standing()]
                             if r.has_chief_standing() else [])
            candidate = max(rival_chiefs or strangers_adjacent, key=lambda x: x[0].energy)[0]
            # Payoff gap: raiding is more attractive the more a target has relative to what this
            # resident already holds -- a rough steal-vs-forage comparison, on top of the real
            # asymmetry _do_raid already has (a raid skips the caloric effort cost _do_forage
            # pays for the same energy). Scales the trigger CHANCE, not just which target gets
            # picked once triggered. Capped at 2x so an enormous gap doesn't make raiding a
            # near-certainty every qualifying tick.
            payoff_ratio = min(2.0, candidate.energy / max(1.0, r.energy))
            if random.random() < OPPORTUNISTIC_RAID_CHANCE * r.traits.risk_tolerance * payoff_ratio:
                if _combat_capability(r) > _combat_capability(candidate) * OPPORTUNISTIC_RAID_POWER_RATIO:
                    return ('raid', None, None, candidate.id)

    # TERRITORIAL DEFENSE: a chief treats a resource-competing stranger's mere presence
    # (farming/herding right next to them, not trading) as a real grievance -- waiting for a
    # decisive capability edge before acting (like ordinary OPPORTUNISTIC RAID above) isn't how
    # a resource-defending Big Man actually behaves, so this uses a real but lower bar
    # (TERRITORIAL_DEFENSE_POWER_RATIO). Still requires adjacency (raid resolution needs it
    # anyway) and still resolves through the same win/loss _do_raid mechanics as every other
    # raid -- a chief with territorial motive isn't guaranteed to win, just more willing to try.
    if r.has_chief_standing() and r.energy > OPPORTUNISTIC_RAID_ENERGY_MIN:
        resource_rivals = [(res, d) for res, d in near_res
                            if d <= 1 and res.energy > 500 and _is_outsider(r, res, group_root)
                            and ('crop_cultivation' in res.known_knowledge or 'animal_husbandry' in res.known_knowledge)]
        if resource_rivals and random.random() < TERRITORIAL_DEFENSE_CHANCE:
            target = max(resource_rivals, key=lambda x: x[0].energy)[0]
            if _combat_capability(r) > _combat_capability(target) * TERRITORIAL_DEFENSE_POWER_RATIO:
                return ('raid', None, None, target.id)

    # NOMADIC WINTER RAID: a real historical pattern (steppe pastoralists raiding agricultural
    # settlements during harsh winters -- Mongol/Hunnic/Scythian incursions are the textbook
    # examples) falls directly out of existing mechanics with no new "raiding party" object.
    # animal_husbandry is now cold-zone-exclusive (see CLIMATE_ZONES), so knowing it alone
    # proves pastoral origin; MIGRATE (winter) below already moves energy-stressed cold-zone
    # residents toward warmer zones every winter. A pastoralist who's already comfortable
    # enough not to need that migration (energy > 900) but is still out in non-cold territory
    # during winter raids a nearby outsider more readily than the ordinary opportunistic case --
    # when many individually-migrating herders share this same disposition and reach the same
    # farmland in the same winter, the AGGREGATE reads as a coordinated raiding wave, but
    # nothing here actually coordinates them (RFC-0007: no scripted war, no Group object).
    if ('animal_husbandry' in r.known_knowledge and season == 'winter'
            and climate_zone(r.y) != 'cold' and r.energy > 900):
        winter_raid_targets = [(res, d) for res, d in near_res
                                if d <= 1 and res.energy > 500 and _is_outsider(r, res, group_root)]
        if winter_raid_targets and random.random() < NOMADIC_WINTER_RAID_CHANCE:
            target = max(winter_raid_targets, key=lambda x: x[0].energy)[0]
            if _combat_capability(r) > _combat_capability(target) * NOMADIC_WINTER_RAID_POWER_RATIO:
                return ('raid', None, None, target.id)
        elif r.known_knowledge['animal_husbandry'].get('crop_type') == 'horse':
            reachable = [(res, d) for res, d in near_res
                         if 1 < d <= HORSE_RAID_RANGE and res.energy > 500
                         and _is_outsider(r, res, group_root)]
            if reachable:
                target = min(reachable, key=lambda x: x[1])[0]
                return _step_toward(r.x, r.y, target.x, target.y, grid, horse_steps)

    # MIGRATE (winter): move to a warmer zone when the cold itself is the acute threat. An
    # established cold-zone herder (already knows animal_husbandry) tolerates real hardship
    # before giving up and leaving -- abandoning a herd/land they've already invested in is a
    # bigger decision than an ordinary forager with nothing to lose relocating, so they use a
    # much lower trigger threshold (COLD_ZONE_HERDER_MIGRATION_THRESHOLD) than everyone else's
    # flat 900. This directly targets a real, previously-unexamined hypothesis for the cold
    # zone's persistent "spikes then crashes back to zero" pattern: the crash may be substantially
    # driven by residents successfully SURVIVING winter but still emigrating anyway (this
    # unconditional 900 threshold applied to husbandry-holders too, with no distinction from an
    # ordinary wanderer), not by outright death -- every fix so far targeted survival/reproduction
    # odds, none touched whether an established herder actually stays once conditions ease.
    herder_migration_threshold = (COLD_ZONE_HERDER_MIGRATION_THRESHOLD
                                   if climate_zone(r.y) == 'cold' and 'animal_husbandry' in r.known_knowledge
                                   else 900)
    if r.energy < herder_migration_threshold and season == 'winter' and climate_zone(r.y) != 'tropical':
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
            wide_cells = _nearby_cells(r.x, r.y, cell_radius + 4, grid)
            far_candidates = [(c, d) for c, d in wide_cells if d > radius and c.biomass > 15]
            if far_candidates:
                target_cell = max(far_candidates, key=lambda x: x[0].biomass)[0]
                return _step_toward(r.x, r.y, target_cell.x, target_cell.y, grid, horse_steps)

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
        wide_scarce = not any(d > radius and c.biomass > 15 for c, d in _nearby_cells(r.x, r.y, cell_radius + 4, grid))
        if local_scarce and not raidable_nearby and wide_scarce and random.random() < FISSION_CHANCE:
            # Gifted scouts (see is_gifted_scout) search wider and mark what they find so
            # bonded followers migrate toward the SAME destination instead of each
            # independently random-sampling their own direction -- an emergent, trait-driven
            # form of leadership (RFC-0004: must emerge from combinations of simpler traits,
            # not be a hardcoded category) rather than an authored "Leader" role or a scripted
            # migration event. Only a real bond matters here, not merely proximity to a scout.
            followed_target = None
            if not r.is_gifted_scout():
                for res, d in near_res:
                    if res.id in r.bonds and res.scout_target is not None:
                        followed_target = res.scout_target
                        break
            if followed_target:
                return _step_toward(r.x, r.y, followed_target[0], followed_target[1], grid, horse_steps)
            search_radius = GIFTED_SCOUT_SEARCH_RADIUS if r.is_gifted_scout() else FISSION_SEARCH_RADIUS
            target_cell = _find_fission_target(r, grid, search_radius)
            if target_cell:
                if r.is_gifted_scout():
                    r.scout_target = (target_cell.x, target_cell.y)
                return _step_toward(r.x, r.y, target_cell.x, target_cell.y, grid, horse_steps)

    # TERRITORIAL RETREAT was attempted here (Hawk-Dove/Bourgeois asymmetric-contest framing --
    # individually flee a local area once nearby unbonded strangers are decisively stronger than
    # one's own bonded allies) and reverted. Across four parameter passes -- including a
    # same-social-circle stranger filter and a real destination search via
    # _find_retreat_target, not a blind flee-direction step -- local 800-tick testing kept
    # producing a real population decline toward near-extinction (e.g. 910 -> 28 with the most
    # conservative thresholds tried) and avg_inbreeding_load climbing toward its cap instead of
    # the intended effect of encouraging healthier outcrossing. This wasn't a simple
    # too-trigger-happy problem fixable by raising thresholds -- something about adding a fourth
    # competing reason to relocate (on top of MIGRATE general/winter and FISSION) structurally
    # destabilized the population/reproduction economy, and needs a different design, not more
    # parameter tuning, before it's tried again.

    # DANGER SENSING: gifted scouts (see is_gifted_scout) can spot a real raid threat before
    # it happens -- a nearby stranger with high risk_tolerance and no/weak bond, within
    # striking range -- and flee it, rather than every resident only reacting to a raid after
    # being hit. Bonded kin near a scout benefit from the same warning (real, if imperfect,
    # threat perception, not authored combat AI or a scripted "danger" object). Outranks
    # routine activity but not acute hunger -- fleeing on an empty stomach isn't survivable
    # either.
    if r.energy >= 1200 and (r.is_gifted_scout()
            or any(res.id in r.bonds and res.is_gifted_scout() for res, d in near_res)):
        threats = [(res, d) for res, d in near_res
                   if d <= GIFTED_SCOUT_DANGER_SENSE_RADIUS
                   and res.traits.risk_tolerance > 0.6
                   and (res.id not in r.bonds or r.bonds[res.id].quality < REPRODUCTION_BOND_THRESHOLD)]
        if threats:
            threat = min(threats, key=lambda x: x[1])[0]
            flee_x = r.x + (r.x - threat.x)
            flee_y = r.y + (r.y - threat.y)
            return _step_toward(r.x, r.y, flee_x, flee_y, grid, horse_steps)

    # CRITICAL / HUNGRY: find food
    if r.energy < 1200:
        if here.biomass > 3:
            return ('forage', None, None, None)
        best = _best_food(cells)
        if best:
            return _step_toward(r.x, r.y, best.x, best.y, grid, horse_steps)
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
        # A cold-zone resident's own fertility uses their zone's own pressure (see
        # Simulation._zone_pressure, COLD_ZONE_EROSION_MULT's comment) instead of the global
        # self._pressure -- otherwise a nearly-empty cold zone's residents had their
        # reproduction chance suppressed by temperate/tropical crowding they have nothing to
        # do with, the same class of unfairness already fixed for calorie-erosion/disease.
        # Scoped to cold only, same low-blast-radius pattern as those fixes (not extended to
        # temperate/tropical, where the earlier all-zones regional-pressure attempt caused real
        # extinctions from exposing those zones to their own, often-higher, local pressure).
        fertility_pressure = (zone_pressure['cold'] if zone_pressure and climate_zone(r.y) == 'cold'
                               else pressure)
        fertility = max(0.0, 1.0 - (fertility_pressure - 1.0) * 0.5)
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
                #
                # An earlier version boosted this chance by inbreeding_load and preferred the
                # lowest-inbreeding_load candidate over the nearest one within the pool (chasing
                # the best heterosis payoff, not just any unrelated partner). Reverted: local
                # testing showed the same failure pattern as the territorial-retreat attempt --
                # re-evaluated fresh every tick with no persistent target, residents kept
                # re-targeting a possibly-different "best" distant candidate each tick, rarely
                # closing the distance and reproducing, and rarely foraging either. Real
                # population decline (933 -> 35 over 800 ticks) resulted. Nearest-candidate
                # selection, unconditionally, is what's actually stable.
                exogamy_pool = _nearby_residents(r.x, r.y, radius * 2, residents, buckets)
                partners = [(res, d) for res, d in exogamy_pool
                            if res.energy > REPRODUCTION_ENERGY and res.age > REPRODUCTION_AGE
                            and res.sex != r.sex
                            and _is_fertile(res, tick)
                            and (not INCEST_AVOIDANCE_ENABLED or _relatedness(r, res) < INCEST_RELATEDNESS_THRESHOLD)]
            else:
                partners = []
            if partners:
                # Mate choice concentrating on higher-status partners is a legitimate emergent
                # pattern (RFC-0011: "high-status male reproductive concentration"), not a
                # privilege the engine grants -- chief_standing is itself a pure readout over
                # each individual's own redistribution history. Only applied among candidates
                # already adjacent (reproducible THIS tick), never as a reason to travel toward
                # a distant "better" candidate re-picked fresh every tick -- that exact pattern
                # (chasing a possibly-different target each tick, never closing the distance)
                # is what collapsed the earlier reverted inbreeding-aware exogamy attempt.
                adjacent_partners = [(res, d) for res, d in partners if d <= 1]
                if adjacent_partners:
                    p = max(adjacent_partners, key=lambda x: x[0].chief_standing())[0]
                    return ('reproduce', None, None, p.id)
                p = min(partners, key=lambda x: x[1])[0]
                return _step_toward(r.x, r.y, p.x, p.y, grid, horse_steps)

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
            return _step_toward(r.x, r.y, mate.x, mate.y, grid, horse_steps)

    # FOLLOW STRONGER: an ordinary resident gravitates toward a bonded provider who is
    # meaningfully more capable (see _capability) than themselves -- proximity to a strong
    # forager/hunter is what actually lets the existing food-share/provisioning mechanics
    # (_do_interact) kick in, so real ability differences translate into real group cohesion
    # rather than an authored "follower" role (RFC-0004: emergent from existing traits/bonds).
    if r.energy > 1200 and near_res:
        stronger = [(res, d) for res, d in near_res
                    if res.id in r.bonds and _capability(res) > _capability(r) + CAPABILITY_FOLLOW_MARGIN]
        if stronger:
            leader = max(stronger, key=lambda x: _capability(x[0]))[0]
            if abs(leader.x - r.x) + abs(leader.y - r.y) > 1:
                return _step_toward(r.x, r.y, leader.x, leader.y, grid, horse_steps)

    # MERCHANT SEEK CHIEF (see is_merchant, RFC-0004): a merchant bonded to a chief-standing
    # ally travels toward them specifically rather than wandering for a random stranger. Real
    # settlements' economic activity concentrates where the local leader already is -- their
    # followers already gravitate there via FOLLOW STRONGER above, so a chief is a natural,
    # already-known hub of exactly the surplus/scarcity pattern a merchant needs, echoing the
    # Sahlins Big Man redistribution role chief_standing is already modeled on. Deliberately
    # reuses FOLLOW STRONGER's exact safety property: the target is an EXISTING bond, not a
    # freshly-detected stranger, so this never hits the persistent-re-targeting failure mode
    # that collapsed the territorial-retreat/exogamy attempts (see Hierarchies, RFC-0007) --
    # the same chief tends to get picked tick after tick because the bond itself is stable, not
    # because of any stored/committed target field. Once adjacent, interacts with the chief
    # directly (not left to the generic SOCIAL block's random pick) so the trip actually
    # resolves into the encounter it was for.
    if r.is_merchant() and r.energy > 1200 and near_res:
        known_chiefs = [(res, d) for res, d in near_res
                         if res.id in r.bonds and res.has_chief_standing()]
        if known_chiefs:
            chief = min(known_chiefs, key=lambda x: x[1])[0]
            if abs(chief.x - r.x) + abs(chief.y - r.y) <= 1:
                return ('interact', None, None, chief.id)
            return _step_toward(r.x, r.y, chief.x, chief.y, grid, horse_steps)

    # SOCIAL — prefer approaching someone already familiar (bonded or kin) over a genuine
    # stranger, mirroring real intergroup wariness: repeated trust builds within an existing
    # circle, contact with true outsiders stays comparatively rare (see RAID/_maybe_trade for
    # where outsider contact actually resolves — as conflict or exchange, not casual bonding).
    # A monotonous recent diet (see DIET_DIVERSITY_* / recent_food_types) is a second, independent
    # reason to actually seek a stranger out here rather than default to someone familiar --
    # otherwise nothing in this engine gives a well-fed-but-undiversified resident (pressure <=
    # 1.0, so this block wouldn't even fire before) any reason to risk a stranger, and
    # _maybe_trade's cross-region exchange (e.g. island salt for mainland grain) never gets a
    # chance to happen at all. Still only ever acts on someone already in near_res -- no
    # traveling toward a distant stranger, which is what made the reverted territorial-retreat/
    # exogamy attempts unstable.
    low_diversity = len({FOOD_CATEGORY.get(t, 'wild') for t, last in r.recent_food_types.items()
                          if tick - last <= DIET_DIVERSITY_WINDOW}) <= 1
    # Merchants (see Resident.is_merchant) approach strangers for the same reason as low
    # diversity above -- they're the ones with something worth trading and the carrying
    # capacity to move it (see _add_resource/_maybe_trade) -- independent of pressure/diet.
    is_merchant = r.is_merchant()
    if r.traits.sociability > 0.5 and near_res and (pressure > 1.0 or low_diversity or is_merchant) and random.random() < 0.5:
        strangers = [res for res, d in near_res if res.id not in r.bonds and _relatedness(r, res) == 0]
        if (low_diversity or is_merchant) and strangers:
            t = random.choice(strangers)
        else:
            familiar = [res for res, d in near_res if res.id in r.bonds or _relatedness(r, res) > 0]
            t = random.choice(familiar) if familiar and random.random() < 0.8 else random.choice(near_res)[0]
        if abs(t.x - r.x) + abs(t.y - r.y) <= 1:
            return ('interact', None, None, t.id) if r.age > 5 and random.random() < (1.0 / (1 + r.traits.sociability * 2)) * 1.5 or random.random() < 0.1 else ('rest', None, None, None)

    # FORAGE if not full
    if r.energy < 2400 and here.biomass > 10 and random.random() < (1.0 - (pressure - 1.0) * 0.2):
        return ('forage', None, None, None)

    # EXPLORE
    return _explore(r, cells, grid, near_res)


def _explore(r, cells, grid, near_res=None):
    horse_steps = max(1, round(_horse_mult(r, HORSE_SPEED_MULT)))
    known = {(m.x, m.y) for m in r.memory}
    # Gifted scouts (see is_gifted_scout) in a temperate zone are exceptional at spotting
    # genuinely unclaimed land, not just high-biomass land -- real farming suitability is
    # highest in temperate zones (see CLIMATE_ZONES), which is exactly where competition over
    # good farmland matters most. Downweight (not hard-exclude) candidates already crowded by
    # other residents, preferring open territory that reduces resource competition.
    avoid_crowds = near_res is not None and r.is_gifted_scout() and climate_zone(r.y) == 'temperate'
    cands = []
    for c, d in cells:
        if not c.passable() or d == 0:
            continue
        s = c.biomass_cap
        if (c.x, c.y) not in known:
            s *= 2
        if avoid_crowds:
            crowd = sum(1 for res, _ in near_res
                        if abs(res.x - c.x) + abs(res.y - c.y) <= GIFTED_SCOUT_CROWD_RADIUS)
            if crowd > 0:
                s /= (1 + crowd)
        cands.append((c, s))
    if cands:
        total = sum(s for _, s in cands)
        if total > 0:
            pick = random.random() * total
            cum = 0
            for c, s in cands:
                cum += s
                if cum >= pick:
                    return _step_toward(r.x, r.y, c.x, c.y, grid, horse_steps)
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
    # Horse ownership (see LIVESTOCK_ARCHETYPES, RFC-0003) makes travel itself dramatically
    # cheaper -- a mount does the physical work a human otherwise would, same real-world
    # logic behind HORSE_RAID_RANGE's extended reach, just applied to the direct cost of a
    # single movement step rather than how far a nomad will bother traveling.
    if r.known_knowledge.get('animal_husbandry', {}).get('crop_type') == 'horse':
        cost *= HORSE_MOVE_COST_NEAR_ZERO  # direct request: "移动的能量消耗接近0"
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


def _do_forage(r, grid, tick, same_cell_residents=None, pressure=0.0):
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
    # Salt (see SALT_WATER_SUITABILITY/SALT_ISLAND_SUITABILITY) is its own suitability, not
    # folded into mine_suit above -- it must never bias the zone-weighted coal/iron_ore/oil pick,
    # just add a separate, deterministic path to salt specifically wherever there's water.
    # Excluded from the cold zone specifically (real evaporite/solar-salt formation needs real
    # warmth, not a mechanic reason so much as a deliberate zone-exclusivity choice: the cold
    # zone's own economy is pastoral grazing, see COLD_ZONE_GRAZING_BONUS, and giving it salt
    # too would blunt the actual point of zone specialization forcing real exchange).
    salt_suit = 0 if cell.climate == 'cold' else (
        SALT_ISLAND_SUITABILITY if cell.near_island else (SALT_WATER_SUITABILITY if cell.water else 0))
    # Fishing (see TERRAIN_FISHING) isn't zone-gated like farming/grazing/mining -- real
    # fisheries exist in cold, temperate, and tropical water alike, so suitability is purely
    # terrain (is this water, and how good a fishery is it) plus the island proximity bonus.
    fish_suit = TERRAIN_FISHING.get(cell.terrain, 0) * (NEAR_ISLAND_FISHING_MULT if cell.near_island else 1.0)

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
        if random.random() < DOMESTICATION_DISCOVERY_CHANCE * graze_suit * HUSBANDRY_DISCOVERY_MULT:
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
    # Salt -- deterministic (not a zone-weighted archetype pick like coal/iron_ore/oil above),
    # gated purely on salt_suit (any water, ten times richer near the island). Still the same
    # 'mining' knowledge domain/yield/reinforcement machinery, just a different, location-driven
    # discovery path into it.
    if salt_suit > 0 and 'mining' not in r.known_knowledge:
        if random.random() < MINING_DISCOVERY_CHANCE * salt_suit:
            _learn_knowledge(r, 'mining', {
                'level': 0.15, 'source': 'experimented_with_salt_gathering', 'tick_learned': tick,
                'crop_type': 'salt',
            })
            discovery_msg = f'{r.name} discovered how to gather salt'
    if fish_suit > 0 and 'fishing' not in r.known_knowledge:
        if random.random() < DOMESTICATION_DISCOVERY_CHANCE * fish_suit:
            if random.random() < DOMESTICATION_SUCCESS_CHANCE:
                _learn_knowledge(r, 'fishing', {
                    'level': 0.15, 'source': 'experimented_with_fishing', 'tick_learned': tick,
                })
                discovery_msg = f'{r.name} learned to fish'

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

    # Fishing — a food source like farming/herding (see FISHING_BASE_BONUS/SKILL_BONUS in the
    # harvest conversion below), not a stockpile like mining; no cultivation bump since there's
    # no land to tend, just skill deepening through practice.
    if fish_suit > 0 and 'fishing' in r.known_knowledge and random.random() < 0.03:
        _reinforce_knowledge(r, 'fishing', 0.02)

    # Mining — extraction adds directly to the miner's personal resource stockpile rather
    # than energy; minerals are goods to trade or have raided, not food. Yield uses whichever
    # suitability actually applies to what this miner extracts -- a salt gatherer standing at a
    # water tile has mine_suit == 0 there (TERRAIN_MINING has no entry for river/lake/coast),
    # so this must read salt_suit for them instead, not the generic terrain-mining suitability.
    if 'mining' in r.known_knowledge:
        mineral_type = r.known_knowledge['mining'].get('crop_type')
        relevant_suit = salt_suit if mineral_type == 'salt' else mine_suit
        if mineral_type and relevant_suit > 0:
            skill = r.skills.get('mining', 0) / 100.0
            yield_amount = MINING_YIELD_PER_TICK * (0.5 + skill) * relevant_suit
            _add_resource(r, mineral_type, yield_amount)
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
        conversion = 41.0  # raised from 38.0 -- live testing reached a births/deaths ratio of
                            # 0.9972 (survived 3305 ticks, essentially at equilibrium but just
                            # under it), so this is a small, deliberate nudge rather than another
                            # large jump, to avoid repeating the earlier explosive-growth/
                            # performance-crisis cycle
        if cell.climate == 'cold' and SEASONS[(tick // SEASON_LENGTH) % 4] == 'winter':
            conversion += COLD_ZONE_WINTER_HUNT_BONUS
        if farm_suit > 0 and 'crop_cultivation' in r.known_knowledge:
            # Real agricultural revolution: farming yields substantially more usable energy per
            # unit of harvested biomass than raw foraging technique, even before mastery -- a
            # real baseline jump just for having adopted cultivation (CROP_CULTIVATION_BASE_BONUS),
            # scaling further with skill/suitability up to a much larger ceiling than before
            # (CROP_CULTIVATION_SKILL_BONUS, raised from 20.0 -- instrumented testing showed the
            # population running a genuine, chronic aggregate energy deficit).
            conversion += CROP_CULTIVATION_BASE_BONUS + r.skills.get('crop_cultivation', 0) / 100.0 * farm_suit * CROP_CULTIVATION_SKILL_BONUS
        if graze_suit > 0 and 'animal_husbandry' in r.known_knowledge:
            husbandry_bonus = ANIMAL_HUSBANDRY_BASE_BONUS + r.skills.get('animal_husbandry', 0) / 100.0 * graze_suit * ANIMAL_HUSBANDRY_SKILL_BONUS
            if cell.climate == 'cold':
                # Real nomadic pastoralism (Eurasian steppe, etc.): large herds over cold-zone
                # grazing land historically supported real population density, not just marginal
                # subsistence -- the cold zone already has the highest grazing_suitability
                # (CLIMATE_ZONES) and grazer livestock already favors it (LIVESTOCK_ARCHETYPES'
                # zone_weights), but the actual yield bonus wasn't zone-differentiated at all.
                husbandry_bonus *= COLD_ZONE_GRAZING_BONUS
            conversion += husbandry_bonus
        if fish_suit > 0 and 'fishing' in r.known_knowledge:
            conversion += FISHING_BASE_BONUS + r.skills.get('fishing', 0) / 100.0 * fish_suit * FISHING_SKILL_BONUS
        # Sex-based division of labor: reproduction/childcare responsibilities reduce, but
        # do not zero out, a female's foraging output — real hunter-gatherer ethnography
        # (e.g. Hadza gathering studies) shows women's gathering reliably contributes a
        # large share of calories, just typically less than men's higher-risk/higher-return
        # foraging. A hard zero was tried first and caused total economic collapse (halving
        # aggregate production while consumption stayed the same, for both sexes) — this
        # keeps genuine asymmetry and real dependency on mate provisioning (_do_interact)
        # without making the population's energy math structurally unsolvable.
        if r.sex == 'male':
            # Foraging efficiency fades gradually past MALE_FORAGE_DECLINE_ONSET rather than a
            # hard cutoff -- an older male keeps contributing energy, just less of it over time,
            # unlike a female's steep post-fertility falloff (see the age-decline block).
            years_past_onset = max(0, r.age - MALE_FORAGE_DECLINE_ONSET)
            sex_mult = max(MALE_FORAGE_DECLINE_FLOOR, 1.0 - years_past_onset * MALE_FORAGE_DECLINE_RATE)
        else:
            sex_mult = FEMALE_FORAGE_MULT
        # Gifted scouts (see is_gifted_scout) are also exceptional hunters/foragers in harsher
        # zones -- their superior perception/strength/speed reads as real skill at tracking and
        # catching prey specifically where farming suitability is low (cold/tropical), not a
        # zone-independent flat bonus.
        if r.is_gifted_scout() and cell.climate in ('cold', 'tropical'):
            sex_mult *= GIFTED_SCOUT_HUNT_BONUS

        # Dietary diversity (see DIET_DIVERSITY_* constants) -- what was actually eaten this
        # tick, not just how much: a farmer eats their own crop, a herder their own livestock,
        # a fisher their catch, anyone else eats whatever wild biomass was on hand.
        if farm_suit > 0 and 'crop_cultivation' in r.known_knowledge:
            food_type = r.known_knowledge['crop_cultivation'].get('crop_type', 'wild')
        elif graze_suit > 0 and 'animal_husbandry' in r.known_knowledge:
            food_type = r.known_knowledge['animal_husbandry'].get('crop_type', 'wild')
        elif fish_suit > 0 and 'fishing' in r.known_knowledge:
            food_type = 'fish'
        else:
            food_type = 'wild'
        r.recent_food_types[food_type] = tick
        distinct_categories = {FOOD_CATEGORY.get(t, 'wild') for t, last in r.recent_food_types.items()
                                if tick - last <= DIET_DIVERSITY_WINDOW}
        diet_mult = DIET_CATEGORY_MULT.get(min(len(distinct_categories), 3), 0.7)
        # Pressure-gated extra penalty on the single-category (most imbalanced) tier only -- see
        # DIET_IMBALANCE_PRESSURE_THRESHOLD. A small/founding population (pressure below the
        # threshold) is never touched; only once the population is genuinely crowded does staying
        # on one food category start costing extra, which is also exactly when a diet-diverse
        # trade partner (see is_merchant/SOCIAL block) becomes worth the risk of approaching.
        if len(distinct_categories) <= 1 and pressure > DIET_IMBALANCE_PRESSURE_THRESHOLD:
            ramp = min(1.0, (pressure - DIET_IMBALANCE_PRESSURE_THRESHOLD) / DIET_IMBALANCE_PRESSURE_RAMP)
            diet_mult -= DIET_IMBALANCE_MAX_EXTRA_PENALTY * ramp

        salt_mult = SALT_FOOD_BONUS_MULT if r.resources.get('salt', 0) > 0 else SALT_DEFICIT_MULT
        gain = harvest * conversion * sex_mult * diet_mult * salt_mult
        # SINGLE_CATEGORY_ENERGY_CAP (a flat 700 kcal ceiling on single-category gain) was
        # tried and reverted -- see the constant's comment for the full postmortem. Root cause:
        # a resident's traits.strength is fixed for their whole life, so a genuinely strong
        # forager's harvest sits above almost any flat ceiling on EVERY single-category tick,
        # not just an occasional lucky outlier -- the Monte-Carlo calibration that picked 700
        # measured a population-wide percentile snapshot, which doesn't describe how often any
        # ONE strong individual gets clipped over their lifetime. A flat cap functions as a
        # persistent tax specifically on the population's strongest/most productive foragers --
        # exactly the individuals whose surplus the rest of the group's provisioning economy
        # (mate provisioning, food-share, follower tribute) depends on -- so it produces a slow,
        # cascading decline rather than a sharp shock. Confirmed via a 5-way bisection across
        # this session's diet-related commits on seed 42 (a long-used, previously stable seed
        # never included in the smaller 3-seed regression suite used to calibrate the cap):
        # every commit up to and including the production/stockpile boost stayed healthy
        # (pop 218-380 at tick 1200), the energy-cap commit died at tick 981 (265->151->66->5->0),
        # and reverting ONLY the cap (keeping every later change, including merchant-seek-chief)
        # restored survival (pop 218 at tick 1200) -- isolating the cap as the sole cause.
        pre_cap_energy = r.energy + gain - effort
        r.energy = min(MAX_ENERGY, pre_cap_energy)
        r.food_total += harvest

        # Surplus beyond what a farmer can personally consume becomes a tradeable/raidable
        # stockpile rather than being wasted at the energy cap — real surplus (a farmer doing
        # well, not necessarily maxed out — see CROP_SURPLUS_ENERGY_THRESHOLD_FRACTION), not
        # routine foraging gain.
        #
        # An unconditional small per-tick yield (mirroring MINING_YIELD_PER_TICK, independent of
        # this threshold) was also tried and reverted -- see CROP_SURPLUS_ENERGY_THRESHOLD_
        # FRACTION's comment for the full postmortem. It flips a farmer's r.resources from
        # empty to non-empty almost immediately, and _maybe_trade's `not r.resources or
        # random.random() >= TRADE_CHANCE` short-circuits on emptiness -- so this silently
        # changes how many random() calls get consumed per interaction, across the whole shared
        # global random stream, for a huge share of the population at once. A 10-seed test found
        # 3 real extinctions that didn't happen without it, and shrinking the per-tick amount
        # 5x (0.15 -> 0.03) didn't fix it -- confirming this is the emptiness *transition*
        # itself destabilizing the shared RNG sequence, not the magnitude. The threshold change
        # below doesn't have this failure mode (verified 10/10 seeds safe) because it only
        # affects how much a farmer gets when the existing rare surplus event fires, not whether
        # the resources dict exists at all for most of the population.
        if farm_suit > 0 and 'crop_cultivation' in r.known_knowledge:
            crop_type = r.known_knowledge['crop_cultivation'].get('crop_type')
            if crop_type:
                surplus_threshold = MAX_ENERGY * CROP_SURPLUS_ENERGY_THRESHOLD_FRACTION
                if pre_cap_energy > surplus_threshold:
                    surplus = (pre_cap_energy - surplus_threshold) * CROP_SURPLUS_CONVERSION
                    _add_resource(r, crop_type, surplus)

        # Leave some food behind (emergent storage)
        # Storage skill increases how much food is retained
        base_retention = random.uniform(0.1, 0.3)
        storage_skill = r.skills.get('food_storage', 0) / 100.0
        retention = min(0.55, base_retention + storage_skill * 0.25)
        leftover_amount = harvest * retention
        cell.leftover += leftover_amount

    # Resource conflict — competition over scarce food. same_cell_residents is pre-bucketed by
    # exact (x, y) in _tick (see resident_buckets/same_cell_residents) so this doesn't need to
    # scan the whole population (or, worse, self.residents including every resident who has
    # ever lived) to find who else is standing on this tile -- see _nearby_residents's docstring
    # for the O(n^2)-in-aggregate failure mode this mirrors.
    # Cultivation-driven conflict (see CULTIVATED_LAND_CONFLICT_THRESHOLD) is a second, distinct
    # trigger alongside plain scarcity: harvesting land someone has genuinely invested real work
    # in is a grievance on its own, independent of how much biomass happens to be left -- so the
    # rival filter here is Hamilton's-rule stranger-preference (a bonded kin sharing the family
    # plot isn't "stealing"), not mutual desperation like the scarcity case below.
    if same_cell_residents and cell.cultivation > CULTIVATED_LAND_CONFLICT_THRESHOLD:
        cultivation_rivals = [o for o in same_cell_residents if o.alive and o.id != r.id
                               and (o.id not in r.bonds or r.bonds[o.id].quality <= 0)
                               and _relatedness(r, o) < 0.25]
        if cultivation_rivals and random.random() < CONFLICT_CHANCE:
            rival = random.choice(cultivation_rivals)
            r_power = r.traits.strength * random.uniform(0.7, 1.3)
            o_power = rival.traits.strength * random.uniform(0.7, 1.3)
            loser = r if r_power < o_power else rival
            dmg = random.uniform(CONFLICT_DMG_MIN, CONFLICT_DMG_MAX)
            loser.health -= dmg
            return f'{r.name} fought {rival.name} over cultivated land — {loser.name} injured (-{dmg:.0f}hp)'

    if same_cell_residents and cell.biomass < 15:
        rivals = [o for o in same_cell_residents if o.alive and o.id != r.id and o.energy < 1050]
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


def _maybe_trade(r, target, tick, residents_by_id=None):
    """Opportunistic exchange of surplus resources (crops/minerals) between two residents who
    happen to meet — not a scripted trade route (RFC-0007 explicitly forbids that), just
    individual reciprocity extended to named goods the same way food-sharing already works for
    calories. A resident with real surplus of something the other visibly lacks may give some
    away; for a resident with no real need of their own this is a one-off gift, not a
    negotiated barter.

    Two groups complete the reciprocal leg too (the target's own surplus-vs-r's-deficit good
    comes back, turning the gift into a real barter): merchants (is_merchant, RFC-0004), who
    additionally earn a profit margin on it (see MERCHANT_TRADE_PROFIT_KCAL) that gets
    redistributed rather than kept; and any resident whose own recent diet is monotonous
    (low_diversity, same test as the SOCIAL block that risked this contact in the first place)
    — they're the ones with an actual nutritional reason to seek the return good, not a
    speculative one, so they get the real exchange without the merchant's profit skim. Either
    way, a food-category good received (`FOOD_CATEGORY`) counts as consumed for diet-diversity
    purposes (`recent_food_types`) — otherwise trading for what you're missing would have no
    actual effect on the imbalance penalty that motivated the trade."""
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
    accepted = _add_resource(target, good, gift)
    r.resources[good] -= accepted
    if accepted > 0 and good in FOOD_CATEGORY:
        target.recent_food_types[good] = tick
    r.bonds[target.id].quality = min(1.0, r.bonds[target.id].quality + 0.15)
    target.bonds[r.id].quality = min(1.0, target.bonds[r.id].quality + 0.15)

    r_low_diversity = len({FOOD_CATEGORY.get(t, 'wild') for t, last in r.recent_food_types.items()
                            if tick - last <= DIET_DIVERSITY_WINDOW}) <= 1
    merchant_mode = r.is_merchant()
    if (merchant_mode or r_low_diversity) and residents_by_id is not None:
        back_candidates = [
            name for name, qty in target.resources.items()
            if name != good and qty > TRADE_SURPLUS_FLOOR and r.resources.get(name, 0.0) < qty * 0.3
        ]
        if back_candidates:
            back_good = random.choice(back_candidates)
            back_gift = target.resources[back_good] * TRADE_GIFT_FRACTION
            back_accepted = _add_resource(r, back_good, back_gift)
            target.resources[back_good] -= back_accepted
            if back_accepted > 0:
                if back_good in FOOD_CATEGORY:
                    r.recent_food_types[back_good] = tick
                if merchant_mode:
                    chief_ally = None
                    for bid, bond in r.bonds.items():
                        if bond.quality > 0:
                            candidate = residents_by_id.get(bid)
                            if candidate is not None and candidate.alive and candidate.has_chief_standing():
                                chief_ally = candidate
                                break
                    bonded_children = [
                        residents_by_id[bid] for bid, bond in r.bonds.items()
                        if bond.quality > 0 and bid in residents_by_id and residents_by_id[bid].alive
                        and residents_by_id[bid].id != target.id
                        and r.id in (residents_by_id[bid].mother_id, residents_by_id[bid].father_id)
                    ]
                    chief_cut = MERCHANT_TRADE_PROFIT_KCAL * MERCHANT_PROFIT_CHIEF_SHARE
                    child_pool = MERCHANT_TRADE_PROFIT_KCAL - chief_cut
                    if chief_ally is not None:
                        chief_ally.energy = min(MAX_ENERGY, chief_ally.energy + chief_cut)
                        r.energy_given_away += chief_cut
                    else:
                        r.energy = min(MAX_ENERGY, r.energy + chief_cut)
                    if bonded_children:
                        share = child_pool / len(bonded_children)
                        for child in bonded_children:
                            child.energy = min(MAX_ENERGY, child.energy + share)
                        r.energy_given_away += child_pool
                    else:
                        r.energy = min(MAX_ENERGY, r.energy + child_pool)
    return f'{r.name} traded {good} with {target.name}'


def _do_interact(r, target_id, residents_by_id, tick, pressure=0.0):
    target = residents_by_id.get(target_id)
    if target is None or not target.alive:
        return None

    event_msg = None
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
    trade_msg = _maybe_trade(r, target, tick, residents_by_id)
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


def _do_reproduce(r, target_id, residents_by_id, all_residents, grid, tick, next_id):
    target = residents_by_id.get(target_id)
    if target is None or not target.alive:
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
    all_residents.append(child)
    return f'{child.name} born to {r.name} & {target.name} (gen {child.generation})', next_id


def _do_raid(r, target_id, residents_by_id, tick):
    target = residents_by_id.get(target_id)
    if target is None or not target.alive or abs(r.x - target.x) + abs(r.y - target.y) > 1:
        return None

    r_power = r.traits.strength * random.uniform(0.6, 1.4) * _horse_mult(r, HORSE_COMBAT_MULT)
    t_power = target.traits.strength * random.uniform(0.6, 1.4) * _horse_mult(target, HORSE_COMBAT_MULT)

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
                taken = _add_resource(r, steal_target, steal_amount)
                target.resources[steal_target] -= taken
                if target.resources[steal_target] < 0.01:
                    del target.resources[steal_target]
                resource_msg = f' and {taken:.1f} {steal_target}'

        # Coercion — see COERCION_* constants. An overwhelming win against a target nobody is
        # bonded strongly enough to defend can escalate a one-off theft into ongoing labor
        # extraction rather than granting the raider anything they didn't individually win.
        # Excludes kin (Hamilton's rule, matching decide()'s RAID stranger-targeting bias) and
        # never stacks -- a resident can only be coerced by one controller at a time.
        coercion_msg = ''
        if (target.coerced_by is None and r_power > t_power * COERCION_POWER_RATIO
                and _relatedness(r, target) < 0.25
                and random.random() < COERCION_CHANCE
                and max((b.quality for bid, b in target.bonds.items()
                         if bid != r.id and (o := residents_by_id.get(bid)) is not None and o.alive),
                        default=0.0) < COERCION_MAX_TARGET_BOND):
            target.coerced_by = r.id
            coercion_msg = f' — {target.name} is now under {r.name}\'s control'

        return f'{r.name} raided {target.name} — stole {stolen:.0f} food{resource_msg}{coercion_msg}'
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
        self._last_snapshot_time = time.time()  # see save_snapshot/SNAPSHOT_INTERVAL_SECONDS

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

            # Founding herders (see COLD_ZONE_DISEASE_MULT's postmortem, RFC-0003): the cold
            # zone's bootstrapping trap isn't just "harsh winters kill people" -- it's a genuine
            # chicken-and-egg problem, since animal_husbandry itself has to be discovered (a
            # random event requiring real survival time) before its own energy/health benefits
            # ever kick in. Real founding dispersals (Eurasian steppe pastoralist migrations)
            # brought already-domesticated herds with them; they didn't reinvent domestication
            # locally from scratch on arrival every time. This doesn't relocate or otherwise
            # privilege anyone -- it only pre-loads animal_husbandry (same level/format as an
            # ordinary discovery event) for a handful of founders who already landed, by the
            # existing random spawn above, on cold-zone terrain that's actually grazing-suitable
            # (TERRAIN_GRAZING > 0), skipping the discovery roll for them specifically.
            cold_grazing_founders = [
                r for r in cluster_residents
                if climate_zone(r.y) == 'cold' and TERRAIN_GRAZING.get(self.grid[r.y][r.x].terrain, 0) > 0
            ]
            for r in cold_grazing_founders[:FOUNDING_HERDER_COUNT]:
                livestock_type = _pick_archetype(LIVESTOCK_ARCHETYPES, 'cold')
                _learn_knowledge(r, 'animal_husbandry', {
                    'level': 0.15, 'source': 'founding_pastoral_knowledge', 'tick_learned': 0,
                    'crop_type': livestock_type,
                })

    @classmethod
    def load_or_create(cls, snapshot_path=None, seed=None):
        """Entry point server.py uses instead of Simulation() directly -- loads persisted
        state if a valid snapshot exists (see SNAPSHOT_PATH), otherwise falls back to a fresh
        simulation exactly as before. Any failure to load (missing file, corrupt JSON, a
        schema change too large for _resident_from_dict/_cell_from_dict's best-effort
        compatibility layer to bridge) falls through to a fresh start rather than crashing the
        server -- a snapshot is an optimization, never a hard requirement to boot."""
        path = Path(snapshot_path) if snapshot_path else SNAPSHOT_PATH
        if path.exists():
            try:
                return cls._load_snapshot(path)
            except Exception:
                pass
        return cls(seed=seed)

    @classmethod
    def _load_snapshot(cls, path):
        with open(path) as f:
            data = json.load(f)
        sim = cls.__new__(cls)
        sim.seed = data['seed']
        sim.grid = [[_cell_from_dict(cd) for cd in row] for row in data['grid']]
        # Only ever-living residents are persisted (see save_snapshot) -- dead residents are
        # not behaviorally relevant going forward (nothing in the hot path looks up a dead
        # ancestor's Resident object, only the mother_id/father_id ints already stored on their
        # children), and re-seeding self.residents with just the living population on load is
        # exactly the fix for the same unbounded-growth bug this session already found and
        # fixed in the live tick loop (see the O(n) resident-list scan writeup).
        sim.residents = [_resident_from_dict(rd) for rd in data['residents']]
        sim.tick_count = data['tick_count']
        sim.events = []
        sim.all_events = data.get('all_events', [])
        sim.metrics_history = data.get('metrics_history', [])
        sim.running = False  # never auto-resume ticking on load -- a fresh Simulation() also
                               # starts paused; the operator/frontend calls /api/start explicitly
        sim.speed = data.get('speed', 5)
        sim.total_births = data.get('total_births', 0)
        sim.total_deaths = data.get('total_deaths', 0)
        sim.lock = threading.Lock()
        sim._next_id = data.get('next_id', max((r.id for r in sim.residents), default=0))
        sim._state_cache = None
        sim._state_cache_time = 0.0
        sim._last_snapshot_time = time.time()
        sim.ai = AIEngine()
        return sim

    def save_snapshot(self, path=None):
        path = Path(path) if path else SNAPSHOT_PATH
        with self.lock:
            living = [r for r in self.residents if r.alive]
            data = {
                'seed': self.seed,
                'tick_count': self.tick_count,
                'total_births': self.total_births,
                'total_deaths': self.total_deaths,
                'next_id': self._next_id,
                'speed': self.speed,
                'grid': [[_cell_to_dict(c) for c in row] for row in self.grid],
                'residents': [_resident_to_dict(r) for r in living],
                'metrics_history': list(self.metrics_history),
                'all_events': list(self.all_events),
            }
        # Write to a temp file and atomically rename over the real path (os.replace is atomic
        # on POSIX) -- a crash or kill mid-write must never leave a half-written snapshot as
        # the file load_or_create finds on next startup. tmp_path must be unique per call (pid +
        # id()) -- this runs outside self.lock (disk I/O shouldn't block the tick loop), so the
        # periodic auto-save timer and a manual /api/snapshot/save call can genuinely overlap;
        # a shared tmp_path let the first os.replace consume the file out from under the second
        # call, which then raised FileNotFoundError on ITS os.replace. Unique names mean both
        # writes complete independently and os.replace just picks whichever lands last.
        tmp_path = f'{path}.{os.getpid()}.{id(data)}.tmp'
        with open(tmp_path, 'w') as f:
            json.dump(data, f)
        os.replace(tmp_path, path)

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
                    # CARRYING_CAPACITY_MULT applies here too (real regrowth), not just to the
                    # calculated carrying_cap/pressure number below -- an earlier version only
                    # inflated the CALCULATED capacity, which made the reported `pressure` metric
                    # look fine (masking fertility/disease penalties that key off it) while the
                    # real food actually available to forage hadn't changed at all. Applying the
                    # same multiplier to real regrowth keeps both numbers honest and consistent.
                    c.biomass = min(c.biomass_cap, c.biomass + TERRAIN[c.terrain]['regrow'] * m * cultivation_bonus * CARRYING_CAPACITY_MULT)
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
        total_regrow_by_zone = {'cold': 0.0, 'temperate': 0.0, 'tropical': 0.0}
        for row in self.grid:
            for c in row:
                if c.passable():
                    zone_cfg = CLIMATE_ZONES[c.climate]
                    avg_m = sum(zone_cfg[s] for s in SEASONS) / 4
                    cultivation_bonus = 1.0 + c.cultivation * CULTIVATION_MAX_BONUS * c.ag_tech_mult
                    regrow = TERRAIN[c.terrain]['regrow'] * avg_m * cultivation_bonus
                    total_regrow += regrow
                    total_regrow_by_zone[c.climate] += regrow
        # total_regrow is in biomass units; convert to kcal at the same base rate used when
        # biomass is actually foraged (see _do_forage) before comparing against per-person
        # daily kcal need, so this ratio stays dimensionally consistent with the energy model
        carrying_cap = max(10, (total_regrow * 38.0 * CARRYING_CAPACITY_MULT) / (BASELINE_ENERGY_COST * 8.0))
        pop = len(living)
        self._pressure = pop / max(1, carrying_cap)

        # Regional pressure (see COLD_ZONE_DISEASE_MULT's comment) -- used ONLY for the
        # calorie-erosion/malnutrition/disease chain below, not the global self._pressure that
        # every other mechanic (diet penalty, migration, raiding, writing threshold) already
        # relies on -- deliberately scoped to just the one problem being fixed here, not a
        # redefinition of pressure everywhere. A cold-zone pioneer population was being punished
        # by temperate-zone crowding it has nothing to do with: self._pressure is a single global
        # scalar (pop / carrying_cap over the WHOLE map), so a nearly-empty cold zone still
        # inherited the full brunt of the rest of the world being crowded.
        pop_by_zone = {'cold': 0, 'temperate': 0, 'tropical': 0}
        for r in living:
            pop_by_zone[climate_zone(r.y)] += 1
        self._zone_pressure = {}
        for zone, zone_regrow in total_regrow_by_zone.items():
            zone_cap = max(10, (zone_regrow * 38.0 * CARRYING_CAPACITY_MULT) / (BASELINE_ENERGY_COST * 8.0))
            self._zone_pressure[zone] = pop_by_zone[zone] / max(1, zone_cap)

        # Spatial bucket index for O(k) nearby-resident queries (see _nearby_residents) instead
        # of an O(n) linear scan per query -- decide() calls this once per living resident every
        # tick, so the unbucketed version was O(n^2) in aggregate per tick, which became the
        # dominant cost (and eventually made the live server unresponsive) once population grew
        # into the many hundreds. Same bug class as the earlier O(n) 'cluster' metric fix, just
        # on a much hotter path. Built once per tick from a `living` snapshot -- residents born
        # mid-tick (via reproduction) won't appear in it until next tick, an acceptable tradeoff.
        resident_buckets = {}
        for r in living:
            resident_buckets.setdefault((r.x // RESIDENT_BUCKET_SIZE, r.y // RESIDENT_BUCKET_SIZE), []).append(r)

        # id -> Resident and (x,y) -> [Resident] indexes, built once per tick from `living`
        # rather than `self.residents` (which never removes dead residents and only grows,
        # currently far larger than the living population after enough ticks) -- these back
        # the interact/reproduce/raid target lookups and _do_forage's same-tile rival check,
        # replacing what used to be an O(len(self.residents)) linear scan on EVERY such call.
        # That scan re-running per action, per tick, against an ever-growing all-time resident
        # list is what actually caused response times to keep degrading over the life of a long
        # run even while the living population itself stayed flat -- same bug class as the
        # resident_buckets/_nearby_residents fix above, just hiding in a different set of call
        # sites.
        residents_by_id = {r.id: r for r in living}
        same_cell_residents = {}
        for r in living:
            same_cell_residents.setdefault((r.x, r.y), []).append(r)

        def _nearby_fn(r):
            return _nearby_residents(r.x, r.y, r.view_radius(), living, resident_buckets)

        self.ai.process_tick(living, self.grid, _nearby_fn, tick)

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

            # Horse's own energy pool (see HORSE_ENERGY_* comment block) -- deterministic, no
            # random() call, so this update ordering (before decide() runs later this same tick)
            # just means today's horse_energy already reflects this tick's zone before the
            # carry/speed/combat bonuses it feeds (via _horse_bonus_scale) get used below.
            if _has_horse(r):
                if r.horse_energy < 0:
                    r.horse_energy = HORSE_ENERGY_MAX
                replenish = (HORSE_ENERGY_REPLENISH_COLD if climate_zone(r.y) == 'cold'
                             else HORSE_ENERGY_REPLENISH_OTHER)
                r.horse_energy = max(0.0, min(HORSE_ENERGY_MAX,
                                               r.horse_energy + replenish - HORSE_ENERGY_CONSUMPTION))

            # Population pressure multiplier — mild below capacity, brutal above. A cold-zone
            # resident uses their OWN regional pressure (see self._zone_pressure above) instead
            # of the global self._pressure every other mechanic reads -- a cold-zone pioneer
            # shouldn't take calorie-erosion/malnutrition/disease damage scaled by how crowded
            # the temperate zone happens to be. Deliberately NOT extended to temperate/tropical:
            # a first attempt applied this substitution to every zone and caused 2 of 10 test
            # seeds to go extinct via a real, direct effect (not RNG-chaos noise -- both declined
            # steadily from the very first checkpoint) -- tropical's own regional pressure runs
            # consistently much higher than the global average (its farming/grazing_suitability
            # are both 0, so its local carrying capacity is far worse per capita than the
            # temperate-heavy global blend that used to dilute it), and tropical/temperate hold
            # the vast majority of the population, so exposing them to their own true local
            # pressure was a net-negative trade even though it fixed a real unfairness for the
            # small cold-zone minority. Scoped down to cold only, where the problem was actually
            # diagnosed and where the population share affected is small enough not to risk this.
            local_pressure = self._zone_pressure['cold'] if climate_zone(r.y) == 'cold' else self._pressure
            pressure_mult = max(1.0, local_pressure ** 2)

            # Malnutrition — everyone suffers when resources are overstretched (locally)
            if local_pressure > 1.0:
                malnutrition = 5.0 * (local_pressure - 1.0) ** 2
                r.health -= malnutrition
                if random.random() < (local_pressure - 1.0) * 0.1:
                    r.health -= random.uniform(10, 30)  # additional mortality risk due to overcrowding

            # Caloric health erosion — health erodes as a direct, graduated consequence of
            # the caloric reserve dropping through two real thresholds (3000 kcal baseline,
            # erosion below 2000, severe below 1500). There is no separate "cold damage":
            # cold works entirely through the upkeep multiplier above, which drives the
            # reserve down into these bands faster in harsh zones/seasons.
            erosion_threshold, death_zone = _calorie_thresholds(r)
            in_crisis = r.energy < death_zone
            recovering = r.energy > erosion_threshold
            erosion_mult = COLD_ZONE_EROSION_MULT if climate_zone(r.y) == 'cold' else 1.0
            if r.energy < erosion_threshold:
                deficit = (erosion_threshold - r.energy) / erosion_threshold
                r.health -= HEALTH_EROSION_RATE * deficit * pressure_mult * erosion_mult
            if in_crisis:
                severe_deficit = (death_zone - r.energy) / death_zone
                r.health -= DEATH_ZONE_RATE * severe_deficit * pressure_mult * erosion_mult

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
            if climate_zone(r.y) == 'cold':
                disease_p *= COLD_ZONE_DISEASE_MULT
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
            # declining sharply in their 30s regardless of chronological age remaining. This
            # baseline curve is the same for both sexes up through a female's fertile window --
            # see the post-fertility cliff below for where she diverges from it.
            if r.age > AGE_DECLINE_ONSET:
                base_progress = (r.age - AGE_DECLINE_ONSET) / AGE_DECLINE_SPAN
                nutrition_penalty = (r.malnutrition_debt / NUTRITION_DEBT_CAP) * 0.8
                # Inbreeding load shortens expected lifespan (RFC-0011: a genetics-level cost,
                # not a behavioral prohibition) -- same mechanism as the malnutrition penalty,
                # since both represent accumulated biological stress accelerating decline.
                inbreeding_penalty = r.inbreeding_load * INBREEDING_AGING_PENALTY
                p = min(0.5, (base_progress + nutrition_penalty + inbreeding_penalty) * 0.10)
                if random.random() < p:
                    r.health -= 5

            # Post-fertility cliff (see FEMALE_FERTILITY_MAX_AGE/FEMALE_POST_FERTILITY_DECLINE)
            # -- once a female is past her reproductive window, she is deliberately made to
            # decline fast rather than linger for decades consuming food without contributing
            # energy or children. This is a resource-allocation design choice, not merely
            # "menopause happens": a real, steep, roughly age-independent health loss each tick.
            if r.sex == 'female' and r.age > FEMALE_FERTILITY_MAX_AGE:
                r.health -= FEMALE_POST_FERTILITY_DECLINE

            # Death check
            if r.health <= 0 or r.age > MAX_AGE:
                if r.age > MAX_AGE:
                    cause = 'old_age'
                elif r.sex == 'female' and r.age > FEMALE_FERTILITY_MAX_AGE:
                    cause = 'senescence'  # distinct from 'disease' for observability -- see
                                            # FEMALE_POST_FERTILITY_DECLINE
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
                    other = residents_by_id.get(r.spouse_id)
                    if other is not None:
                        other.spouse_id = None

                # Leadership succession — see HEIR_ENERGY_INHERITANCE. A dead chief's standing
                # itself can't be handed to anyone (chief_standing stays a pure readout over
                # the HEIR's own future redistribution behavior, never assigned by the engine —
                # RFC-0007 forbids granting a capability/status an individual didn't earn
                # themselves), but their accumulated resources, some remaining energy, and their
                # follower network are real inheritable capital that gives the heir a genuine
                # head start toward earning chief_standing in their own right. Heir preference:
                # the most capable gifted scout among the dead chief's own followers (bonded,
                # alive), falling back to the eldest living son.
                if r.has_chief_standing():
                    followers = [residents_by_id.get(bid) for bid, bond in r.bonds.items() if bond.quality > 0]
                    followers = [f for f in followers if f is not None and f.alive]
                    heir_candidates = [f for f in followers if f.is_gifted_scout()]
                    heir = max(heir_candidates, key=_capability) if heir_candidates else None
                    if heir is None:
                        sons = [f for f in living if f.sex == 'male' and (f.mother_id == r.id or f.father_id == r.id)]
                        heir = max(sons, key=lambda s: s.age) if sons else None
                    if heir is not None:
                        for good, amount in r.resources.items():
                            _add_resource(heir, good, amount)
                        heir.energy = min(MAX_ENERGY, heir.energy + r.energy * HEIR_ENERGY_INHERITANCE)
                        for f in followers:
                            if f.id == heir.id:
                                continue
                            old_quality = f.bonds[r.id].quality
                            if f.id not in heir.bonds or heir.bonds[f.id].quality < old_quality:
                                heir.bonds[f.id] = Bond(f.id, old_quality, tick)
                            if heir.id not in f.bonds or f.bonds[heir.id].quality < old_quality:
                                f.bonds[heir.id] = Bond(heir.id, old_quality, tick)
                        evts.append({'tick': tick, 'type': 'succession',
                                     'text': f'{heir.name} inherits {r.name}\'s standing and followers',
                                     'x': heir.x, 'y': heir.y})

                evts.append({'tick': tick, 'type': 'death',
                             'text': f'{r.name} died ({cause}, age {r.age}, gen {r.generation})',
                             'x': r.x, 'y': r.y})
                continue

            # Memory decay
            if r.memory and random.random() < 0.02:
                r.memory.pop(random.randint(0, len(r.memory) - 1))

            # Coercion status — ends via the controller dying (checked lazily here rather than
            # scanning coerced residents at the moment of a death) or a small standing chance of
            # breaking free outright (see COERCION_ESCAPE_CHANCE); never a permanent lock.
            if r.coerced_by is not None:
                controller = residents_by_id.get(r.coerced_by)
                if controller is None or not controller.alive or random.random() < COERCION_ESCAPE_CHANCE:
                    r.coerced_by = None

            # Slow tier override or fast tier decision
            ai_action, ai_text = self.ai.get_override(r.id)
            if ai_action:
                action, tx, ty, tid = ai_action
                evts.append({'tick': tick, 'type': 'ai',
                             'text': f'[AI] {r.name}: {ai_text[:80] if ai_text else "decided"}',
                             'x': r.x, 'y': r.y})
            else:
                action, tx, ty, tid = decide(r, self.grid, living, tick, self._pressure, resident_buckets,
                                              getattr(self, '_group_root', {}), getattr(self, '_zone_pressure', None))

            msg = None
            _energy_before_action = r.energy
            if action == 'move':
                msg = _do_move(r, tx, ty, self.grid)
            elif action == 'forage':
                msg = _do_forage(r, self.grid, tick, same_cell_residents.get((r.x, r.y)), self._pressure)
            elif action == 'rest':
                r.health = min(MAX_HEALTH, r.health + 2.5 * r.traits.endurance)
            elif action == 'interact':
                msg = _do_interact(r, tid, residents_by_id, tick, self._pressure)
            elif action == 'raid':
                msg = _do_raid(r, tid, residents_by_id, tick)
            elif action == 'scavenge':
                msg = _do_scavenge(r, self.grid)
            elif action == 'reproduce':
                msg, self._next_id = _do_reproduce(r, tid, residents_by_id, self.residents, self.grid, tick, self._next_id)

            # Coercion tribute — a share of a coerced resident's own foraging gain is
            # redirected to their controller before anything else is tallied (see coerced_by,
            # COERCION_TRIBUTE_SHARE, and _do_raid's coercion branch). This is what makes
            # controlling another person's labor economically worthwhile in the first place;
            # the forager still ran their own decide()/skills, only the surplus is diverted.
            if action == 'forage' and r.coerced_by is not None and r.energy > _energy_before_action:
                controller = residents_by_id.get(r.coerced_by)
                if controller is not None and controller.alive:
                    tribute = (r.energy - _energy_before_action) * COERCION_TRIBUTE_SHARE
                    r.energy -= tribute
                    controller.energy = min(MAX_ENERGY, controller.energy + tribute)

            # Follower tribute — see FOLLOWER_TRIBUTE_SHARE. Voluntary counterpart of coercion
            # tribute: a resident bonded to a chief-standing ally redirects a modest share of
            # their own forage surplus to that leader. Doesn't touch the chief's own
            # energy_given_away (see FOLLOWER_TRIBUTE_SHARE's comment).
            elif action == 'forage' and r.coerced_by is None and r.energy > _energy_before_action:
                chief_ally = None
                for bid, bond in r.bonds.items():
                    if bond.quality > 0:
                        candidate = residents_by_id.get(bid)
                        if candidate is not None and candidate.alive and candidate.has_chief_standing():
                            chief_ally = candidate
                            break
                if chief_ally is not None:
                    tribute = (r.energy - _energy_before_action) * FOLLOWER_TRIBUTE_SHARE
                    r.energy -= tribute
                    chief_ally.energy = min(MAX_ENERGY, chief_ally.energy + tribute)

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
            group_root = {}
            for r in living:
                root = find(r.id)
                groups[root] = groups.get(root, 0) + 1
                group_root[r.id] = root
            self._last_group_count = len(groups)
            self._last_largest_group = max(groups.values(), default=0)
            # Per-resident group membership (see decide()'s OPPORTUNISTIC RAID/TERRITORIAL
            # DEFENSE) -- reuses the find() roots this same union-find pass already computes,
            # no extra cost. Refreshed on the same SEASON_LENGTH cadence as group_count above;
            # a resident who joined/left a group within the last few ticks may read slightly
            # stale, an acceptable tradeoff matching resident_buckets' own documented one.
            self._group_root = group_root
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
        fisher_holders = sum(1 for r in living if 'fishing' in r.known_knowledge)
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
        gifted_scout_count = sum(1 for r in living if r.is_gifted_scout())
        merchant_count = sum(1 for r in living if r.is_merchant())
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

        horse_owners = [r for r in living if _has_horse(r)]
        avg_horse_energy_pct = (round(100.0 * sum(max(0.0, r.horse_energy) for r in horse_owners)
                                       / (len(horse_owners) * HORSE_ENERGY_MAX), 1)
                                 if horse_owners else 0.0)

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
            'fisher_holders': fisher_holders,
            'cultivated_cells': cultivated_cells,
            'language_holders': language_holders,
            'writing_holders': writing_holders,
            'chief_holders': chief_holders,
            'priest_holders': priest_holders,
            'gifted_scout_count': gifted_scout_count,
            'merchant_count': merchant_count,
            'coerced_count': sum(1 for r in living if r.coerced_by is not None),
            'avg_diet_diversity': round(sum(
                len({FOOD_CATEGORY.get(t, 'wild') for t, last in r.recent_food_types.items()
                     if tick - last <= DIET_DIVERSITY_WINDOW})
                for r in living) / max(1, n), 3),
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
            'avg_horse_energy_pct': avg_horse_energy_pct,
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
                'is_gifted_scout': r.is_gifted_scout(), 'scout_target': r.scout_target,
                'is_merchant': r.is_merchant(), 'carrying_capacity': round(r.traits.carrying_capacity, 1),
                'coerced_by': r.coerced_by,
                'diet_diversity': len({FOOD_CATEGORY.get(t, 'wild') for t, last in r.recent_food_types.items()
                                        if self.tick_count - last <= DIET_DIVERSITY_WINDOW}),
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
            if time.time() - self._last_snapshot_time > SNAPSHOT_INTERVAL_SECONDS:
                self._last_snapshot_time = time.time()
                try:
                    self.save_snapshot()
                except Exception:
                    pass  # a failed snapshot write must never take down the live tick loop
            time.sleep(1.0 / self.speed)
