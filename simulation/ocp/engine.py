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
REPRODUCTION_ENERGY = 55
REPRODUCTION_COST = 25
OFFSPRING_ENERGY = 20
BASELINE_ENERGY_COST = 2.0
PERCEPTION_BASE_RADIUS = 3
MAX_ENERGY = 100.0
MAX_HEALTH = 100.0
SEASON_LENGTH = 8
MEMORY_CAPACITY = 50
TRAIT_MUTATION = 0.15

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
WINTER_COLD_THRESHOLD = 30
WINTER_COLD_DMG = 8
ACCIDENT_CHANCE = 0.003
ACCIDENT_DMG_MIN = 8
NUTRITION_STRESS_ENERGY = 30    # below this, chronic malnutrition debt accumulates
NUTRITION_RECOVERY_ENERGY = 65  # above this, malnutrition debt slowly heals
NUTRITION_DEBT_RATE = 0.5       # debt gained per tick while chronically hungry
NUTRITION_RECOVERY_RATE = 0.15  # debt healed per tick while reliably well-fed
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
CLIMATE_ZONES = {
    'cold':      {'spring': 1.1, 'summer': 0.8, 'autumn': 0.35, 'winter': 0.005,
                  'winter_upkeep': 2.8, 'cold_threshold': 50, 'cold_dmg': 14,
                  'grazing_suitability': 1.0, 'farming_suitability': 0.1},
    'temperate': {'spring': 1.4, 'summer': 1.0, 'autumn': 0.55, 'winter': 0.02,
                  'winter_upkeep': 1.8, 'cold_threshold': 35, 'cold_dmg': 9,
                  'grazing_suitability': 0.25, 'farming_suitability': 1.0},
    'tropical':  {'spring': 1.2, 'summer': 1.0, 'autumn': 0.75, 'winter': 0.05,
                  'winter_upkeep': 1.3, 'cold_threshold': 20, 'cold_dmg': 4,
                  'grazing_suitability': 0.0, 'farming_suitability': 0.0},
}

# Terrain suitability for domestication (physical property of the land, like biomass_cap)
# Cold zone pasture-grade terrain suits grazing; temperate arable terrain suits crop cultivation.
# Tropical zone's zone-level suitability above is 0, so terrain suitability never activates there.
TERRAIN_GRAZING = {'plains': 0.8, 'mountain': 1.0, 'desert': 0.3}
TERRAIN_FARMING = {'plains': 1.0, 'river': 0.7, 'forest': 0.2}

DOMESTICATION_DISCOVERY_CHANCE = 0.0025  # per qualifying forage tick, before suitability scaling
# Residents forage nomadically and rarely revisit the exact same cell many ticks in a row,
# so a single visit must contribute a meaningful amount for land improvement to be observable
# at population scale; decay is slow so occasional return visits still net-accumulate.
CULTIVATION_GAIN_RATE = 1.2  # cultivation gained per forage tick at full skill and suitability
CULTIVATION_DECAY = 0.0002  # cultivation lost per tick when not actively tended
CULTIVATION_MAX_BONUS = 7.0  # at cultivation=1.0, regrow is multiplied by (1 + this) — real farmland
                              # vastly outproduces wild foraging per unit area

# Shelter and clothing — Experiment pathway triggered by direct cold exposure (energy below
# the zone's cold_threshold). Colder zones expose residents to this condition constantly,
# so these technologies emerge first and fastest exactly where they matter — no zone gate
# is needed beyond the cold-exposure condition itself, unlike domestication.
SHELTER_DISCOVERY_CHANCE = 0.05   # per winter tick of direct cold exposure
CLOTHING_DISCOVERY_CHANCE = 0.05  # per winter tick of direct cold exposure

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
LANGUAGE_BOND_THRESHOLD = 0.2        # this specific relationship must carry real cooperative value
LANGUAGE_REPEAT_THRESHOLD = 3        # repeated game — interacted with this individual several times
LANGUAGE_PRESSURE_THRESHOLD = 0.6    # environmental uncertainty/scarcity creates coordination payoff
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
WRITING_ENERGY_THRESHOLD = 55        # writing requires surplus, not survival-mode scarcity
WRITING_GROUP_SIZE = 3               # writing serves a larger, more organized group than language alone
WRITING_PRESSURE_THRESHOLD = 0.9     # society has grown to fill its available capacity


