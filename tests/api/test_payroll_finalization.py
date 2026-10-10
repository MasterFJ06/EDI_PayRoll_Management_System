from collections.abc import Generator
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies.unit_of_work import get_unit_of_work
from app.domain.shared.exceptions import BusinessRuleViolation
from app.infrastructure.security.jwt import create_access_token
from app.main import app


class FinalizationUnitOfWork:
    def __init__(self) -> None:
        self.user = SimpleNamespace(
            user_id=12, username="payroll-finalize-test", status="ACTIVE"
        )
        self.users = SimpleNamespace(get_by_id=lambda _user_id: self.user)
        self.authorization = SimpleNamespace(has_permission=Mock(return_value=True))
        self.run = SimpleNamespace(
            payroll_run_id=42,
            payroll_year=2026,
            payroll_month=10,
            status="PROCESSED",
            initiated_by_user_id=12,
            finalized_at=None,
        )
        self.payroll_runs = SimpleNamespace(
            lock_for_finalization=self._lock_run,
            finalize_processed_run=self._finalize,
            get_by_id=self._get_run,
        )
        self.open_issue = False
        self.existing_payslip = None
        self.payroll_processing_issues = SimpleNamespace(
            has_open_for_update=lambda _run_id: self.open_issue
        )
        self.payslips = SimpleNamespace(
            get_by_run_id_for_update=lambda _run_id: self.existing_payslip
        )
        self.audit_events = SimpleNamespace(add=self._add_audit)
        self.audit_events_written: list[tuple[object, list[object]]] = []
        self.commit_count = 0
        self.audit_error: Exception | None = None
        self.transition_succeeds = True

    def _lock_run(self, run_id: int):
        return self.run if run_id == self.run.payroll_run_id else None

    def _get_run(self, run_id: int):
        return self.run if run_id == self.run.payroll_run_id else None

    def _finalize(self, run_id: int) -> bool:
        if not self.transition_succeeds or self.run.status != "PROCESSED":
            return False
        self.run.status = "FINALIZED"
        self.run.finalized_at = datetime(2026, 10, 31, 12, 0, 0)
        return True

    def _add_audit(self, event, changes=()):
        if self.audit_error is not None:
            raise self.audit_error
        self.audit_events_written.append((event, list(changes)))

    def commit(self) -> None:
        self.commit_count += 1


@pytest.fixture
def finalization_uow() -> Generator[FinalizationUnitOfWork, None, None]:
    uow = FinalizationUnitOfWork()
    app.dependency_overrides[get_unit_of_work] = lambda: uow
    yield uow
    app.dependency_overrides.clear()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


def _headers() -> dict[str, str]:
    token = create_access_token(user_id=12, username="payroll-finalize-test")
    return {"Authorization": f"Bearer {token}"}


def _finalize(client: TestClient, headers: dict[str, str] | None = None):
    return client.post("/api/v1/payroll/runs/42/finalize", headers=headers)


def test_finalization_requires_authentication(
    client: TestClient, finalization_uow: FinalizationUnitOfWork
) -> None:
    response = _finalize(client)
    assert response.status_code == 401
    assert finalization_uow.commit_count == 0


def test_finalization_requires_persisted_permission(
    client: TestClient, finalization_uow: FinalizationUnitOfWork
) -> None:
    finalization_uow.authorization.has_permission = lambda *_args: False
    response = _finalize(client, _headers())
    assert response.status_code == 403
    assert finalization_uow.commit_count == 0


def test_finalization_missing_run_returns_404(
    client: TestClient, finalization_uow: FinalizationUnitOfWork
) -> None:
    response = client.post("/api/v1/payroll/runs/999/finalize", headers=_headers())
    assert response.status_code == 404
    assert finalization_uow.commit_count == 0


@pytest.mark.parametrize("state", ["CREATED", "PROCESSING", "FAILED", "FINALIZED"])
def test_finalization_rejects_invalid_state(
    client: TestClient, finalization_uow: FinalizationUnitOfWork, state: str
) -> None:
    finalization_uow.run.status = state
    response = _finalize(client, _headers())
    assert response.status_code == 409
    assert finalization_uow.run.status == state
    assert finalization_uow.commit_count == 0
    assert finalization_uow.audit_events_written == []


def test_finalization_rechecks_open_issues_and_existing_payslips_under_lock(
    client: TestClient, finalization_uow: FinalizationUnitOfWork
) -> None:
    finalization_uow.open_issue = True
    response = _finalize(client, _headers())
    assert response.status_code == 409
    assert finalization_uow.run.status == "PROCESSED"
    finalization_uow.open_issue = False
    finalization_uow.existing_payslip = object()
    response = _finalize(client, _headers())
    assert response.status_code == 409
    assert finalization_uow.run.status == "PROCESSED"
    assert finalization_uow.commit_count == 0


def test_finalization_returns_existing_run_response_and_audits_once(
    client: TestClient, finalization_uow: FinalizationUnitOfWork
) -> None:
    response = _finalize(client, _headers())
    assert response.status_code == 200
    assert response.json() == {
        "payroll_run_id": 42,
        "payroll_year": 2026,
        "payroll_month": 10,
        "status": "FINALIZED",
        "initiated_by_user_id": 12,
    }
    assert finalization_uow.commit_count == 1
    event, changes = finalization_uow.audit_events_written[0]
    assert event.action_type == "PAYROLL_RUN_FINALIZED"
    assert event.actor_user_id == 12
    assert event.correlation_id == response.headers["X-Request-ID"]
    assert [(change.field_name, change.old_value, change.new_value) for change in changes] == [
        ("status", "PROCESSED", "FINALIZED"),
        ("finalized_at", None, "2026-10-31 12:00:00"),
    ]


def test_competing_or_repeated_finalization_returns_conflict(
    client: TestClient, finalization_uow: FinalizationUnitOfWork
) -> None:
    first = _finalize(client, _headers())
    second = _finalize(client, _headers())
    assert first.status_code == 200
    assert second.status_code == 409
    assert finalization_uow.commit_count == 1
    assert len(finalization_uow.audit_events_written) == 1


def test_audit_failure_does_not_commit_finalization(
    client: TestClient, finalization_uow: FinalizationUnitOfWork
) -> None:
    finalization_uow.audit_error = RuntimeError("private audit database detail")
    response = _finalize(client, _headers())
    assert response.status_code == 500
    assert "private audit database detail" not in response.text
    assert finalization_uow.commit_count == 0
