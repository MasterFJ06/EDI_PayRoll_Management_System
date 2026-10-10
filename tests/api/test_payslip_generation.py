from collections.abc import Generator
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.api.dependencies.unit_of_work import get_unit_of_work
from app.infrastructure.security.jwt import create_access_token
from app.main import app


class PayslipUnitOfWork:
    def __init__(self) -> None:
        self.user = SimpleNamespace(user_id=12, username="payslip-test", status="ACTIVE")
        self.users = SimpleNamespace(get_by_id=lambda user_id: self.user if user_id == 12 else None)
        self.authorization = SimpleNamespace(has_permission=Mock(return_value=True))
        self.run = SimpleNamespace(payroll_run_id=7, status="FINALIZED")
        self.payroll_runs = SimpleNamespace(lock_for_finalization=self._lock_run)
        self.result = SimpleNamespace(
            payroll_result_id=19,
            payroll_run_id=7,
            gross_earnings="1200.00",
            total_deductions="100.00",
            net_salary="1100.00",
            workforce_calculation_snapshot={"frozen": True},
        )
        self.payroll_results = SimpleNamespace(get_by_id=self._get_result)
        self.payslip = None
        self.payslips = SimpleNamespace(
            get_by_result_id=lambda _result_id: self.payslip,
            get_by_number=lambda _number: None,
            add=self._add_payslip,
        )
        self.audit_events = SimpleNamespace(add=self._add_audit)
        self.audit = None
        self.audit_error = None
        self.commit_count = 0
        self.rollback_count = 0
        self.integrity_error = None

    def _lock_run(self, run_id: int):
        return self.run if run_id == self.run.payroll_run_id else None

    def _get_result(self, result_id: int):
        return self.result if result_id == self.result.payroll_result_id else None

    def _add_payslip(self, payslip):
        if self.integrity_error is not None:
            raise self.integrity_error
        payslip.payslip_id = 31
        payslip.generated_at = datetime(2026, 10, 10, 12, 0)
        self.payslip = payslip
        return payslip

    def _add_audit(self, event, changes=()):
        if self.audit_error is not None:
            raise self.audit_error
        self.audit = (event, list(changes))

    def commit(self) -> None:
        self.commit_count += 1

    def rollback(self) -> None:
        self.rollback_count += 1
        self.payslip = None
        self.audit = None


@pytest.fixture
def payslip_uow() -> Generator[PayslipUnitOfWork, None, None]:
    uow = PayslipUnitOfWork()
    app.dependency_overrides[get_unit_of_work] = lambda: uow
    yield uow
    app.dependency_overrides.clear()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


def _headers(user_id: int = 12) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {create_access_token(user_id, 'payslip-test')}"
    }


def _generate(client: TestClient, **kwargs):
    return client.post(
        "/api/v1/payroll/runs/7/results/19/payslip",
        json={"payslip_number": "PS-19", **kwargs},
        headers=_headers(),
    )


def test_generate_payslip_requires_authentication_and_persisted_permission(
    client: TestClient, payslip_uow: PayslipUnitOfWork
) -> None:
    assert _generate(client).status_code == 401
    payslip_uow.authorization.has_permission.return_value = False
    response = _generate(client)
    assert response.status_code == 403
    assert payslip_uow.commit_count == 0


def test_generate_payslip_uses_authenticated_actor_and_returns_null_document(
    client: TestClient, payslip_uow: PayslipUnitOfWork
) -> None:
    response = _generate(client)
    assert response.status_code == 201, response.text
    assert response.json() == {
        "payslip_id": 31,
        "payroll_result_id": 19,
        "payslip_number": "PS-19",
        "generated_by_user_id": 12,
        "generated_at": "2026-10-10T12:00:00",
        "document_path": None,
    }
    assert payslip_uow.authorization.has_permission.call_args.args == (
        12, "payroll.payslip.create"
    )
    assert payslip_uow.payslip.generated_by_user_id == 12
    assert payslip_uow.payslip.document_path is None
    assert payslip_uow.audit[0].action_type == "PAYSLIP_GENERATED"
    assert payslip_uow.audit[0].resource_id == 31
    assert payslip_uow.audit[0].actor_user_id == 12
    assert payslip_uow.audit[0].correlation_id == response.headers["X-Request-ID"]
    assert payslip_uow.commit_count == 1
    assert payslip_uow.result.gross_earnings == "1200.00"
    assert payslip_uow.result.total_deductions == "100.00"
    assert payslip_uow.result.net_salary == "1100.00"
    assert payslip_uow.result.workforce_calculation_snapshot == {"frozen": True}


def test_client_cannot_supply_generator_identity(client: TestClient) -> None:
    response = _generate(client, generated_by_user_id=999)
    assert response.status_code == 422


@pytest.mark.parametrize("status", ["CREATED", "PROCESSING", "FAILED", "PROCESSED"])
def test_generate_payslip_rejects_nonfinalized_run(
    client: TestClient, payslip_uow: PayslipUnitOfWork, status: str
) -> None:
    payslip_uow.run.status = status
    response = _generate(client)
    assert response.status_code == 409
    assert payslip_uow.payslip is None
    assert payslip_uow.commit_count == 0


def test_generate_payslip_hides_missing_and_cross_run_results(
    client: TestClient, payslip_uow: PayslipUnitOfWork
) -> None:
    payslip_uow.payroll_results.get_by_id = lambda _result_id: None
    assert _generate(client).status_code == 404
    payslip_uow.payroll_results.get_by_id = lambda _result_id: SimpleNamespace(
        payroll_run_id=8
    )
    assert _generate(client).status_code == 404
    payslip_uow.payroll_runs.lock_for_finalization = lambda _run_id: None
    assert _generate(client).status_code == 404
    assert payslip_uow.commit_count == 0


def test_generate_payslip_duplicate_and_unique_race_return_conflict(
    client: TestClient, payslip_uow: PayslipUnitOfWork
) -> None:
    payslip_uow.payslip = object()
    assert _generate(client).status_code == 409
    payslip_uow.payslip = None
    payslip_uow.integrity_error = IntegrityError(
        "INSERT", {}, Exception("Duplicate entry for key 'payslips.uq_payslip_result'")
    )
    response = _generate(client)
    assert response.status_code == 409
    assert payslip_uow.rollback_count == 1
    assert payslip_uow.commit_count == 0


def test_audit_failure_does_not_commit_payslip(
    client: TestClient, payslip_uow: PayslipUnitOfWork
) -> None:
    payslip_uow.audit_error = RuntimeError("private database detail")
    response = _generate(client)
    assert response.status_code == 500
    assert "private database detail" not in response.text
    assert payslip_uow.commit_count == 0
    assert payslip_uow.rollback_count == 1
    assert payslip_uow.payslip is None


def test_invalid_payslip_number_is_validated(client: TestClient) -> None:
    response = _generate(client, payslip_number="x" * 51)
    assert response.status_code == 422
