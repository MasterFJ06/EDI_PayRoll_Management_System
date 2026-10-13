import re

from app.infrastructure.security.refresh_token import (
    generate_refresh_token,
    hash_refresh_token,
)


def test_refresh_token_is_opaque_random_and_hash_is_sha256() -> None:
    first = generate_refresh_token()
    second = generate_refresh_token()

    assert first != second
    assert re.fullmatch(r"[A-Za-z0-9_-]+", first)
    assert len(first) >= 64
    assert hash_refresh_token(first) == hash_refresh_token(first)
    assert hash_refresh_token(first) != first
    assert re.fullmatch(r"[0-9a-f]{64}", hash_refresh_token(first))
