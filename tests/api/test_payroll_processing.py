from collections.abc import Generator
from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock

from app.api.dependencies.unit_of_work import get_unit_of_work
from app.application.payroll.payroll_processing_orchestrator import (
    PayrollProcessingOrchestrator,
)
from app.infrastructure.security.jwt import create_access_token
from app.main import app


class ProcessingRunRepository:
    def __init__(self, status: str = "CREATED") -> None:
        self.run = SimpleNamespace(
            payroll_run_id=42,
            payroll_year=2026,
            payroll_month=10,
            status=status,
            initiated_by_user_id=12,
            started_at=None,
        )

    def claim_for_processing(self, run_id: int) -> bool:
        if run_id != self.run.payroll_run_id or self.run.status != "CREATED":
            return False
        self.run.status = "PROCESSING"
        self.run.started_at = datetime(2026, 10, 1, 12, 0, 0)
        return True

    def mark_failed_if_processing(self, run_id: int) -> bool:
        if run_id != self.run.payroll_run_id or self.run.status != "PROCESSING":
            return False
        self.run.status = "FAILED"
        return True

    def get_by_id(self, run_id: int) -> SimpleNamespace | None:
        return self.run if run_id == self.run.payroll_run_id else None


class AuditEventFake:
    def __init__(self) -> None:
        self.events: list[tuple[object, list[object]]] = []

    def add(self, event, changes=()):
        event.audit_event_id = len(self.events) + 1
        for change in changes:
            change.audit_event_id = event.audit_event_id
        self.events.append((event, list(changes)))
        return event


class ProcessingUnitOfWork:
    def __init__(self, status: str = "CREATED") -> None:
        self.user = SimpleNamespace(
            user_id=12,
            username="payroll-processing-test",
            status="ACTIVE",
        )
        self.users = Mock()
        self.users.get_by_id.return_value = self.user
        self.authorization = Mock()
        self.authorization.has_permission.return_value = True
        self.payroll_runs = ProcessingRunRepository(status)
        self.audit_events = AuditEventFake()
        self.payroll_results = Mock()
        self.payroll_result_components = Mock()
        self.payroll_processing_issues = Mock()
        self.payslips = Mock()
        self.commit_count = 0
        self.rollback_count = 0

    def commit(self) -> None:
        self.commit_count += 1

    def rollback(self) -> None:
        self.rollback_count += 1


@pytest.fixture
def fake_uow() -> Generator[ProcessingUnitOfWork, None, None]:
    uow = ProcessingUnitOfWork()
    app.dependency_overrides[get_unit_of_work] = lambda: uow
    yield uow
    app.dependency_overrides.clear()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


def auth_headers() -> dict[str, str]:
    token = create_access_token(user_id=12, username="payroll-processing-test")
    return {"Authorization": f"Bearer {token}"}


def test_process_created_run_claims_and_audits_processing_start(
    client: TestClient, fake_uow: ProcessingUnitOfWork
) -> None:
    response = client.post(
        "/api/v1/payroll/runs/42/process", headers=auth_headers()
    )

    assert response.status_code == 200
    assert response.json()["status"] == "PROCESSING"
    assert fake_uow.payroll_runs.run.started_at is not None
    assert fake_uow.commit_count == 1
    assert fake_uow.authorization.has_permission.call_args.args == (
        12,
        "payroll.run.process",
    )
    assert len(fake_uow.audit_events.events) == 1
    event, changes = fake_uow.audit_events.events[0]
    assert event.action_type == "PAYROLL_RUN_PROCESSING_STARTED"
    assert event.correlation_id == response.headers["X-Request-ID"]
    assert [(change.field_name, change.old_value, change.new_value) for change in changes] == [
        ("status", "CREATED", "PROCESSING")
    ]
    for repository in (
        fake_uow.payroll_results,
        fake_uow.payroll_result_components,
        fake_uow.payroll_processing_issues,
        fake_uow.payslips,
    ):
        repository.add.assert_not_called()


def test_process_endpoint_does_not_accept_client_state_changes(
    client: TestClient, fake_uow: ProcessingUnitOfWork
) -> None:
    response = client.post(
        "/api/v1/payroll/runs/42/process",
        json={"status": "PROCESSED", "started_at": None},
        headers=auth_headers(),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "PROCESSING"


@pytest.mark.parametrize("initial_status", ["PROCESSING", "PROCESSED", "FAILED", "FINALIZED"])
def test_process_rejects_non_created_state_without_second_claim(
    client: TestClient,
    fake_uow: ProcessingUnitOfWork,
    initial_status: str,
) -> None:
    fake_uow.payroll_runs.run.status = initial_status
    original_started_at = fake_uow.payroll_runs.run.started_at

    response = client.post(
        "/api/v1/payroll/runs/42/process", headers=auth_headers()
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "BUSINESS_RULE_VIOLATION"
    assert fake_uow.payroll_runs.run.status == initial_status
    assert fake_uow.payroll_runs.run.started_at == original_started_at
    assert fake_uow.commit_count == 0
    assert fake_uow.audit_events.events == []


def test_duplicate_process_requests_only_start_one_attempt(
    client: TestClient, fake_uow: ProcessingUnitOfWork
) -> None:
    first = client.post("/api/v1/payroll/runs/42/process", headers=auth_headers())
    started_at = fake_uow.payroll_runs.run.started_at
    second = client.post("/api/v1/payroll/runs/42/process", headers=auth_headers())

    assert first.status_code == 200
    assert second.status_code == 409
    assert fake_uow.payroll_runs.run.status == "PROCESSING"
    assert fake_uow.payroll_runs.run.started_at == started_at
    assert fake_uow.commit_count == 1
    assert len(fake_uow.audit_events.events) == 1


def test_missing_run_returns_404(client: TestClient, fake_uow: ProcessingUnitOfWork) -> None:
    response = client.post(
        "/api/v1/payroll/runs/999/process", headers=auth_headers()
    )

    assert response.status_code == 404


def test_process_requires_authentication(
    client: TestClient, fake_uow: ProcessingUnitOfWork
) -> None:
    response = client.post("/api/v1/payroll/runs/42/process")

    assert response.status_code == 401


def test_process_requires_process_permission(
    client: TestClient, fake_uow: ProcessingUnitOfWork
) -> None:
    fake_uow.authorization.has_permission.return_value = False

    response = client.post(
        "/api/v1/payroll/runs/42/process", headers=auth_headers()
    )

    assert response.status_code == 403
    assert fake_uow.payroll_runs.run.status == "CREATED"


def test_orchestration_failure_marks_run_failed_and_returns_sanitized_500(
    client: TestClient,
    fake_uow: ProcessingUnitOfWork,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_after_claim(self, payroll_run_id: int) -> None:
        raise RuntimeError("private payroll details")

    monkeypatch.setattr(
        PayrollProcessingOrchestrator,
        "_processing_pipeline_extension_point",
        fail_after_claim,
    )

    response = client.post(
        "/api/v1/payroll/runs/42/process", headers=auth_headers()
    )

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_SERVER_ERROR"
    assert "private payroll details" not in response.text
    assert fake_uow.payroll_runs.run.status == "FAILED"
    assert fake_uow.commit_count == 2
    assert [event.action_type for event, _ in fake_uow.audit_events.events] == [
        "PAYROLL_RUN_PROCESSING_STARTED",
        "PAYROLL_RUN_PROCESSING_FAILED",
    ]
