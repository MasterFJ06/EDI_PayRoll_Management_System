from collections.abc import Generator
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies.unit_of_work import get_unit_of_work
from app.domain.shared.exceptions import BusinessRuleViolation
from app.infrastructure.security.jwt import create_access_token
from app.main import app


class RetryRunRepository:
    def __init__(self) -> None:
        self.run = SimpleNamespace(
            payroll_run_id=42,
            payroll_year=2026,
            payroll_month=10,
            status="FAILED",
            initiated_by_user_id=12,
            attempt_number=3,
            started_at=None,
            attempt_lease_expires_at=None,
        )
        self.missing = False
        self.stale_after_read = False
        self.expected_attempts: list[int] = []

    def get_by_id(self, payroll_run_id: int):
        if self.missing or payroll_run_id != self.run.payroll_run_id:
            return None
        if self.stale_after_read and self.run.status == "FAILED":
            self.stale_after_read = False
            initial_view = SimpleNamespace(**vars(self.run))
            self.run.status = "PROCESSING"
            self.run.attempt_number += 1
            return initial_view
        return self.run

    def lock_failed_attempt(self, payroll_run_id: int):
        return self.run if payroll_run_id == self.run.payroll_run_id else None

    def retry_failed_attempt(self, payroll_run_id: int, expected_attempt_number: int):
        self.expected_attempts.append(expected_attempt_number)
        if (
            payroll_run_id != self.run.payroll_run_id
            or self.run.status != "FAILED"
            or self.run.attempt_number != expected_attempt_number
        ):
            return None
        self.run.status = "PROCESSING"
        self.run.attempt_number += 1
        return self.run.attempt_number


class RetryAuditRepository:
    def __init__(self) -> None:
        self.events: list[tuple[object, list[object]]] = []

    def add(self, event, changes=()):
        event.audit_event_id = len(self.events) + 1
        materialized_changes = list(changes)
        for change in materialized_changes:
            change.audit_event_id = event.audit_event_id
        self.events.append((event, materialized_changes))
        return event


class RetryUnitOfWork:
    def __init__(self) -> None:
        self.user = SimpleNamespace(
            user_id=12,
            username="payroll-retry-test",
            status="ACTIVE",
        )
        self.users = SimpleNamespace(get_by_id=lambda user_id: self.user)
        self.authorization = SimpleNamespace(has_permission=Mock(return_value=True))
        self.payroll_runs = RetryRunRepository()
        self.audit_events = RetryAuditRepository()
        self.payroll_results = SimpleNamespace(delete_by_run=lambda _run_id: 1)
        self.payroll_result_components = SimpleNamespace(
            delete_by_run=lambda _run_id: 2
        )
        self.payroll_run_workforce_snapshots = SimpleNamespace(
            delete_by_run_and_attempt=lambda _run_id, _attempt: 1
        )
        self.payslip: object | None = None
        self.payslips = SimpleNamespace(
            get_by_run_id=lambda _run_id: self.payslip
        )
        self.commit_count = 0

    def commit(self) -> None:
        self.commit_count += 1


@pytest.fixture
def retry_uow() -> Generator[RetryUnitOfWork, None, None]:
    uow = RetryUnitOfWork()
    app.dependency_overrides[get_unit_of_work] = lambda: uow
    yield uow
    app.dependency_overrides.clear()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


def auth_headers() -> dict[str, str]:
    token = create_access_token(user_id=12, username="payroll-retry-test")
    return {"Authorization": f"Bearer {token}"}


def test_retry_requires_authentication(
    client: TestClient, retry_uow: RetryUnitOfWork
) -> None:
    response = client.post("/api/v1/payroll/runs/42/retry")

    assert response.status_code == 401
    assert retry_uow.payroll_runs.expected_attempts == []


def test_retry_requires_permission(
    client: TestClient, retry_uow: RetryUnitOfWork
) -> None:
    retry_uow.authorization.has_permission = lambda *_: False

    response = client.post(
        "/api/v1/payroll/runs/42/retry", headers=auth_headers()
    )

    assert response.status_code == 403
    assert retry_uow.payroll_runs.expected_attempts == []


