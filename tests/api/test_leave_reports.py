from collections.abc import Generator
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies.unit_of_work import get_unit_of_work
from app.domain.leave.leave_report import (
    LeaveAllocationReportRecord,
    LeaveBalanceReportRecord,
)
from app.infrastructure.security.jwt import create_access_token
from app.main import app


class LeaveReportTestUow:
    def __init__(self) -> None:
        self.user = SimpleNamespace(user_id=95, username="leave-report-api", status="ACTIVE")
        self.users = SimpleNamespace(get_by_id=lambda user_id: self.user if user_id == 95 else None)
        self.permissions = {"report.leave.read"}
        self.permission_checks: list[tuple[int, str]] = []
        self.authorization = SimpleNamespace(has_permission=self.has_permission)
        self.allocations = [
            LeaveAllocationReportRecord(
                leave_request_id=80 + day_id,
                leave_request_day_id=day_id,
                employee_id=12,
                employee_code="EMP-12",
                first_name="Asha",
                last_name="Patel",
                department_id=3,
                department_name="Finance",
                designation_id=4,
                designation_name="Analyst",
                leave_type_id=5,
                leave_type_name="Annual",
                start_date=date(2026, 1, 1),
                end_date=date(2026, 1, 4),
                requested_days=Decimal("2.00"),
                status=leave_status,
                leave_date=date(2026, 1, day_id),
                day_fraction=Decimal("0.50"),
            )
            for day_id, leave_status in enumerate(
                ("PENDING", "APPROVED", "REJECTED", "CANCELLED"), start=1
            )
        ]
        self.balances = [
            LeaveBalanceReportRecord(
                employee_id=12,
                employee_code="EMP-12",
                first_name="Asha",
                last_name="Patel",
                department_id=3,
                department_name="Finance",
                designation_id=4,
                designation_name="Analyst",
                leave_type_id=5,
                leave_type_name="Annual",
                balance_year=0,
                allocated_days=Decimal("10.00"),
                used_days=Decimal("2.50"),
            )
        ]
        self.allocation_calls: list[dict[str, object]] = []
        self.balance_calls: list[dict[str, object]] = []
        self.leave_reports = SimpleNamespace(
            list_allocation_report_page=self.list_allocation_report_page,
            list_balance_report_page=self.list_balance_report_page,
        )

    def has_permission(self, user_id: int, permission_code: str) -> bool:
        self.permission_checks.append((user_id, permission_code))
        return permission_code in self.permissions

    def list_allocation_report_page(self, **kwargs):
        self.allocation_calls.append(kwargs)
        records = [
            row for row in self.allocations
            if (kwargs["date_from"] is None or row.leave_date >= kwargs["date_from"])
            and (kwargs["date_to"] is None or row.leave_date <= kwargs["date_to"])
            and (kwargs["employee_id"] is None or row.employee_id == kwargs["employee_id"])
            and (kwargs["department_id"] is None or row.department_id == kwargs["department_id"])
            and (kwargs["leave_type_id"] is None or row.leave_type_id == kwargs["leave_type_id"])
            and (kwargs["status"] is None or row.status == kwargs["status"])
            and (
                kwargs["after_leave_date"] is None
                or (row.leave_date, row.leave_request_day_id)
                > (kwargs["after_leave_date"], kwargs["after_leave_request_day_id"])
            )
        ]
        records.sort(key=lambda row: (row.leave_date, row.leave_request_day_id))
        return records[:kwargs["limit"]]

    def list_balance_report_page(self, **kwargs):
        self.balance_calls.append(kwargs)
        records = [
            row for row in self.balances
            if (kwargs["employee_id"] is None or row.employee_id == kwargs["employee_id"])
            and (kwargs["department_id"] is None or row.department_id == kwargs["department_id"])
            and (kwargs["leave_type_id"] is None or row.leave_type_id == kwargs["leave_type_id"])
            and (kwargs["balance_year"] is None or row.balance_year == kwargs["balance_year"])
            and (
                kwargs["after_employee_id"] is None
                or (row.employee_id, row.leave_type_id, row.balance_year)
                > (
                    kwargs["after_employee_id"],
                    kwargs["after_leave_type_id"],
                    kwargs["after_balance_year"],
                )
            )
        ]
        records.sort(key=lambda row: (row.employee_id, row.leave_type_id, row.balance_year))
        return records[:kwargs["limit"]]


@pytest.fixture
def leave_report_uow() -> Generator[LeaveReportTestUow, None, None]:
    uow = LeaveReportTestUow()
    app.dependency_overrides[get_unit_of_work] = lambda: uow
    yield uow
    app.dependency_overrides.pop(get_unit_of_work, None)


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


def _headers() -> dict[str, str]:
    token = create_access_token(95, "leave-report-api")
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.parametrize(
    "path",
    ["/api/v1/reports/leave/allocations", "/api/v1/reports/leave/balances"],
)
def test_leave_reports_require_authentication_and_dedicated_permission(
    client: TestClient, leave_report_uow: LeaveReportTestUow, path: str
) -> None:
    assert client.get(path).status_code == 401
    leave_report_uow.permissions = {"payroll.run.read", "report.payroll.read"}
    denied = client.get(path, headers=_headers())
    assert denied.status_code == 403
    assert leave_report_uow.permission_checks == [(95, "report.leave.read")]
    assert leave_report_uow.allocation_calls == []
    assert leave_report_uow.balance_calls == []


