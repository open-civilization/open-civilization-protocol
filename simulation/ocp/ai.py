"""
OCP Slow-Tier AI Decision Module (RFC-0005)
Supports Anthropic, OpenAI, DeepSeek, Google Gemini.
"""

import httpx
import json
import random
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

log = logging.getLogger("ocp.ai")

PROVIDERS = {
    'anthropic': {
        'name': 'Anthropic',
        'url': 'https://api.anthropic.com/v1/messages',
        'models': [
            {'id': 'claude-sonnet-4-20250514', 'label': 'Claude Sonnet 4'},
            {'id': 'claude-haiku-4-5-20251001', 'label': 'Claude Haiku 4.5'},
        ],
    },
    'openai': {
        'name': 'OpenAI',
        'url': 'https://api.openai.com/v1/chat/completions',
        'models': [
            {'id': 'gpt-4o-mini', 'label': 'GPT-4o Mini'},
            {'id': 'gpt-4o', 'label': 'GPT-4o'},
        ],
    },
    'deepseek': {
        'name': 'DeepSeek',
        'url': 'https://api.deepseek.com/v1/chat/completions',
        'models': [
            {'id': 'deepseek-chat', 'label': 'DeepSeek Chat'},
        ],
    },
    'google': {
        'name': 'Google',
        'url': 'https://generativelanguage.googleapis.com/v1beta',
        'models': [
            {'id': 'gemini-2.0-flash', 'label': 'Gemini 2.0 Flash'},
            {'id': 'gemini-2.5-flash', 'label': 'Gemini 2.5 Flash'},
        ],
    },
}

SETTINGS_PATH = Path(__file__).resolve().parent.parent / "settings.json"

DEFAULT_SETTINGS = {
    'ai_enabled': False,
    'provider': 'anthropic',
    'providers': {
        'anthropic': {'api_key': '', 'model': 'claude-sonnet-4-20250514'},
        'openai':    {'api_key': '', 'model': 'gpt-4o-mini'},
        'deepseek':  {'api_key': '', 'model': 'deepseek-chat'},
        'google':    {'api_key': '', 'model': 'gemini-2.0-flash'},
    },
    'budget_per_season': 2,
    'max_calls_per_tick': 2,
}


def load_settings():
    if SETTINGS_PATH.exists():
        try:
            with open(SETTINGS_PATH) as f:
                saved = json.load(f)
            merged = {**DEFAULT_SETTINGS, **saved}
            merged['providers'] = {**DEFAULT_SETTINGS['providers'], **saved.get('providers', {})}
            return merged
        except Exception:
            pass
    return dict(DEFAULT_SETTINGS)


def save_settings(settings):
    with open(SETTINGS_PATH, 'w') as f:
        json.dump(settings, f, indent=2)


def mask_key(key: str) -> str:
    if not key or len(key) < 8:
        return '****' if key else ''
    return key[:4] + '****' + key[-4:]


def get_public_settings(settings):
    pub = dict(settings)
    pub['providers'] = {}
    for prov, conf in settings.get('providers', {}).items():
        pub['providers'][prov] = {
            'api_key': mask_key(conf.get('api_key', '')),
            'model': conf.get('model', ''),
            'has_key': bool(conf.get('api_key', '')),
        }
    pub['provider_info'] = {k: {'name': v['name'], 'models': v['models']} for k, v in PROVIDERS.items()}
    return pub


# ── LLM Calls ──

def call_llm(provider: str, api_key: str, model: str, prompt: str, max_tokens: int = 80, timeout: int = 20) -> Optional[str]:
    try:
        if provider == 'anthropic':
            return _call_anthropic(api_key, model, prompt, max_tokens, timeout)
        elif provider in ('openai', 'deepseek'):
            url = PROVIDERS[provider]['url']
            return _call_openai_compat(url, api_key, model, prompt, max_tokens, timeout)
        elif provider == 'google':
            return _call_google(api_key, model, prompt, max_tokens, timeout)
        return None
    except Exception as e:
        log.warning("LLM call failed: %s", e)
        return None


