from collections.abc import Generator
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies.unit_of_work import get_unit_of_work
from app.application.reporting.payroll_results_report_service import (
    encode_payroll_results_cursor,
)
from app.domain.payroll.payroll_result_report import PayrollResultReportRecord
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
        self.results = [
            PayrollResultReportRecord(
                payroll_result_id=101 + index,
                payroll_run_id=7,
                employee_id=21 + index,
                salary_assignment_id=31 + index,
                gross_earnings=Decimal("1000.01"),
                total_deductions=Decimal("50.00"),
                net_salary=Decimal("950.01"),
                employee_code=f"EMP-{index + 1}",
                employee_name=f"Employee {index + 1}",
            )
            for index in range(3)
        ]
        self.page_calls: list[tuple[int, int | None, int | None, int]] = []
        self.payroll_results = SimpleNamespace(
            aggregate_by_run=self._aggregate,
            list_report_page=self._list_report_page,
        )

    def _aggregate(self, run_id: int):
        self.aggregate_calls.append(run_id)
        return self.aggregate

    def _has_permission(self, user_id: int, code: str) -> bool:
        self.permission_checks.append((user_id, code))
        return code in self.permission_codes

    def _list_report_page(
        self,
        payroll_run_id: int,
        after_employee_id: int | None,
        after_payroll_result_id: int | None,
        limit: int,
    ) -> list[PayrollResultReportRecord]:
        self.page_calls.append(
            (payroll_run_id, after_employee_id, after_payroll_result_id, limit)
        )
        rows = [row for row in self.results if row.payroll_run_id == payroll_run_id]
        if after_employee_id is not None and after_payroll_result_id is not None:
            rows = [
                row
                for row in rows
                if (row.employee_id, row.payroll_result_id)
                > (after_employee_id, after_payroll_result_id)
            ]
        return rows[:limit]


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


def test_payroll_results_report_auth_and_permission_are_enforced(
    client: TestClient, report_uow: ReportUnitOfWork
) -> None:
    path = "/api/v1/reports/payroll/runs/7/results"
    assert client.get(path).status_code == 401
    report_uow.permission_codes = {"payroll.run.read"}
    response = client.get(path, headers=_headers())
    assert response.status_code == 403
    assert report_uow.permission_checks == [(12, "report.payroll.read")]


def test_payroll_results_report_returns_exact_fields_and_keyset_pages(
    client: TestClient, report_uow: ReportUnitOfWork
) -> None:
    first = client.get(
        "/api/v1/reports/payroll/runs/7/results?limit=2", headers=_headers()
    )
    assert first.status_code == 200, first.text
    first_body = first.json()
    assert set(first_body) == {"payroll_run_id", "results", "pagination"}
    assert first_body["payroll_run_id"] == 7
    assert set(first_body["pagination"]) == {"limit", "has_more", "next_cursor"}
    assert first_body["pagination"]["limit"] == 2
    assert first_body["pagination"]["has_more"] is True
    assert first_body["pagination"]["next_cursor"]
    assert [row["employee_id"] for row in first_body["results"]] == [21, 22]
    assert first_body["results"][0] == {
        "payroll_result_id": 101,
        "payroll_run_id": 7,
        "employee_id": 21,
        "salary_assignment_id": 31,
        "gross_earnings": "1000.01",
        "total_deductions": "50.00",
        "net_salary": "950.01",
        "employee_code": "EMP-1",
        "employee_name": "Employee 1",
    }
    assert set(first_body["results"][0]) == {
        "payroll_result_id",
        "payroll_run_id",
        "employee_id",
        "salary_assignment_id",
        "gross_earnings",
        "total_deductions",
        "net_salary",
        "employee_code",
        "employee_name",
    }

    second = client.get(
        "/api/v1/reports/payroll/runs/7/results",
        params={"limit": 2, "cursor": first_body["pagination"]["next_cursor"]},
        headers=_headers(),
    )
    assert second.status_code == 200, second.text
    second_body = second.json()
    assert [row["employee_id"] for row in second_body["results"]] == [23]
    assert second_body["pagination"] == {
        "limit": 2,
        "has_more": False,
        "next_cursor": None,
    }
    assert report_uow.page_calls == [
        (7, None, None, 3),
        (7, 22, 102, 3),
    ]


def test_payroll_results_report_defaults_to_fifty(
    client: TestClient, report_uow: ReportUnitOfWork
) -> None:
    response = client.get(
        "/api/v1/reports/payroll/runs/7/results", headers=_headers()
    )
    assert response.status_code == 200
    assert response.json()["pagination"]["limit"] == 50
    assert report_uow.page_calls == [(7, None, None, 51)]


@pytest.mark.parametrize("limit", [0, 101])
def test_payroll_results_report_rejects_out_of_range_limits(
    client: TestClient, report_uow: ReportUnitOfWork, limit: int
) -> None:
    response = client.get(
        f"/api/v1/reports/payroll/runs/7/results?limit={limit}",
        headers=_headers(),
    )
    assert response.status_code == 422
    assert report_uow.page_calls == []


@pytest.mark.parametrize("limit", [1, 100])
def test_payroll_results_report_accepts_limit_boundaries(
    client: TestClient, report_uow: ReportUnitOfWork, limit: int
) -> None:
    response = client.get(
        f"/api/v1/reports/payroll/runs/7/results?limit={limit}",
        headers=_headers(),
    )
    assert response.status_code == 200
    assert response.json()["pagination"]["limit"] == limit
    assert report_uow.page_calls == [(7, None, None, limit + 1)]


def test_payroll_results_report_rejects_malformed_tampered_and_cross_run_cursors(
    client: TestClient, report_uow: ReportUnitOfWork
) -> None:
    cross_run_cursor = encode_payroll_results_cursor(8, 21, 101)
    valid_cursor = encode_payroll_results_cursor(7, 21, 101)
    tampered_cursor = valid_cursor[:-1] + (
        "A" if valid_cursor[-1] != "A" else "B"
    )
    for cursor in ("not-a-cursor", tampered_cursor, cross_run_cursor):
        response = client.get(
            "/api/v1/reports/payroll/runs/7/results",
            params={"cursor": cursor},
            headers=_headers(),
        )
        assert response.status_code == 422
    assert report_uow.page_calls == []


@pytest.mark.parametrize("state", ["CREATED", "PROCESSING", "PROCESSED", "FAILED"])
def test_payroll_results_report_rejects_non_finalized_runs(
    client: TestClient, report_uow: ReportUnitOfWork, state: str
) -> None:
    report_uow.run.status = state
    response = client.get(
        "/api/v1/reports/payroll/runs/7/results", headers=_headers()
    )
    assert response.status_code == 409
    assert report_uow.page_calls == []


def test_payroll_results_report_missing_run_returns_404(
    client: TestClient, report_uow: ReportUnitOfWork
) -> None:
    response = client.get(
        "/api/v1/reports/payroll/runs/999/results", headers=_headers()
    )
    assert response.status_code == 404
    assert report_uow.page_calls == []