def test_hr_authorized_allocation_contract_defaults_status_and_paginates(
    client: TestClient, leave_report_uow: LeaveReportTestUow
) -> None:
    first = client.get(
        "/api/v1/reports/leave/allocations", params={"limit": 2}, headers=_headers()
    )
    assert first.status_code == 200, first.text
    first_body = first.json()
    fields = {
        "leave_request_id", "leave_request_day_id", "employee_id", "employee_code",
        "first_name", "last_name", "department_id", "department_name", "designation_id",
        "designation_name", "leave_type_id", "leave_type_name", "start_date", "end_date",
        "requested_days", "status", "leave_date", "day_fraction",
    }
    assert set(first_body) == {"allocations", "pagination"}
    assert all(set(row) == fields for row in first_body["allocations"])
    assert [row["status"] for row in first_body["allocations"]] == ["PENDING", "APPROVED"]
    assert first_body["allocations"][0]["requested_days"] == "2.00"
    assert first_body["pagination"]["has_more"] is True
    assert first_body["pagination"]["limit"] == 2
    assert leave_report_uow.allocation_calls[0]["status"] is None
    assert leave_report_uow.allocation_calls[0]["limit"] == 3
    assert {
        "reason", "review_comment", "reviewer_user_id", "net_salary", "password_hash", "email"
    }.isdisjoint(fields)

    second = client.get(
        "/api/v1/reports/leave/allocations",
        params={"limit": 2, "cursor": first_body["pagination"]["next_cursor"]},
        headers=_headers(),
    )
    assert second.status_code == 200, second.text
    assert [row["status"] for row in second.json()["allocations"]] == ["REJECTED", "CANCELLED"]
    assert second.json()["pagination"]["has_more"] is False


def test_allocation_filters_are_inclusive_and_invalid_queries_return_422(
    client: TestClient, leave_report_uow: LeaveReportTestUow
) -> None:
    response = client.get(
        "/api/v1/reports/leave/allocations",
        params={
            "date_from": "2026-01-02", "date_to": "2026-01-02", "employee_id": 12,
            "department_id": 3, "leave_type_id": 5, "status": "APPROVED",
        },
        headers=_headers(),
    )
    assert response.status_code == 200, response.text
    assert [row["leave_date"] for row in response.json()["allocations"]] == ["2026-01-02"]
    assert leave_report_uow.allocation_calls[0]["date_from"] == date(2026, 1, 2)
    assert leave_report_uow.allocation_calls[0]["date_to"] == date(2026, 1, 2)
    for params in (
        {"date_from": "2026-01-03", "date_to": "2026-01-02"},
        {"status": "UNKNOWN"}, {"employee_id": 0}, {"department_id": -1},
        {"leave_type_id": 0}, {"limit": 0}, {"limit": 101}, {"cursor": "malformed"},
    ):
        invalid = client.get(
            "/api/v1/reports/leave/allocations", params=params, headers=_headers()
        )
        assert invalid.status_code == 422, (params, invalid.text)


def test_balance_report_returns_stored_values_and_validates_filters(
    client: TestClient, leave_report_uow: LeaveReportTestUow
) -> None:
    response = client.get(
        "/api/v1/reports/leave/balances",
        params={"employee_id": 12, "department_id": 3, "leave_type_id": 5, "balance_year": 0},
        headers=_headers(),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    fields = {
        "employee_id", "employee_code", "first_name", "last_name", "department_id",
        "department_name", "designation_id", "designation_name", "leave_type_id",
        "leave_type_name", "balance_year", "allocated_days", "used_days",
    }
    assert set(body) == {"balances", "pagination"}
    assert set(body["balances"][0]) == fields
    assert body["balances"][0]["balance_year"] == 0
    assert body["balances"][0]["allocated_days"] == "10.00"
    assert body["balances"][0]["used_days"] == "2.50"
    assert "remaining_days" not in body["balances"][0]
    assert leave_report_uow.balance_calls[0]["balance_year"] == 0
    assert leave_report_uow.balance_calls[0]["limit"] == 51

    for params in ({"employee_id": 0}, {"department_id": -1}, {"leave_type_id": 0}, {"balance_year": 65536}, {"limit": 101}, {"cursor": "bad"}):
        invalid = client.get(
            "/api/v1/reports/leave/balances", params=params, headers=_headers()
        )
        assert invalid.status_code == 422, (params, invalid.text)


def test_leave_reports_return_empty_envelopes_for_no_matching_rows(
    client: TestClient, leave_report_uow: LeaveReportTestUow
) -> None:
    leave_report_uow.allocations = []
    leave_report_uow.balances = []

    allocations = client.get(
        "/api/v1/reports/leave/allocations", headers=_headers()
    )
    balances = client.get("/api/v1/reports/leave/balances", headers=_headers())

    assert allocations.status_code == 200, allocations.text
    assert allocations.json() == {
        "allocations": [],
        "pagination": {"limit": 50, "has_more": False, "next_cursor": None},
    }
    assert balances.status_code == 200, balances.text
    assert balances.json() == {
        "balances": [],
        "pagination": {"limit": 50, "has_more": False, "next_cursor": None},
    }


def test_cursor_is_bound_to_filters_for_each_leave_report(
    client: TestClient, leave_report_uow: LeaveReportTestUow
) -> None:
    allocation = client.get(
        "/api/v1/reports/leave/allocations", params={"limit": 1}, headers=_headers()
    )
    cursor = allocation.json()["pagination"]["next_cursor"]
    assert cursor
    cross_filter = client.get(
        "/api/v1/reports/leave/allocations",
        params={"limit": 1, "employee_id": 12, "cursor": cursor},
        headers=_headers(),
    )
    assert cross_filter.status_code == 422
    cross_report = client.get(
        "/api/v1/reports/leave/balances", params={"cursor": cursor}, headers=_headers()
    )
    assert cross_report.status_code == 422
