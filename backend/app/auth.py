"""
Minimal token-based authentication for V1.

Two tokens exist:
    USER_TOKEN  - used by the frontend / PWA (human user)
    AGENT_TOKEN - used by the local PC agent (agent/run_agent.py)

Both are read from environment variables (see .env.example). Nothing
is hardcoded. This is intentionally simple for V1 - it is NOT a full
OAuth/JWT system. That can be added later without touching callers,
since everything goes through these two dependency functions.
"""
from __future__ import annotations

import secrets

from fastapi import Header, HTTPException, status

from app.config import get_settings


def _tokens_match(a: str, b: str) -> bool:
    """Constant-time comparison - a plain `!=` leaks how many leading
    characters matched via response timing, letting an attacker with
    network access recover the token byte-by-byte over many requests."""
    return secrets.compare_digest(a, b)


def _extract_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header.",
        )
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header must be 'Bearer <token>'.",
        )
    return parts[1]


def require_user(authorization: str | None = Header(default=None)) -> str:
    """Dependency for endpoints called by the human user's client (PWA)."""
    settings = get_settings()
    token = _extract_token(authorization)
    if not _tokens_match(token, settings.USER_TOKEN):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user token.")
    return token


def require_agent(authorization: str | None = Header(default=None)) -> str:
    """Dependency for endpoints called only by the local PC agent."""
    settings = get_settings()
    token = _extract_token(authorization)
    if not _tokens_match(token, settings.AGENT_TOKEN):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid agent token.")
    return token


def require_user_or_agent(authorization: str | None = Header(default=None)) -> str:
    """Dependency for endpoints either side may call (e.g. reading tasks)."""
    settings = get_settings()
    token = _extract_token(authorization)
    if not (_tokens_match(token, settings.USER_TOKEN) or _tokens_match(token, settings.AGENT_TOKEN)):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")
    return token
