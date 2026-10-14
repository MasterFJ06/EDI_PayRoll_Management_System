from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies.unit_of_work import get_unit_of_work
from app.infrastructure.persistence.models.user import User
from app.infrastructure.security.password import hash_password
from app.infrastructure.security.refresh_token import hash_refresh_token
from app.main import app


class FakeRefreshRepository:
    def __init__(self):
        self.rows = []

    def get_database_time(self):
        return datetime(2026, 10, 13, 12)

    def add(self, row):
        row.token_id = len(self.rows) + 1
        self.rows.append(row)
        return row

    def get_by_token_hash_for_update(self, value):
        return next((row for row in self.rows if row.token_hash == value), None)

    def revoke(self, row, timestamp):
        row.revoked_at = timestamp

    def revoke_family(self, family_id, timestamp):
        for row in self.rows:
            if row.family_id == family_id and row.revoked_at is None:
                row.revoked_at = timestamp
        return 1


class AuthUnitOfWork:
    def __init__(self):
        self.user = User(
            username="auth-user", email="auth@example.invalid",
            password_hash=hash_password("CorrectPass123!"), status="ACTIVE",
        )
        self.user.user_id = 9
        self.users = SimpleNamespace(
            get_by_username=lambda username: self.user if username == self.user.username else None,
            get_by_id=lambda user_id: self.user if user_id == self.user.user_id else None,
            get_by_id_for_update=lambda user_id: self.user if user_id == self.user.user_id else None,
        )
        self.refresh_tokens = FakeRefreshRepository()
        self.commit_count = 0
        self.rollback_count = 0

    def commit(self):
        self.commit_count += 1

    def rollback(self):
        self.rollback_count += 1


@pytest.fixture
def auth_uow():
    uow = AuthUnitOfWork()
    app.dependency_overrides[get_unit_of_work] = lambda: uow
    yield uow
    app.dependency_overrides.clear()


def test_login_keeps_access_fields_and_adds_hash_only_refresh_token(auth_uow):
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "auth-user", "password": "CorrectPass123!"},
        )
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"access_token", "refresh_token", "token_type"}
    assert body["access_token"] and body["token_type"] == "bearer"
    assert auth_uow.refresh_tokens.rows[0].token_hash == hash_refresh_token(body["refresh_token"])
    assert body["refresh_token"] not in auth_uow.refresh_tokens.rows[0].token_hash


def test_inactive_user_cannot_receive_refresh_token(auth_uow):
    auth_uow.user.status = "DISABLED"
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "auth-user", "password": "CorrectPass123!"},
        )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "BUSINESS_RULE_VIOLATION"
    assert auth_uow.refresh_tokens.rows == []
    assert auth_uow.commit_count == 0


def test_refresh_and_logout_contract_and_malformed_body(auth_uow, monkeypatch):
    from app.application.identity import refresh_token_service

    monkeypatch.setattr(refresh_token_service, "generate_refresh_token", lambda: "replacement-token")
    with TestClient(app) as client:
        login = client.post(
            "/api/v1/auth/login",
            json={"username": "auth-user", "password": "CorrectPass123!"},
        )
        old = login.json()["refresh_token"]
        rotated = client.post("/api/v1/auth/refresh", json={"refresh_token": old})
        replay = client.post("/api/v1/auth/refresh", json={"refresh_token": old})
        malformed = client.post("/api/v1/auth/refresh", json={})
        logout = client.post("/api/v1/auth/logout", json={"refresh_token": "replacement-token"})
        repeated_logout = client.post("/api/v1/auth/logout", json={"refresh_token": "replacement-token"})
        unknown_logout = client.post("/api/v1/auth/logout", json={"refresh_token": "unknown-token"})

    assert rotated.status_code == 200
    assert rotated.json()["refresh_token"] == "replacement-token"
    assert replay.status_code == 401
    assert replay.json() == {"detail": "Invalid or expired refresh token."}
    assert malformed.status_code == 422
    assert logout.status_code == repeated_logout.status_code == 204
    assert unknown_logout.status_code == 401
    assert unknown_logout.json() == {"detail": "Invalid or expired refresh token."}
    assert auth_uow.commit_count == 5
