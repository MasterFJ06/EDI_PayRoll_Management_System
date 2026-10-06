import jwt

from app.core.config import get_settings
from app.infrastructure.security.jwt import create_access_token
from app.infrastructure.security.jwt import (
    create_access_token,
    decode_access_token,
)
import pytest

def test_create_access_token() -> None:
    token = create_access_token(
        user_id=1,
        username="john",
    )

    settings = get_settings()

    payload = jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )

    assert payload["sub"] == "1"
    assert payload["username"] == "john"
    assert payload["type"] == "access"
    assert "iat" in payload
    assert "exp" in payload

def test_decode_access_token() -> None:
    token = create_access_token(
        user_id=1,
        username="john",
    )

    payload = decode_access_token(token)

    assert payload["sub"] == "1"
    assert payload["username"] == "john"
    assert payload["type"] == "access"


def test_decode_access_token_rejects_invalid_token() -> None:
    with pytest.raises(ValueError, match="Invalid access token."):
        decode_access_token("not-a-valid-token")


def test_decode_access_token_rejects_wrong_token_type() -> None:
    settings = get_settings()

    token = jwt.encode(
        {
            "sub": "1",
            "username": "john",
            "type": "refresh",
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(ValueError, match="Invalid access token type."):
        decode_access_token(token)