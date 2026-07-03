"""Standalone AI-provider settings for the Simulation Scientist Agent.

Deliberately kept separate from simulation.ocp.ai's settings.json. The agent
(theory discovery + rule-change proposals) is a different consumer than
resident decision-making — it should be free to run a different provider,
model, or key than the live simulation's AI, configured independently via
its own panel in the Agent tab.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from simulation.ocp.ai import PROVIDERS, mask_key
except ModuleNotFoundError:
    from ocp.ai import PROVIDERS, mask_key

SETTINGS_PATH = Path(__file__).resolve().parent / "agent_settings.json"

DEFAULT_SETTINGS: dict[str, Any] = {
    "provider": "anthropic",
    "providers": {
        "anthropic": {"api_key": "", "model": "claude-sonnet-4-20250514"},
        "openai": {"api_key": "", "model": "gpt-4o-mini"},
        "deepseek": {"api_key": "", "model": "deepseek-chat"},
        "google": {"api_key": "", "model": "gemini-2.0-flash"},
    },
}


def load_settings() -> dict[str, Any]:
    if SETTINGS_PATH.exists():
        try:
            saved = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
            merged = {**DEFAULT_SETTINGS, **saved}
            merged["providers"] = {**DEFAULT_SETTINGS["providers"], **saved.get("providers", {})}
            return merged
        except Exception:
            pass
    return json.loads(json.dumps(DEFAULT_SETTINGS))


def save_settings(settings: dict[str, Any]) -> None:
    SETTINGS_PATH.write_text(json.dumps(settings, indent=2), encoding="utf-8")


def update_settings(new_settings: dict[str, Any]) -> dict[str, Any]:
    """Merges into the current settings — a key is only overwritten if a real
    (non-masked) value was sent, so re-saving without retyping the key doesn't
    wipe it, matching simulation.ocp.ai.AIEngine.update_settings's contract."""
    settings = load_settings()
    if "provider" in new_settings:
        settings["provider"] = new_settings["provider"]
    if "providers" in new_settings:
        for prov, conf in new_settings["providers"].items():
            if prov in settings["providers"]:
                if conf.get("api_key") and not str(conf["api_key"]).startswith("****"):
                    settings["providers"][prov]["api_key"] = conf["api_key"]
                if conf.get("model"):
                    settings["providers"][prov]["model"] = conf["model"]
    save_settings(settings)
    return settings


def get_public_settings(settings: dict[str, Any]) -> dict[str, Any]:
    pub = dict(settings)
    pub["providers"] = {}
    for prov, conf in settings.get("providers", {}).items():
        pub["providers"][prov] = {
            "api_key": mask_key(conf.get("api_key", "")),
            "model": conf.get("model", ""),
            "has_key": bool(conf.get("api_key", "")),
        }
    pub["provider_info"] = {k: {"name": v["name"], "models": v["models"]} for k, v in PROVIDERS.items()}
    return pub
