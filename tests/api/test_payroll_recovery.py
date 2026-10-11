from collections.abc import Generator
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies.unit_of_work import get_unit_of_work
from app.infrastructure.security.jwt import create_access_token
from app.main import app


class RecoveryRunRepository:
    def __init__(self) -> None:
        self.run = SimpleNamespace(
            payroll_run_id=42,
            payroll_year=2026,
            payroll_month=10,
            status="PROCESSING",
            initiated_by_user_id=12,
            attempt_number=3,
            attempt_lease_expires_at=datetime(2026, 10, 1, 11, 59),
        )
        self.missing = False
        self.expired = True

    def get_by_id(self, run_id: int):
        return None if self.missing or run_id != 42 else self.run

    def lock_expired_processing_attempt(self, run_id: int):
        if run_id != 42 or not self.expired or self.run.status != "PROCESSING":
            return None
        return self.run

    def recover_expired_attempt(self, run_id: int, attempt_number: int) -> bool:
        if (
            run_id != 42
            or self.run.status != "PROCESSING"
            or self.run.attempt_number != attempt_number
            or not self.expired
        ):
            return False
        self.run.status = "FAILED"
        self.run.attempt_lease_expires_at = None
        return True


class RecoveryAuditRepository:
    def __init__(self) -> None:
        self.events = []

    def add(self, event, changes=()):
        self.events.append((event, list(changes)))
        return event


class RecoveryUnitOfWork:
    def __init__(self) -> None:
        self.user = SimpleNamespace(user_id=12, username="recovery-test", status="ACTIVE")
        self.users = SimpleNamespace(get_by_id=lambda user_id: self.user)
        self.authorization = SimpleNamespace(has_permission=Mock(return_value=True))
        self.payroll_runs = RecoveryRunRepository()
        self.audit_events = RecoveryAuditRepository()
        self.commit_count = 0

    def commit(self) -> None:
        self.commit_count += 1


@pytest.fixture
def recovery_uow() -> Generator[RecoveryUnitOfWork, None, None]:
    uow = RecoveryUnitOfWork()
    app.dependency_overrides[get_unit_of_work] = lambda: uow
    yield uow
    app.dependency_overrides.clear()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


def auth_headers() -> dict[str, str]:
    token = create_access_token(user_id=12, username="recovery-test")
    return {"Authorization": f"Bearer {token}"}


def test_recovery_requires_authentication(client, recovery_uow) -> None:
    response = client.post("/api/v1/payroll/runs/42/recover")
    assert response.status_code == 401
    assert recovery_uow.commit_count == 0


def test_recovery_requires_dedicated_permission(client, recovery_uow) -> None:
    recovery_uow.authorization.has_permission.return_value = False
    response = client.post(
        "/api/v1/payroll/runs/42/recover", headers=auth_headers()
    )
    assert response.status_code == 403
    recovery_uow.authorization.has_permission.assert_called_once_with(
        12, "payroll.run.recover"
    )
    assert recovery_uow.commit_count == 0


def test_recovery_missing_run_returns_404(client, recovery_uow) -> None:
    recovery_uow.payroll_runs.missing = True
    response = client.post(
        "/api/v1/payroll/runs/42/recover", headers=auth_headers()
    )
    assert response.status_code == 404
    assert recovery_uow.commit_count == 0


def test_recovery_transitions_expired_attempt_and_audits_actor(client, recovery_uow) -> None:
    response = client.post(
        "/api/v1/payroll/runs/42/recover", headers=auth_headers()
    )
    assert response.status_code == 200
    assert response.json()["status"] == "FAILED"
    assert recovery_uow.payroll_runs.run.attempt_number == 3
    assert recovery_uow.payroll_runs.run.attempt_lease_expires_at is None
    assert recovery_uow.commit_count == 1
    event, changes = recovery_uow.audit_events.events[0]
    assert event.action_type == "PAYROLL_RUN_ATTEMPT_RECOVERED"
    assert event.actor_user_id == 12
    assert event.correlation_id == response.headers["X-Request-ID"]
    assert [(change.field_name, change.old_value, change.new_value) for change in changes] == [
        ("payroll_run_id", None, "42"),
        ("attempt_number", None, "3"),
        ("status", "PROCESSING", "FAILED"),
        ("attempt_lease_expires_at", "2026-10-01T11:59:00", None),
    ]


@pytest.mark.parametrize(
    ("status", "expired"),
    [("CREATED", True), ("PROCESSING", False), ("FAILED", True), ("PROCESSED", True), ("FINALIZED", True)],
)
def test_recovery_rejects_unexpired_or_wrong_state(
    client, recovery_uow, status: str, expired: bool
) -> None:
    recovery_uow.payroll_runs.run.status = status
    recovery_uow.payroll_runs.expired = expired
    response = client.post(
        "/api/v1/payroll/runs/42/recover", headers=auth_headers()
    )
    assert response.status_code == 409
    assert recovery_uow.commit_count == 0
    assert recovery_uow.audit_events.events == []

