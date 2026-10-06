from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from app.core.config import get_settings


settings = get_settings()


def create_access_token(
    user_id: int,
    username: str,
) -> str:
    """Create a JWT access token for an authenticated user."""

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(
        minutes=settings.access_token_expire_minutes
    )

    payload: dict[str, Any] = {
        "sub": str(user_id),
        "username": username,
        "type": "access",
        "iat": now,
        "exp": expires_at,
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT access token."""

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.PyJWTError as exc:
        raise ValueError("Invalid access token.") from exc

    if payload.get("type") != "access":
        raise ValueError("Invalid access token type.")

    if payload.get("sub") is None:
        raise ValueError("Access token subject is missing.")

    return payload