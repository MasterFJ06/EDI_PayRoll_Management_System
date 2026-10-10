from collections.abc import Generator
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies.unit_of_work import get_unit_of_work
from app.infrastructure.security.jwt import create_access_token
from app.main import app


class ReportUnitOfWork:
    def __init__(self) -> None:
        self.user = SimpleNamespace(
            user_id=12, username="payroll-report-test", status="ACTIVE"
        )
        self.users = SimpleNamespace(
            get_by_id=lambda user_id: self.user if user_id == 12 else None
        )
        self.permission_codes = {"report.payroll.read"}
        self.permission_checks: list[tuple[int, str]] = []
        self.authorization = SimpleNamespace(has_permission=self._has_permission)
        self.run = SimpleNamespace(
            payroll_run_id=7,
            payroll_year=2026,
            payroll_month=10,
            status="FINALIZED",
            initiated_by_user_id=12,
        )
        self.payroll_runs = SimpleNamespace(
            get_by_id=lambda run_id: self.run if run_id == 7 else None
        )
        self.aggregate = (
            2,
            Decimal("3000.20"),
            Decimal("200.10"),
            Decimal("2800.10"),
        )
        self.aggregate_calls: list[int] = []
        self.payroll_results = SimpleNamespace(aggregate_by_run=self._aggregate)

    def _aggregate(self, run_id: int):
        self.aggregate_calls.append(run_id)
        return self.aggregate

    def _has_permission(self, user_id: int, code: str) -> bool:
        self.permission_checks.append((user_id, code))
        return code in self.permission_codes


@pytest.fixture
def report_uow() -> Generator[ReportUnitOfWork, None, None]:
    uow = ReportUnitOfWork()
    app.dependency_overrides[get_unit_of_work] = lambda: uow
    yield uow
    app.dependency_overrides.clear()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


def _headers() -> dict[str, str]:
    token = create_access_token(12, "payroll-report-test")
    return {"Authorization": f"Bearer {token}"}


def test_report_requires_authentication_and_persisted_permission(
    client: TestClient, report_uow: ReportUnitOfWork
) -> None:
    path = "/api/v1/reports/payroll/runs/7"
    assert client.get(path).status_code == 401
    report_uow.permission_codes = {"payroll.run.read"}
    assert client.get(path, headers=_headers()).status_code == 403
    assert report_uow.permission_checks == [(12, "report.payroll.read")]


def test_report_returns_only_finalized_summary_and_decimal_totals(
    client: TestClient, report_uow: ReportUnitOfWork
) -> None:
    response = client.get("/api/v1/reports/payroll/runs/7", headers=_headers())
    assert response.status_code == 200
    assert response.json() == {
        "payroll_run_id": 7,
        "payroll_year": 2026,
        "payroll_month": 10,
        "status": "FINALIZED",
        "initiated_by_user_id": 12,
        "employee_result_count": 2,
        "total_gross_pay": "3000.20",
        "total_deductions": "200.10",
        "total_net_pay": "2800.10",
    }
    sensitive_fields = {
        "employee_id",
        "employee_name",
        "components",
        "workforce_calculation_snapshot",
    }
    assert not sensitive_fields & response.json().keys()
    assert report_uow.permission_checks == [(12, "report.payroll.read")]


def test_report_missing_run_returns_404(
    client: TestClient, report_uow: ReportUnitOfWork
) -> None:
    response = client.get("/api/v1/reports/payroll/runs/999", headers=_headers())
    assert response.status_code == 404
    assert report_uow.permission_checks == [(12, "report.payroll.read")]


@pytest.mark.parametrize("state", ["CREATED", "PROCESSING", "PROCESSED", "FAILED"])
def test_report_rejects_non_finalized_run(
    client: TestClient, report_uow: ReportUnitOfWork, state: str
) -> None:
    report_uow.run.status = state
    response = client.get("/api/v1/reports/payroll/runs/7", headers=_headers())
    assert response.status_code == 409
    assert report_uow.aggregate_calls == []


def test_empty_finalized_run_is_rejected_without_fabricated_totals(
    client: TestClient, report_uow: ReportUnitOfWork
) -> None:
    report_uow.aggregate = (0, None, None, None)
    response = client.get("/api/v1/reports/payroll/runs/7", headers=_headers())
    assert response.status_code == 409