def _call_anthropic(key, model, prompt, max_tokens, timeout=20):
    r = httpx.post(
        PROVIDERS['anthropic']['url'],
        headers={
            'x-api-key': key,
            'anthropic-version': '2023-06-01',
            'content-type': 'application/json',
        },
        json={
            'model': model,
            'max_tokens': max_tokens,
            'messages': [{'role': 'user', 'content': prompt}],
        },
        timeout=timeout,
    )
    r.raise_for_status()
    return r.json()['content'][0]['text']


def _call_openai_compat(url, key, model, prompt, max_tokens, timeout=20):
    r = httpx.post(
        url,
        headers={
            'Authorization': f'Bearer {key}',
            'Content-Type': 'application/json',
        },
        json={
            'model': model,
            'max_tokens': max_tokens,
            'messages': [{'role': 'user', 'content': prompt}],
        },
        timeout=timeout,
    )
    r.raise_for_status()
    return r.json()['choices'][0]['message']['content']


def _call_google(key, model, prompt, max_tokens, timeout=20):
    url = f"{PROVIDERS['google']['url']}/models/{model}:generateContent?key={key}"
    r = httpx.post(
        url,
        headers={'Content-Type': 'application/json'},
        json={
            'contents': [{'parts': [{'text': prompt}]}],
            'generationConfig': {'maxOutputTokens': max_tokens},
        },
        timeout=timeout,
    )
    r.raise_for_status()
    return r.json()['candidates'][0]['content']['parts'][0]['text']


# ── Trigger Detection (RFC-0005) ──

def check_trigger(resident, nearby_residents, grid, tick):
    r = resident
    here = grid[r.y][r.x]

    # Trigger 1: First contact with a stranger
    for nr, dist in nearby_residents:
        if dist <= 1 and nr.id not in r.bonds:
            look = 'strong' if nr.traits.strength > 1.1 else 'tired' if nr.traits.endurance < 0.7 else 'ordinary'
            return 'first_contact', f"You see someone you have never met. They look {look} and are {dist} step(s) away."

    # Trigger 2: Resource crisis — hungry with no food nearby
    if r.energy < 450 and here.biomass < 5:
        return 'crisis', "You are very hungry and there is almost no food here."

    # Trigger 3: Surplus reflection — well-fed, healthy, occasional
    if r.energy > 2550 and r.health > 85 and r.age > 15 and random.random() < 0.08:
        return 'surplus', "You feel well-fed and safe. You have a moment to think."

    # Trigger 4: Cultural moment — a resident who depends on the same people repeatedly
    # for real cooperation (hunting, warning, sharing, care), or a knowledge-rich group
    # with no way to keep what it knows. This is narrative flavor only: the mechanical
    # discovery of spoken_language/writing in engine.py is a deterministic rule keyed on
    # cooperation, repeated contact, and population pressure, and does not depend on this
    # trigger firing or on the AI being enabled at all.
    if (len(r.bonds) >= 5 and r.energy > 1500 and r.age > 15
            and 'spoken_language' not in r.known_knowledge and random.random() < 0.05):
        return 'cultural_language', ("You rely on the same people again and again — to warn of danger, "
                                      "to share food, to help with the young. A cry or a grunt isn't "
                                      "enough anymore. You keep wanting a sound that always means the "
                                      "same thing.")
    if ('spoken_language' in r.known_knowledge and 'writing' not in r.known_knowledge
            and len(r.known_knowledge) >= 3 and r.energy > 1650 and random.random() < 0.05):
        return 'cultural_writing', ("Your people now know more than any one person can hold in memory. "
                                     "Stories get told wrong. You wonder if marks on stone or wood could "
                                     "hold what memory loses.")

    return None, None


# ── Prompt Construction (RFC-0005: observation window only) ──