def test_retry_missing_run_returns_404(
    client: TestClient, retry_uow: RetryUnitOfWork
) -> None:
    retry_uow.payroll_runs.missing = True

    response = client.post(
        "/api/v1/payroll/runs/42/retry", headers=auth_headers()
    )

    assert response.status_code == 404
    assert retry_uow.payroll_runs.expected_attempts == []


def test_retry_success_uses_internal_attempt_and_existing_response_contract(
    client: TestClient, retry_uow: RetryUnitOfWork
) -> None:
    response = client.post(
        "/api/v1/payroll/runs/42/retry", headers=auth_headers()
    )

    assert response.status_code == 200
    assert response.json() == {
        "payroll_run_id": 42,
        "payroll_year": 2026,
        "payroll_month": 10,
        "status": "PROCESSING",
        "initiated_by_user_id": 12,
    }
    assert "attempt_number" not in response.json()
    assert retry_uow.payroll_runs.expected_attempts == [3]
    assert retry_uow.payroll_runs.run.attempt_number == 4
    assert retry_uow.commit_count == 1
    retry_uow.authorization.has_permission.assert_called_once_with(
        12, "payroll.run.retry"
    )
    assert len(retry_uow.audit_events.events) == 1
    event, _ = retry_uow.audit_events.events[0]
    assert event.action_type == "PAYROLL_RUN_RETRY_CLAIMED"
    assert event.actor_user_id == 12
    assert event.correlation_id == response.headers["X-Request-ID"]


@pytest.mark.parametrize(
    "state", ["CREATED", "PROCESSING", "PROCESSED", "FINALIZED"]
)
def test_retry_rejects_non_failed_states(
    client: TestClient, retry_uow: RetryUnitOfWork, state: str
) -> None:
    retry_uow.payroll_runs.run.status = state

    response = client.post(
        "/api/v1/payroll/runs/42/retry", headers=auth_headers()
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "BUSINESS_RULE_VIOLATION"
    assert retry_uow.payroll_runs.run.status == state
    assert retry_uow.commit_count == 0
    assert retry_uow.audit_events.events == []


def test_retry_with_payslip_returns_conflict_without_touching_payslip(
    client: TestClient, retry_uow: RetryUnitOfWork
) -> None:
    payslip = SimpleNamespace(payslip_id=91, payroll_result_id=17)
    retry_uow.payslip = payslip

    response = client.post(
        "/api/v1/payroll/runs/42/retry", headers=auth_headers()
    )

    assert response.status_code == 409
    assert retry_uow.payslip is payslip
    assert retry_uow.payroll_runs.run.status == "FAILED"
    assert retry_uow.audit_events.events == []
    assert retry_uow.commit_count == 0


def test_stale_api_attempt_is_rejected_by_b3_service(
    client: TestClient, retry_uow: RetryUnitOfWork
) -> None:
    retry_uow.payroll_runs.stale_after_read = True

    response = client.post(
        "/api/v1/payroll/runs/42/retry", headers=auth_headers()
    )

    assert response.status_code == 409
    assert retry_uow.payroll_runs.expected_attempts == [3]
    assert retry_uow.payroll_runs.run.status == "PROCESSING"
    assert retry_uow.audit_events.events == []
    assert retry_uow.commit_count == 0


def test_retry_requires_no_request_body_and_does_not_duplicate_audit(
    client: TestClient, retry_uow: RetryUnitOfWork
) -> None:
    response = client.post(
        "/api/v1/payroll/runs/42/retry", headers=auth_headers()
    )

    assert response.status_code == 200
    assert len(retry_uow.audit_events.events) == 1


def test_unexpected_retry_failure_remains_sanitized_500(
    client: TestClient, retry_uow: RetryUnitOfWork
) -> None:
    def fail_delete(_run_id: int) -> int:
        raise RuntimeError("private database detail")

    retry_uow.payroll_result_components.delete_by_run = fail_delete

    response = client.post(
        "/api/v1/payroll/runs/42/retry", headers=auth_headers()
    )

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_SERVER_ERROR"
    assert "private database detail" not in response.text
