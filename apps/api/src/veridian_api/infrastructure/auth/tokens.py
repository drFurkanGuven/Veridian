from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

import jwt

from veridian_api.core.config import Settings
from veridian_api.core.exceptions import UnauthorizedError


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def create_access_token(user_id: UUID, settings: Settings) -> tuple[str, int]:
    expires_in = settings.jwt_access_token_expire_minutes * 60
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    payload = {
        "sub": str(user_id),
        "exp": expires_at,
        "type": "access",
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, expires_in


def decode_access_token(token: str, settings: Settings) -> UUID:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.PyJWTError as exc:
        raise UnauthorizedError("Invalid or expired access token") from exc

    if payload.get("type") != "access":
        raise UnauthorizedError("Invalid token type")

    sub = payload.get("sub")
    if not sub:
        raise UnauthorizedError("Invalid token subject")

    return UUID(str(sub))


def create_oauth_state(provider: str, settings: Settings) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    payload: dict[str, Any] = {
        "provider": provider,
        "type": "oauth_state",
        "exp": expires_at,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def verify_oauth_state(state: str, provider: str, settings: Settings) -> None:
    try:
        payload = jwt.decode(
            state,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.PyJWTError as exc:
        raise UnauthorizedError("Invalid OAuth state") from exc

    if payload.get("type") != "oauth_state" or payload.get("provider") != provider:
        raise UnauthorizedError("Invalid OAuth state")


def refresh_token_expires_at(settings: Settings) -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_token_expire_days)