def _transmission_fidelity(speaker):
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

    def view_radius(self):
        return max(1, int(PERCEPTION_BASE_RADIUS * self.traits.perception))

    def upkeep(self):
        return BASELINE_ENERGY_COST / self.traits.endurance


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
            inherited_knowledge[kname] = {
                'level': kdata['level'] * parent_fidelity,
                'source': f'inherited_from_{parent.name}',
                'tick_learned': tick
            }
        if partner and partner.known_knowledge:
            # Also inherit from partner, taking the best version
            partner_fidelity = _transmission_fidelity(partner) * random.uniform(0.85, 1.0)
            for kname, kdata in partner.known_knowledge.items():
                if kname in inherited_knowledge:
                    # Take the better version
                    if kdata['level'] > inherited_knowledge[kname]['level']:
                        inherited_knowledge[kname]['level'] = kdata['level'] * partner_fidelity
                else:
                    inherited_knowledge[kname] = {
                        'level': kdata['level'] * partner_fidelity,
                        'source': f'inherited_from_{partner.name}',
                        'tick_learned': tick
                    }
    else:
        while True:
            x, y = random.randint(0, GRID_W-1), random.randint(0, GRID_H-1)
            if grid[y][x].passable():
                break
        traits = Traits.random()
        gen, pid = 0, None
        nrg = random.uniform(65, 90)
        inherited_knowledge = {}

    child = Resident(rid, _rand_name(), x, y, 0, nrg, MAX_HEALTH, traits,
                    True, pid, gen, [], {}, tick)
    child.known_knowledge = inherited_knowledge
    child.skills = {kname: kdata['level'] * 100 for kname, kdata in inherited_knowledge.items()}
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
    if r.energy < 50 and here.leftover > 3:
        return ('scavenge', None, None, None)

    # DESPERATE: raid nearby cells for leftover food (no killing needed)
    if r.energy < 25 and here.biomass < 2 and here.leftover < 2:
        # Look for nearby cells with leftovers
        cells = _nearby_cells(r.x, r.y, 2, grid)
        leftover_cells = [(c, d) for c, d in cells if c.leftover > 5 and d > 0]
        if leftover_cells:
            target_cell = max(leftover_cells, key=lambda x: x[0].leftover)[0]
            return _step_toward(r.x, r.y, target_cell.x, target_cell.y, grid)

    # RAID: attack someone for energy as last resort
    raid_base = 0.3 + r.traits.risk_tolerance * 0.5
    if pressure > 1.2:
        raid_base += 0.2 * (pressure - 1.2)

    if r.energy < 18 and here.biomass < 3 and here.leftover < 2:
        adjacent = [(res, d) for res, d in near_res if d <= 1 and res.energy > 30]
        if adjacent and random.random() < raid_base:
            target = max(adjacent, key=lambda x: x[0].energy)[0]
            return ('raid', None, None, target.id)

    # MIGRATE: Move to warmer zone when resources fail (especially in winter)
    if r.energy < 30 and season == 'winter' and climate_zone(r.y) != 'tropical':
        # Try to move toward tropical zone
        if r.y > 52:  # Already in tropical
            pass
        elif r.y > 26:  # In temperate, move toward tropical
            target_y = min(r.y + 2, 79)
            return ('move', r.x, target_y, None)
        else:  # In cold, move toward temperate
            target_y = min(r.y + 3, 79)
            return ('move', r.x, target_y, None)

    # CRITICAL / HUNGRY: find food
    if r.energy < 40:
        if here.biomass > 3:
            return ('forage', None, None, None)
        best = _best_food(cells)
        if best:
            return _step_toward(r.x, r.y, best.x, best.y, grid)
        return _random_move(r, grid)

    # INJURED: rest
    if r.health < 50 and r.energy > 20:
        return ('rest', None, None, None)

    # REPRODUCE — fertility drops under Malthusian pressure
    if r.energy > REPRODUCTION_ENERGY and r.age > REPRODUCTION_AGE:
        fertility = 1.0 if pressure < 0.8 else max(0.05, 1.0 / (1.0 + (pressure - 0.8) * 5))
        if random.random() < fertility:
            partners = [(res, d) for res, d in near_res
                        if res.energy > REPRODUCTION_ENERGY and res.age > REPRODUCTION_AGE]
            if partners:
                p = min(partners, key=lambda x: x[1])[0]
                if abs(p.x - r.x) + abs(p.y - r.y) <= 1:
                    return ('reproduce', None, None, p.id)
                return _step_toward(r.x, r.y, p.x, p.y, grid)

    # SOCIAL
    if r.traits.sociability > 0.5 and near_res and random.random() < 0.3:
        t = random.choice(near_res)[0]
        if abs(t.x - r.x) + abs(t.y - r.y) <= 1:
            return ('interact', None, None, t.id)

    # FORAGE if not full
    if r.energy < 80 and here.biomass > 10:
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
    cost = TERRAIN[cell.terrain]['move'] / r.traits.speed
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

    if farm_suit > 0 and 'crop_cultivation' not in r.known_knowledge:
        if random.random() < DOMESTICATION_DISCOVERY_CHANCE * farm_suit:
            r.known_knowledge['crop_cultivation'] = {
                'level': 0.15, 'source': 'experimented_with_planting', 'tick_learned': tick
            }
            r.skills['crop_cultivation'] = 15.0
            discovery_msg = f'{r.name} discovered crop cultivation'
    if graze_suit > 0 and 'animal_husbandry' not in r.known_knowledge:
        if random.random() < DOMESTICATION_DISCOVERY_CHANCE * graze_suit:
            r.known_knowledge['animal_husbandry'] = {
                'level': 0.15, 'source': 'experimented_with_herding', 'tick_learned': tick
            }
            r.skills['animal_husbandry'] = 15.0
            discovery_msg = f'{r.name} discovered animal husbandry'

    # Tending the land — knowledge-holders raise the cell's cultivation level through
    # sustained work; skill itself deepens gradually through practice (learning by doing)
    if farm_suit > 0 and 'crop_cultivation' in r.known_knowledge:
        skill = r.skills.get('crop_cultivation', 0) / 100.0
        cell.cultivation = min(1.0, cell.cultivation + CULTIVATION_GAIN_RATE * skill * farm_suit)
        if random.random() < 0.03:
            current = r.known_knowledge['crop_cultivation']['level']
            r.known_knowledge['crop_cultivation']['level'] = min(1.0, current + 0.02 * (1.0 - current))
            r.skills['crop_cultivation'] = r.known_knowledge['crop_cultivation']['level'] * 100
    if graze_suit > 0 and 'animal_husbandry' in r.known_knowledge:
        skill = r.skills.get('animal_husbandry', 0) / 100.0
        cell.cultivation = min(1.0, cell.cultivation + CULTIVATION_GAIN_RATE * skill * graze_suit)
        if random.random() < 0.03:
            current = r.known_knowledge['animal_husbandry']['level']
            r.known_knowledge['animal_husbandry']['level'] = min(1.0, current + 0.02 * (1.0 - current))
            r.skills['animal_husbandry'] = r.known_knowledge['animal_husbandry']['level'] * 100

    # Harvest from biomass
    if cell.biomass > 0:
        harvest = min(cell.biomass, 15 * r.traits.strength) * random.uniform(0.5, 1.0)
        effort = 0.5 / r.traits.endurance
        cell.biomass -= harvest

        # Domestication conversion efficiency — better technique extracts more usable energy
        # from the same harvested biomass (does not exceed what was actually taken from the land)
        conversion = 0.8
        if farm_suit > 0 and 'crop_cultivation' in r.known_knowledge:
            conversion += r.skills.get('crop_cultivation', 0) / 100.0 * farm_suit * 0.5
        if graze_suit > 0 and 'animal_husbandry' in r.known_knowledge:
            conversion += r.skills.get('animal_husbandry', 0) / 100.0 * graze_suit * 0.5
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
                  and o.x == r.x and o.y == r.y and o.energy < 35]
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

    scavenged = min(cell.leftover * 0.7, MAX_ENERGY - r.energy)
    cell.leftover -= scavenged
    r.energy = min(MAX_ENERGY, r.energy + scavenged)

    return f'{r.name} scavenged {scavenged:.0f} food from leftovers'


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
    if pressure < LANGUAGE_PRESSURE_THRESHOLD:
        return None
    chance = LANGUAGE_DISCOVERY_CHANCE * (LANGUAGE_COOPERATION_BONUS if cooperative else 1.0)
    if random.random() < chance:
        origin = 'during_cooperation' if cooperative else 'through_repeated_contact'
        r.known_knowledge['spoken_language'] = {
            'level': 0.3, 'source': f'coined_with_{target.name}_{origin}', 'tick_learned': tick
        }
        r.skills['spoken_language'] = 30.0
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
    if r.energy > 60 and target.energy < 30 and r.traits.sociability > 0.4:
        share = min(15, r.energy - 50)
        r.energy -= share
        target.energy = min(MAX_ENERGY, target.energy + share * 0.9)
        r.bonds[target.id].quality = min(1.0, r.bonds[target.id].quality + 0.2)
        target.bonds[r.id].quality = min(1.0, target.bonds[r.id].quality + 0.3)
        lang_msg = _maybe_discover_language(r, target, tick, pressure, cooperative=True)
        return lang_msg or f'{r.name} shared food with {target.name}'

    # Exchange spatial memory (with distortion per RFC-0001 Law 6)
    r.bonds[target.id].quality = min(1.0, r.bonds[target.id].quality + 0.05)
    if r.memory and random.random() < 0.5:
        mem = random.choice(r.memory)
        distorted = MemEntry(mem.x, mem.y, mem.biomass * random.uniform(0.7, 1.3), tick)
        target.memory.append(distorted)
        if len(target.memory) > MEMORY_CAPACITY:
            target.memory.sort(key=lambda m: m.tick, reverse=True)
            target.memory = target.memory[:MEMORY_CAPACITY]

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

    if r.known_knowledge and random.random() < transmission_prob:
        # Pick a random knowledge the speaker has
        knowledge_name = random.choice(list(r.known_knowledge.keys()))
        speaker_knowledge = r.known_knowledge[knowledge_name]
        channel_fidelity = _transmission_fidelity(r)

        # Listener learns with distortion/loss proportional to quality gap
        if knowledge_name not in target.known_knowledge:
            # First time hearing about this knowledge — capped by the speaker's channel,
            # scaled down if the speaker's own grasp of it is still shallow
            fidelity = channel_fidelity * (0.5 + speaker_knowledge['level'] * 0.5)
            learned_level = speaker_knowledge['level'] * fidelity
            target.known_knowledge[knowledge_name] = {
                'level': learned_level,
                'source': f'learned_from_{r.name}',
                'tick_learned': tick
            }
            target.skills[knowledge_name] = learned_level * 100
            if not event_msg:
                event_msg = f'{r.name} taught {target.name} about {knowledge_name}'
        else:
            # Reinforce existing knowledge (only if speaker knows better)
            existing_level = target.known_knowledge[knowledge_name]['level']
            if speaker_knowledge['level'] > existing_level:
                improvement = (speaker_knowledge['level'] - existing_level) * channel_fidelity * 0.2
                target.known_knowledge[knowledge_name]['level'] = min(1.0, existing_level + improvement)
                target.skills[knowledge_name] = target.known_knowledge[knowledge_name]['level'] * 100

        # Learning by doing: successfully communicating deepens the speaker's own
        # language/writing fluency, same reinforcement pattern as other practiced skills
        for meta_skill in ('spoken_language', 'writing'):
            if meta_skill in r.known_knowledge and random.random() < 0.04:
                current = r.known_knowledge[meta_skill]['level']
                r.known_knowledge[meta_skill]['level'] = min(1.0, current + 0.03 * (1.0 - current))
                r.skills[meta_skill] = r.known_knowledge[meta_skill]['level'] * 100

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
        stolen = min(target.energy * 0.4, 20)
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

        # Environment: biomass regrowth (zone-dependent season multiplier, cultivated land regrows faster)
        for row in self.grid:
            for c in row:
                if c.biomass < c.biomass_cap:
                    m = c.season_mult(season)
                    cultivation_bonus = 1.0 + c.cultivation * CULTIVATION_MAX_BONUS
                    c.biomass = min(c.biomass_cap, c.biomass + TERRAIN[c.terrain]['regrow'] * m * cultivation_bonus)
                # Untended land slowly reverts to wild (Law 10 Entropy)
                if c.cultivation > 0:
                    c.cultivation = max(0.0, c.cultivation - CULTIVATION_DECAY)

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
                    cultivation_bonus = 1.0 + c.cultivation * CULTIVATION_MAX_BONUS
                    total_regrow += TERRAIN[c.terrain]['regrow'] * avg_m * cultivation_bonus
        carrying_cap = max(10, total_regrow / (BASELINE_ENERGY_COST * 8.0))
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

            # Upkeep — zone-dependent winter multiplier, reduced by food storage and clothing
            cost = r.upkeep()
            zone_cfg = CLIMATE_ZONES[climate_zone(r.y)]
            if season == 'winter':
                storage_skill = r.skills.get('food_storage', 0) / 100.0
                clothing_skill = r.skills.get('clothing_making', 0) / 100.0
                # Stored food and insulating clothing both soften winter upkeep; independent
                # reductions combine multiplicatively (neither alone reaches the other's ceiling)
                food_reduction = 1.0 - storage_skill * 0.3
                clothing_reduction = 1.0 - clothing_skill * 0.35
                effective_upkeep = zone_cfg['winter_upkeep'] * food_reduction * clothing_reduction
                cost *= effective_upkeep
            r.energy -= cost

            # Population pressure multiplier — mild below capacity, brutal above
            pressure_mult = max(1.0, self._pressure ** 2)

            # Starvation — amplified by pressure (less food per person)
            if r.energy <= 0:
                r.energy = 0
                r.health -= 5 * pressure_mult

            # Malnutrition — everyone suffers when resources are overstretched
            if self._pressure > 1.0:
                malnutrition = 5.0 * (self._pressure - 1.0) ** 2
                r.health -= malnutrition

            # Winter exposure — zone-dependent cold damage, blunted by shelter
            cold_thr = zone_cfg['cold_threshold']
            cold_dmg = zone_cfg['cold_dmg']
            if season == 'winter' and cold_thr > 0 and r.energy < cold_thr:
                shelter_skill = r.skills.get('shelter_building', 0) / 100.0
                effective_cold_dmg = cold_dmg * (1.0 - shelter_skill * 0.6)
                r.health -= effective_cold_dmg * (1.0 - r.energy / cold_thr)

            # Winter: near-starvation drives knowledge discovery and reinforcement
            if season == 'winter':
                # Starvation discovery: residents who nearly starve (energy < 10) may learn
                # from painful experience, only if they don't already know
                if r.energy < 10 and 'food_storage' not in r.known_knowledge:
                    if random.random() < 0.08:  # 8% chance per winter tick of near-starvation
                        r.known_knowledge['food_storage'] = {
                            'level': 0.2,
                            'source': 'desperate_winter_experience',
                            'tick_learned': tick
                        }
                        r.skills['food_storage'] = 20.0
                        evts.append({'tick': tick, 'type': 'discovery',
                                     'text': f'{r.name} learned food storage through winter hardship',
                                     'x': r.x, 'y': r.y})

                # Knowledge reinforcement: experienced residents with knowledge may improve
                # through successful winter survival
                elif r.energy > 15 and 'food_storage' in r.known_knowledge and random.random() < 0.06:
                    current = r.known_knowledge['food_storage']['level']
                    improvement = 0.04 + (0.04 * (1.0 - current))
                    r.known_knowledge['food_storage']['level'] = min(1.0, current + improvement)
                    r.skills['food_storage'] = r.known_knowledge['food_storage']['level'] * 100

                # Shelter discovery — Experiment pathway: repeated direct cold-exposure damage
                # (energy below the zone's cold threshold) motivates building windbreaks/shelter.
                # Colder zones expose residents to this condition far more often, so shelter
                # naturally emerges first and fastest where it matters most.
                if (r.energy < cold_thr and 'shelter_building' not in r.known_knowledge
                        and random.random() < SHELTER_DISCOVERY_CHANCE):
                    r.known_knowledge['shelter_building'] = {
                        'level': 0.2, 'source': 'cold_exposure_experience', 'tick_learned': tick
                    }
                    r.skills['shelter_building'] = 20.0
                    evts.append({'tick': tick, 'type': 'discovery',
                                 'text': f'{r.name} learned to build shelter against the cold',
                                 'x': r.x, 'y': r.y})
                elif (r.energy >= cold_thr and 'shelter_building' in r.known_knowledge
                        and random.random() < 0.05):
                    current = r.known_knowledge['shelter_building']['level']
                    r.known_knowledge['shelter_building']['level'] = min(1.0, current + 0.04 * (1.0 - current))
                    r.skills['shelter_building'] = r.known_knowledge['shelter_building']['level'] * 100

                # Clothing discovery — same Experiment pathway, independent invention from
                # shelter (a resident may find one, the other, or both over time)
                if (r.energy < cold_thr and 'clothing_making' not in r.known_knowledge
                        and random.random() < CLOTHING_DISCOVERY_CHANCE):
                    r.known_knowledge['clothing_making'] = {
                        'level': 0.2, 'source': 'cold_exposure_experience', 'tick_learned': tick
                    }
                    r.skills['clothing_making'] = 20.0
                    evts.append({'tick': tick, 'type': 'discovery',
                                 'text': f'{r.name} learned to make warm clothing',
                                 'x': r.x, 'y': r.y})
                elif (r.energy >= cold_thr and 'clothing_making' in r.known_knowledge
                        and random.random() < 0.05):
                    current = r.known_knowledge['clothing_making']['level']
                    r.known_knowledge['clothing_making']['level'] = min(1.0, current + 0.04 * (1.0 - current))
                    r.skills['clothing_making'] = r.known_knowledge['clothing_making']['level'] * 100

            # Writing discovery — Experiment pathway: a resident who already has spoken
            # language, belongs to a larger organized group, holds enough distinct
            # knowledge domains to strain memory, has energy surplus, and whose society
            # is pressing at or beyond its subsistence ceiling occasionally devises a
            # symbolic record to externalize what oral tradition alone keeps losing.
            if ('spoken_language' in r.known_knowledge and 'writing' not in r.known_knowledge
                    and len(r.known_knowledge) >= WRITING_COMPLEXITY_THRESHOLD
                    and len(r.bonds) >= WRITING_GROUP_SIZE
                    and r.energy > WRITING_ENERGY_THRESHOLD
                    and self._pressure > WRITING_PRESSURE_THRESHOLD):
                if random.random() < WRITING_DISCOVERY_CHANCE:
                    r.known_knowledge['writing'] = {
                        'level': 0.25,
                        'source': 'devised_symbolic_record',
                        'tick_learned': tick
                    }
                    r.skills['writing'] = 25.0
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
                if len(r.memory) > MEMORY_CAPACITY:
                    r.memory.sort(key=lambda m: m.tick, reverse=True)
                    r.memory = r.memory[:MEMORY_CAPACITY]

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
            'avg_immunity': round(sum(r.traits.immunity for r in living) / max(1, n), 3),
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
                'str': round(r.traits.strength, 2),
                'spd': round(r.traits.speed, 2),
                'per': round(r.traits.perception, 2),
                'end': round(r.traits.endurance, 2),
                'soc': round(r.traits.sociability, 2),
                'risk': round(r.traits.risk_tolerance, 2),
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
