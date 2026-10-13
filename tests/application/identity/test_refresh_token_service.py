from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.application.identity.refresh_token_service import RefreshTokenService
from app.domain.shared.exceptions import BusinessRuleViolation
from app.infrastructure.persistence.models.refresh_token import RefreshToken


NOW = datetime(2026, 10, 13, 12, 0, 0)


class FakeRefreshRepository:
    def __init__(self, rows=()) -> None:
        self.rows = list(rows)

    def get_database_time(self):
        return NOW

    def get_by_token_hash_for_update(self, token_hash):
        return next((row for row in self.rows if row.token_hash == token_hash), None)

    def add(self, row):
        self.rows.append(row)
        return row

    def revoke(self, row, timestamp):
        row.revoked_at = timestamp

    def revoke_family(self, family_id, timestamp):
        changed = 0
        for row in self.rows:
            if row.family_id == family_id and row.revoked_at is None:
                row.revoked_at = timestamp
                changed += 1
        return changed


def _uow(rows=(), users=None):
    uow = Mock()
    uow.refresh_tokens = FakeRefreshRepository(rows)
    uow.users = SimpleNamespace(
        get_by_id=lambda user_id: (users or {}).get(user_id),
        get_by_id_for_update=lambda user_id: (users or {}).get(user_id),
    )
    return uow


def test_issue_persists_hash_only_with_configured_expiration(monkeypatch) -> None:
    from app.application.identity import refresh_token_service as module

    user = SimpleNamespace(user_id=7, username="refresh-user", status="ACTIVE")
    uow = _uow(users={7: user})
    monkeypatch.setattr(module, "get_settings", lambda: SimpleNamespace(refresh_token_expire_days=7))
    monkeypatch.setattr(module, "generate_refresh_token", lambda: "plain-secret")

    issued = RefreshTokenService(uow).issue(user)

    row = uow.refresh_tokens.rows[0]
    assert issued == "plain-secret"
    assert row.token_hash != issued
    assert row.token_hash == module.hash_refresh_token(issued)
    assert row.expires_at == NOW + timedelta(days=7)
    assert row.family_id
    uow.commit.assert_called_once()


def test_issue_rejects_inactive_user_without_persisting_token() -> None:
    user = SimpleNamespace(user_id=7, username="refresh-user", status="DISABLED")
    uow = _uow(users={7: user})

    with pytest.raises(BusinessRuleViolation, match="User account is not active"):
        RefreshTokenService(uow).issue(user)

    assert uow.refresh_tokens.rows == []
    uow.rollback.assert_called_once()
    uow.commit.assert_not_called()


def test_rotation_consumes_old_and_creates_replacement_in_same_family(monkeypatch) -> None:
    from app.application.identity import refresh_token_service as module

    user = SimpleNamespace(user_id=7, username="refresh-user", status="ACTIVE")
    monkeypatch.setattr(module, "generate_refresh_token", lambda: "replacement")
    old = RefreshToken(
        user_id=7, family_id="family-a", token_hash=module.hash_refresh_token("old"),
        expires_at=NOW + timedelta(days=1),
    )
    uow = _uow([old], {7: user})

    pair = RefreshTokenService(uow).rotate("old")

    assert pair is not None and pair.user is user and pair.refresh_token == "replacement"
    assert old.revoked_at == NOW
    assert len(uow.refresh_tokens.rows) == 2
    assert uow.refresh_tokens.rows[1].family_id == old.family_id
    assert uow.refresh_tokens.rows[1].token_hash == module.hash_refresh_token("replacement")
    uow.commit.assert_called_once()


@pytest.mark.parametrize("condition", ["missing", "expired", "inactive", "unknown-user"])
def test_invalid_rotation_does_not_issue_replacement(condition: str) -> None:
    from app.infrastructure.security.refresh_token import hash_refresh_token

    user = SimpleNamespace(user_id=7, username="refresh-user", status="ACTIVE")
    row = RefreshToken(
        user_id=7, family_id="family-a", token_hash=hash_refresh_token("known"),
        expires_at=NOW - timedelta(seconds=1) if condition == "expired" else NOW + timedelta(days=1),
        revoked_at=NOW if condition == "missing" else None,
    )
    if condition == "missing":
        rows, users, credential = [], {7: user}, "unknown"
    elif condition == "inactive":
        user.status = "DISABLED"
        rows, users, credential = [row], {7: user}, "known"
    elif condition == "unknown-user":
        rows, users, credential = [row], {}, "known"
    else:
        rows, users, credential = [row], {7: user}, "known"
    uow = _uow(rows, users)

    result = RefreshTokenService(uow).rotate(credential)

    assert result is None
    if condition in {"inactive", "unknown-user"}:
        uow.commit.assert_called_once()
        assert row.revoked_at == NOW
    else:
        uow.commit.assert_not_called()
    assert len(uow.refresh_tokens.rows) == len(rows)


def test_replay_revokes_only_its_family() -> None:
    from app.infrastructure.security.refresh_token import hash_refresh_token

    old = RefreshToken(
        user_id=7, family_id="family-a", token_hash=hash_refresh_token("used"),
        expires_at=NOW + timedelta(days=1), revoked_at=NOW - timedelta(seconds=1),
    )
    active_same = RefreshToken(
        user_id=7, family_id="family-a", token_hash=hash_refresh_token("new"),
        expires_at=NOW + timedelta(days=1),
    )
    other_session = RefreshToken(
        user_id=7, family_id="family-b", token_hash=hash_refresh_token("other"),
        expires_at=NOW + timedelta(days=1),
    )
    uow = _uow([old, active_same, other_session])

    assert RefreshTokenService(uow).rotate("used") is None

    assert active_same.revoked_at == NOW
    assert other_session.revoked_at is None
    uow.commit.assert_called_once()


def test_logout_is_idempotent_and_revokes_only_associated_family() -> None:
    from app.infrastructure.security.refresh_token import hash_refresh_token

    requested = RefreshToken(
        user_id=7, family_id="family-a", token_hash=hash_refresh_token("logout"),
        expires_at=NOW + timedelta(days=1),
    )
    same_family = RefreshToken(
        user_id=7, family_id="family-a", token_hash=hash_refresh_token("rotated"),
        expires_at=NOW + timedelta(days=1),
    )
    other = RefreshToken(
        user_id=7, family_id="family-b", token_hash=hash_refresh_token("other"),
        expires_at=NOW + timedelta(days=1),
    )
    uow = _uow([requested, same_family, other])

    assert RefreshTokenService(uow).logout("logout") is True
    assert RefreshTokenService(uow).logout("logout") is True
    assert requested.revoked_at == NOW
    assert same_family.revoked_at == NOW
    assert other.revoked_at is None
    assert uow.commit.call_count == 2
