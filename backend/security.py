"""Signed, expiry-bound session cookies for the ECS application."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time


COOKIE_NAME = "zhike_session"
MAX_AGE_SECONDS = 60 * 60 * 24 * 7
# A missing local development secret gets a new random value per process. It is
# deliberately not deterministic, so restarting a local server invalidates old
# cookies. Production must inject ZHIKE_SESSION_SECRET through its server env.
_PROCESS_SECRET = os.getenv("ZHIKE_SESSION_SECRET") or secrets.token_urlsafe(48)


def is_production() -> bool:
    return os.getenv("ZHIKE_ENV", "development").lower() == "production"


def session_secret_configured() -> bool:
    return bool(os.getenv("ZHIKE_SESSION_SECRET"))


def _encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def create_session_token(user_id: str) -> str:
    payload = {"sub": user_id, "exp": int(time.time()) + MAX_AGE_SECONDS}
    raw = _encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = _encode(hmac.new(_PROCESS_SECRET.encode("utf-8"), raw.encode("ascii"), hashlib.sha256).digest())
    return f"{raw}.{signature}"


def verify_session_token(token: str | None) -> str | None:
    if not token or "." not in token:
        return None
    raw, signature = token.rsplit(".", 1)
    expected = _encode(hmac.new(_PROCESS_SECRET.encode("utf-8"), raw.encode("ascii"), hashlib.sha256).digest())
    if not hmac.compare_digest(signature, expected):
        return None
    try:
        payload = json.loads(_decode(raw))
        if not isinstance(payload.get("sub"), str) or int(payload.get("exp", 0)) < time.time():
            return None
        return payload["sub"]
    except (ValueError, TypeError, json.JSONDecodeError):
        return None
