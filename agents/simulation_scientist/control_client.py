"""HTTP client for the sandbox's agent config/trigger store.

Every call here is initiated by the polling machine (this one) — the sandbox
(simulation/ocp/server.py + agent_control.py) never calls out on its own.
"""

from __future__ import annotations

from typing import Any

import httpx


class ControlClient:
    def __init__(self, server_url: str, timeout: float = 15.0):
        self.base = server_url.rstrip("/")
        self.timeout = timeout

    def _get(self, path: str) -> dict[str, Any]:
        resp = httpx.get(f"{self.base}{path}", timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, json_body: dict[str, Any] | None = None) -> dict[str, Any]:
        resp = httpx.post(f"{self.base}{path}", json=json_body or {}, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def get_control(self) -> dict[str, Any]:
        return self._get("/api/agent/control")

    def claim_run(self) -> tuple[bool, dict[str, Any]]:
        result = self._post("/api/agent/control/claim")
        return bool(result.get("claimed")), result.get("state", {})

    def report_run(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._post("/api/agent/control/report", payload)

    def get_settings(self) -> dict[str, Any]:
        """Unmasked settings (real API key) — for driving the LLM, never for display."""
        return self._get("/api/agent/settings/raw")

    def is_stop_requested(self) -> bool:
        return bool(self.get_control().get("stop_requested"))
