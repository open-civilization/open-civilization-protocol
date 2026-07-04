"""Short-lived GitHub App installation tokens for the autonomous push path.

The org disables classic SSH deploy keys, so scheduler.py authenticates as a
GitHub App instead: sign a short-lived JWT with the App's private key, trade
it for an installation access token (valid ~1 hour), and use that token as
the password half of an HTTPS git remote for a single push. No long-lived
credential is ever written into git config or kept around after the push.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

import httpx
import jwt

APP_ID_PATH = Path("/home/ubuntu/ocp-simulation/.github_app_id")
INSTALLATION_ID_PATH = Path("/home/ubuntu/ocp-simulation/.github_app_installation_id")
PRIVATE_KEY_PATH = Path("/home/ubuntu/ocp-simulation/.github_app_key.pem")


def _read_config() -> tuple[Optional[str], Optional[str], Optional[str]]:
    app_id = APP_ID_PATH.read_text(encoding="utf-8").strip() if APP_ID_PATH.exists() else None
    installation_id = INSTALLATION_ID_PATH.read_text(encoding="utf-8").strip() if INSTALLATION_ID_PATH.exists() else None
    private_key = PRIVATE_KEY_PATH.read_text(encoding="utf-8") if PRIVATE_KEY_PATH.exists() else None
    return app_id, installation_id, private_key


def is_configured() -> bool:
    app_id, installation_id, private_key = _read_config()
    return bool(app_id and installation_id and private_key)


def get_installation_token() -> tuple[Optional[str], str]:
    """Returns (token, message). token is None if not configured or the exchange failed."""
    app_id, installation_id, private_key = _read_config()
    if not (app_id and installation_id and private_key):
        return None, "GitHub App not configured (missing app id, installation id, or private key)."

    now = int(time.time())
    payload = {"iat": now - 60, "exp": now + 9 * 60, "iss": app_id}
    try:
        encoded_jwt = jwt.encode(payload, private_key, algorithm="RS256")
    except Exception as exc:  # noqa: BLE001
        return None, f"Failed to sign JWT with the App private key: {exc!r}"

    try:
        resp = httpx.post(
            f"https://api.github.com/app/installations/{installation_id}/access_tokens",
            headers={
                "Authorization": f"Bearer {encoded_jwt}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=20,
        )
    except Exception as exc:  # noqa: BLE001
        return None, f"Token exchange request failed: {exc!r}"

    if resp.status_code != 201:
        return None, f"Token exchange failed ({resp.status_code}): {resp.text[:300]}"

    token = resp.json().get("token")
    if not token:
        return None, "Token exchange succeeded but response had no 'token' field."
    return token, "OK"
