"""Cryptographic helpers for opaque refresh credentials."""

import hashlib
import secrets


def generate_refresh_token() -> str:
    """Return a high-entropy opaque refresh secret."""

    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    """Return the lowercase SHA-256 hex digest used for persistence."""

    return hashlib.sha256(token.encode("utf-8")).hexdigest()