def build_prompt(resident, grid, nearby_cells, nearby_residents, trigger_text, trigger_type=None):
    r = resident
    here = grid[r.y][r.x]

    # What the resident sees
    perception_lines = []
    for cell, dist in nearby_cells[:8]:
        food = 'rich' if cell.biomass > 50 else 'some' if cell.biomass > 15 else 'scarce'
        w = ', water' if cell.water else ''
        where = 'here' if dist == 0 else f'{dist} steps away'
        perception_lines.append(f"  {cell.terrain} ({food} food{w}) — {where}")

    # People nearby
    social_lines = []
    for nr, dist in nearby_residents[:5]:
        bond = r.bonds.get(nr.id)
        if bond:
            rel = 'friend' if bond.quality > 0.3 else 'acquaintance'
        else:
            rel = 'stranger'
        social_lines.append(f"  {nr.name} ({rel}, {dist} step(s) away)")

    # Personality
    traits = []
    if r.traits.sociability > 0.6: traits.append('social')
    elif r.traits.sociability < 0.3: traits.append('solitary')
    if r.traits.risk_tolerance > 0.6: traits.append('bold')
    elif r.traits.risk_tolerance < 0.3: traits.append('cautious')
    if r.traits.strength > 1.2: traits.append('strong')
    if r.traits.endurance > 1.2: traits.append('tough')

    perception = '\n'.join(perception_lines) if perception_lines else '  Nothing notable'
    social = '\n'.join(social_lines) if social_lines else '  No one'
    personality = ', '.join(traits) if traits else 'unremarkable'

    energy_desc = 'starving' if r.energy < 450 else 'hungry' if r.energy < 1050 else 'adequate' if r.energy < 1950 else 'well-fed'
    health_desc = 'injured' if r.health < 40 else 'tired' if r.health < 70 else 'healthy'

    header = f"""You are {r.name}. You live in a wild world. You know nothing about Earth or human history — only what you have seen and been told.

State: {energy_desc} (energy {r.energy:.0f}/3000 kcal), {health_desc} (health {r.health:.0f}/100), age {r.age}
Where: ({r.x},{r.y}) on {here.terrain}
Personality: {personality}

What you see:
{perception}

People nearby:
{social}

Situation: {trigger_text}
"""

    if trigger_type == 'cultural_language':
        return header + "\nInvent ONE short spoken word or sound for something you deal with constantly (food, water, danger, a person). Reply in under 20 words: the word and what it means."
    if trigger_type == 'cultural_writing':
        return header + "\nInvent ONE simple mark or symbol you could scratch or draw to represent something important. Reply in under 20 words: describe the mark and what it stands for."

    return header + "\nWhat do you do? Pick ONE: move, forage, rest, approach someone, share food, or explore a new direction.\nReply in under 30 words with your action and a short reason."


# ── Response Parsing ──

def parse_response(text, nearby_residents):
    if not text:
        return None
    t = text.lower()

    if any(w in t for w in ('forage', 'gather', 'eat', 'hunt', 'fish')):
        return ('forage', None, None, None)

    if any(w in t for w in ('rest', 'sleep', 'recover', 'heal')):
        return ('rest', None, None, None)

    if any(w in t for w in ('share', 'give', 'offer', 'help')):
        if nearby_residents:
            return ('interact', None, None, nearby_residents[0][0].id)

    if any(w in t for w in ('approach', 'talk', 'greet', 'interact', 'meet', 'introduce')):
        if nearby_residents:
            return ('interact', None, None, nearby_residents[0][0].id)

    if any(w in t for w in ('move', 'explore', 'travel', 'migrate', 'walk', 'leave', 'wander')):
        return None  # let fast tier pick direction

    return None


# ── Orchestrator ──

