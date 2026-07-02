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
INITIAL_POPULATION = 120
MAX_AGE = 65
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
CLIMATE_ZONES = {
    'cold':      {'spring': 1.0, 'summer': 0.7, 'autumn': 0.2, 'winter': 0.02,
                  'winter_upkeep': 3.0, 'cold_threshold': 50, 'cold_dmg': 25},
    'temperate': {'spring': 1.5, 'summer': 1.0, 'autumn': 0.5, 'winter': 0.15,
                  'winter_upkeep': 1.5, 'cold_threshold': 30, 'cold_dmg': 10},
    'tropical':  {'spring': 1.1, 'summer': 1.0, 'autumn': 0.9, 'winter': 0.8,
                  'winter_upkeep': 1.0, 'cold_threshold': 0,  'cold_dmg': 0},
}

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

    @staticmethod
    def random():
        return Traits(
            strength=random.uniform(0.6, 1.4),
            speed=random.uniform(0.6, 1.4),
            perception=random.uniform(0.6, 1.4),
            endurance=random.uniform(0.6, 1.4),
            sociability=random.uniform(0.1, 0.9),
            risk_tolerance=random.uniform(0.1, 0.9),
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
        )

    def blend(self, other):
        return Traits(
            strength=(self.strength + other.strength) / 2,
            speed=(self.speed + other.speed) / 2,
            perception=(self.perception + other.perception) / 2,
            endurance=(self.endurance + other.endurance) / 2,
            sociability=(self.sociability + other.sociability) / 2,
            risk_tolerance=(self.risk_tolerance + other.risk_tolerance) / 2,
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
    skills: dict = field(default_factory=lambda: {'food_storage': 0.0, 'agriculture': 0.0})
    known_knowledge: dict = field(default_factory=lambda: {})  # knowledge_name -> {level, source, tick_learned}

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
        # Inherit knowledge from parents with some fidelity loss
        inherited_knowledge = {}
        for kname, kdata in parent.known_knowledge.items():
            # Children inherit parental knowledge with some degradation
            inherit_fidelity = random.uniform(0.7, 0.95)
            inherited_knowledge[kname] = {
                'level': kdata['level'] * inherit_fidelity,
                'source': f'inherited_from_{parent.name}',
                'tick_learned': tick
            }
        if partner and partner.known_knowledge:
            # Also inherit from partner, taking the best version
            for kname, kdata in partner.known_knowledge.items():
                if kname in inherited_knowledge:
                    # Take the better version
                    if kdata['level'] > inherited_knowledge[kname]['level']:
                        inherit_fidelity = random.uniform(0.7, 0.95)
                        inherited_knowledge[kname]['level'] = kdata['level'] * inherit_fidelity
                else:
                    inherit_fidelity = random.uniform(0.7, 0.95)
                    inherited_knowledge[kname] = {
                        'level': kdata['level'] * inherit_fidelity,
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
    child.skills = {'food_storage': inherited_knowledge.get('food_storage', {}).get('level', 0) * 100,
                    'agriculture': inherited_knowledge.get('agriculture', {}).get('level', 0) * 100}
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

    # Harvest from biomass
    if cell.biomass > 0:
        harvest = min(cell.biomass, 15 * r.traits.strength) * random.uniform(0.5, 1.0)
        effort = 0.5 / r.traits.endurance
        cell.biomass -= harvest
        gain = harvest * 0.8
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


def _do_interact(r, target_id, residents, tick):
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

    # Share food if one is hungry
    if r.energy > 60 and target.energy < 30 and r.traits.sociability > 0.4:
        share = min(15, r.energy - 50)
        r.energy -= share
        target.energy = min(MAX_ENERGY, target.energy + share * 0.9)
        r.bonds[target.id].quality = min(1.0, r.bonds[target.id].quality + 0.2)
        target.bonds[r.id].quality = min(1.0, target.bonds[r.id].quality + 0.3)
        return f'{r.name} shared food with {target.name}'

    # Exchange spatial memory (with distortion per RFC-0001 Law 6)
    r.bonds[target.id].quality = min(1.0, r.bonds[target.id].quality + 0.05)
    if r.memory and random.random() < 0.5:
        mem = random.choice(r.memory)
        distorted = MemEntry(mem.x, mem.y, mem.biomass * random.uniform(0.7, 1.3), tick)
        target.memory.append(distorted)
        if len(target.memory) > MEMORY_CAPACITY:
            target.memory.sort(key=lambda m: m.tick, reverse=True)
            target.memory = target.memory[:MEMORY_CAPACITY]

    # Knowledge transmission (oral tradition)
    # Higher sociability increases knowledge sharing probability
    if r.known_knowledge and random.random() < (r.traits.sociability * 0.4):
        # Pick a random knowledge the speaker has
        knowledge_name = random.choice(list(r.known_knowledge.keys()))
        speaker_knowledge = r.known_knowledge[knowledge_name]

        # Listener learns with some distortion and loss
        if knowledge_name not in target.known_knowledge:
            # First time hearing about this knowledge
            fidelity = random.uniform(0.6, 0.95) * (r.traits.sociability * 0.5 + 0.5)
            learned_level = speaker_knowledge['level'] * fidelity
            target.known_knowledge[knowledge_name] = {
                'level': learned_level,
                'source': f'learned_from_{r.name}',
                'tick_learned': tick
            }
            target.skills[knowledge_name] = learned_level * 100
            event_msg = f'{r.name} taught {target.name} about {knowledge_name}'
        else:
            # Reinforce existing knowledge
            existing_level = target.known_knowledge[knowledge_name]['level']
            fidelity = random.uniform(0.7, 0.98)
            improvement = (speaker_knowledge['level'] - existing_level) * fidelity * 0.3
            if improvement > 0:
                target.known_knowledge[knowledge_name]['level'] = min(1.0, existing_level + improvement)
                target.skills[knowledge_name] = target.known_knowledge[knowledge_name]['level'] * 100

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

        # Environment: biomass regrowth (zone-dependent season multiplier)
        for row in self.grid:
            for c in row:
                if c.biomass < c.biomass_cap:
                    m = c.season_mult(season)
                    c.biomass = min(c.biomass_cap, c.biomass + TERRAIN[c.terrain]['regrow'] * m)

        living = [r for r in self.residents if r.alive]
        random.shuffle(living)

        # Carrying capacity based on annual average food production per zone
        total_regrow = 0
        for row in self.grid:
            for c in row:
                if c.passable():
                    zone_cfg = CLIMATE_ZONES[c.climate]
                    avg_m = sum(zone_cfg[s] for s in SEASONS) / 4
                    total_regrow += TERRAIN[c.terrain]['regrow'] * avg_m
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

        for r in living:
            if not r.alive:
                continue
            r.age += 1

            # Upkeep — zone-dependent winter multiplier
            cost = r.upkeep()
            zone_cfg = CLIMATE_ZONES[climate_zone(r.y)]
            if season == 'winter':
                cost *= zone_cfg['winter_upkeep']
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

            # Winter exposure — zone-dependent cold damage
            cold_thr = zone_cfg['cold_threshold']
            cold_dmg = zone_cfg['cold_dmg']
            if season == 'winter' and cold_thr > 0 and r.energy < cold_thr:
                r.health -= cold_dmg * (1.0 - r.energy / cold_thr)

            # Winter starvation — if in non-tropical zone during winter and food scarce, high death rate
            if season == 'winter' and climate_zone(r.y) != 'tropical':
                here = self.grid[r.y][r.x]
                if here.biomass < 5 and here.leftover < 5 and r.energy < 30:
                    # Intense starvation pressure in winter — discovery moment
                    r.health -= 8  # Base starvation damage
                    if r.energy < 15:
                        r.health -= 12  # Extra damage if critically low
                    # Knowledge discovery: surviving winter hunger creates pressure to "learn" food storage
                    if 'food_storage' not in r.known_knowledge and random.random() < 0.08:
                        r.known_knowledge['food_storage'] = {
                            'level': random.uniform(0.2, 0.5),
                            'source': 'self-discovered',
                            'tick_learned': tick
                        }
                        r.skills['food_storage'] = r.known_knowledge['food_storage']['level'] * 100
                        evts.append({'tick': tick, 'type': 'discovery',
                                     'text': f'{r.name} discovered food storage during winter hardship',
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

            # Age decline — starts around age 35
            if r.age > 35:
                p = (r.age - 35) / 30 * 0.10
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
                msg = _do_interact(r, tid, self.residents, tick)
            elif action == 'raid':
                msg = _do_raid(r, tid, self.residents, tick)
            elif action == 'scavenge':
                msg = _do_scavenge(r, self.grid)
            elif action == 'reproduce':
                msg, self._next_id = _do_reproduce(r, tid, self.residents, self.grid, tick, self._next_id)

            if msg:
                evts.append({'tick': tick, 'type': action, 'text': msg, 'x': r.x, 'y': r.y})

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

        # Writing system emergence — pressure when knowledge degrades too much through oral transmission
        # When average skill degrades below threshold AND there's widespread knowledge,
        # high-sociability individuals discover symbolic recording
        if storage_holders > n * 0.3 and avg_storage_skill < 5.0 and not hasattr(self, '_has_writing'):
            # Someone invents writing/symbols
            candidates = [r for r in living if r.traits.sociability > 0.6 and 'food_storage' in r.known_knowledge]
            if candidates and random.random() < 0.15:
                inventor = random.choice(candidates)
                self._has_writing = True
                evts.append({'tick': tick, 'type': 'discovery',
                             'text': f'{inventor.name} invented a system of symbols to record knowledge!',
                             'x': inventor.x, 'y': inventor.y})
                # Give the inventor an upgraded skill to use writing
                inventor.known_knowledge['writing'] = {
                    'level': 0.5,
                    'source': 'invented',
                    'tick_learned': tick
                }
                inventor.skills['writing'] = 50.0

        # Writing transmission — much higher fidelity than oral tradition
        if hasattr(self, '_has_writing') and self._has_writing:
            writing_holders = sum(1 for r in living if 'writing' in r.known_knowledge)
            # Those who know writing can transmit knowledge with much higher fidelity
            for r in living:
                if 'writing' in r.known_knowledge and r.known_knowledge.get('food_storage', {}).get('level', 0) < 0.8:
                    # Can reinforce their own knowledge through written records
                    r.known_knowledge['food_storage'] = {
                        'level': min(0.8, (r.known_knowledge.get('food_storage', {}).get('level', 0) + 0.15)),
                        'source': 'written_records',
                        'tick_learned': tick
                    }
                    r.skills['food_storage'] = r.known_knowledge['food_storage']['level'] * 100

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
            'has_writing': getattr(self, '_has_writing', False),
            'writing_holders': sum(1 for r in living if 'writing' in r.known_knowledge) if hasattr(self, '_has_writing') else 0,
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
            for row in self.grid:
                for c in row:
                    terrain.append(c.terrain)
                    biomass.append(round(c.biomass, 1))
                    leftover.append(round(c.leftover, 1))

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
                'terrain': terrain, 'biomass': biomass, 'leftover': leftover,
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