class AIEngine:
    def __init__(self):
        self.settings = load_settings()
        self.executor = ThreadPoolExecutor(max_workers=3)
        self.pending = {}   # resident_id -> Future
        self.overrides = {} # resident_id -> (action_tuple, ai_text)
        self.total_calls = 0
        self.total_errors = 0
        self.recent_decisions = []  # last N AI decisions for display

    def update_settings(self, new_settings):
        for key in ('ai_enabled', 'provider', 'budget_per_season', 'max_calls_per_tick'):
            if key in new_settings:
                self.settings[key] = new_settings[key]
        if 'providers' in new_settings:
            for prov, conf in new_settings['providers'].items():
                if prov in self.settings['providers']:
                    if conf.get('api_key') and not conf['api_key'].startswith('****'):
                        self.settings['providers'][prov]['api_key'] = conf['api_key']
                    if conf.get('model'):
                        self.settings['providers'][prov]['model'] = conf['model']
        save_settings(self.settings)

    def process_tick(self, residents, grid, nearby_fn, tick):
        if not self.settings.get('ai_enabled'):
            return

        # Collect completed futures
        for rid, future in list(self.pending.items()):
            if future.done():
                try:
                    result = future.result()
                    if result:
                        action, ai_text, rname = result
                        if action:
                            self.overrides[rid] = (action, ai_text)
                        self.recent_decisions.append({
                            'tick': tick, 'resident': rname,
                            'response': ai_text[:120] if ai_text else '(no response)',
                        })
                        if len(self.recent_decisions) > 30:
                            self.recent_decisions = self.recent_decisions[-30:]
                except Exception:
                    self.total_errors += 1
                del self.pending[rid]

        # Don't submit new calls if too many are already queued
        max_pending = self.executor._max_workers * 2
        if len(self.pending) >= max_pending:
            return

        # Find new triggers
        provider = self.settings['provider']
        prov_conf = self.settings['providers'].get(provider, {})
        api_key = prov_conf.get('api_key', '')
        model = prov_conf.get('model', '')
        if not api_key:
            return

        budget = self.settings.get('budget_per_season', 2)
        max_per_tick = self.settings.get('max_calls_per_tick', 2)
        season_tick = tick % 25  # reset budget each season

        calls_this_tick = 0
        living = [r for r in residents if r.alive]
        random.shuffle(living)

        for r in living:
            if calls_this_tick >= max_per_tick:
                break
            if r.id in self.pending or r.id in self.overrides:
                continue

            # Budget check (stored on resident as _ai_calls)
            if not hasattr(r, '_ai_calls'):
                r._ai_calls = 0
            if season_tick == 0:
                r._ai_calls = 0
            if r._ai_calls >= budget:
                continue

            nr = nearby_fn(r)
            trigger_type, trigger_text = check_trigger(r, nr, grid, tick)
            if trigger_type is None:
                continue

            nearby_cells_data = []
            radius = r.view_radius()
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    nx, ny = r.x + dx, r.y + dy
                    if 0 <= nx < len(grid[0]) and 0 <= ny < len(grid) and abs(dx) + abs(dy) <= radius:
                        nearby_cells_data.append((grid[ny][nx], abs(dx) + abs(dy)))

            prompt = build_prompt(r, grid, nearby_cells_data, nr, trigger_text, trigger_type)
            r._ai_calls += 1
            self.total_calls += 1
            calls_this_tick += 1

            rname = r.name
            nr_snapshot = [(n, d) for n, d in nr]
            is_cultural = trigger_type in ('cultural_language', 'cultural_writing')

            def _do_call(p=prompt, prov=provider, key=api_key, mdl=model, nrs=nr_snapshot, name=rname, cultural=is_cultural):
                text = call_llm(prov, key, mdl, p)
                if cultural:
                    # Narrative-only: the mechanical discovery is decided deterministically
                    # in engine.py. A benign no-op action just lets the invented word/mark
                    # surface as an event through the normal AI-decision log.
                    action = ('rest', None, None, None) if text else None
                else:
                    action = parse_response(text, nrs) if text else None
                return action, text, name

            self.pending[r.id] = self.executor.submit(_do_call)

    def get_override(self, resident_id):
        if resident_id in self.overrides:
            action, ai_text = self.overrides.pop(resident_id)
            return action, ai_text
        return None, None

    def get_stats(self):
        return {
            'total_calls': self.total_calls,
            'total_errors': self.total_errors,
            'pending': len(self.pending),
            'recent': self.recent_decisions[-10:],
        }
