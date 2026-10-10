from collections.abc import Generator
from datetime import date
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies.unit_of_work import get_unit_of_work
from app.domain.employee.employee_report import EmployeeReportRecord
from app.infrastructure.security.jwt import create_access_token
from app.main import app


class EmployeeReportTestUow:
    def __init__(self) -> None:
        self.user = SimpleNamespace(user_id=95, username="employee-report-api", status="ACTIVE")
        self.users = SimpleNamespace(get_by_id=lambda user_id: self.user if user_id == 95 else None)
        self.allowed = True
        self.permission_checks: list[tuple[int, str]] = []
        self.authorization = SimpleNamespace(has_permission=self.has_permission)
        self.records = [
            EmployeeReportRecord(
                employee_id=employee_id,
                employee_code=f"EMP-{employee_id}",
                first_name="First",
                last_name="Last",
                department_id=5,
                department_name="Finance",
                designation_id=6,
                designation_name="Analyst",
                joining_date=date(2022, 3, 1),
                employment_end_date=None,
                employment_status=status,
            )
            for employee_id, status in ((10, "ACTIVE"), (12, "INACTIVE"), (20, "TERMINATED"))
        ]
        self.calls: list[dict[str, object]] = []
        self.employees = SimpleNamespace(list_report_page=self.list_report_page)

    def has_permission(self, user_id: int, code: str) -> bool:
        self.permission_checks.append((user_id, code))
        return self.allowed and code == "report.employee.read"

    def list_report_page(self, **kwargs):
        self.calls.append(kwargs)
        rows = [
            row for row in self.records
            if (kwargs["employee_code"] is None or row.employee_code == kwargs["employee_code"])
            and (kwargs["department_id"] is None or row.department_id == kwargs["department_id"])
            and (kwargs["designation_id"] is None or row.designation_id == kwargs["designation_id"])
            and (kwargs["employment_status"] is None or row.employment_status == kwargs["employment_status"])
            and (kwargs["after_employee_id"] is None or row.employee_id > kwargs["after_employee_id"])
        ]
        return rows[: kwargs["limit"]]


@pytest.fixture
def employee_report_uow() -> Generator[EmployeeReportTestUow, None, None]:
    uow = EmployeeReportTestUow()
    app.dependency_overrides[get_unit_of_work] = lambda: uow
    yield uow
    app.dependency_overrides.pop(get_unit_of_work, None)


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


def _headers() -> dict[str, str]:
    token = create_access_token(95, "employee-report-api")
    return {"Authorization": f"Bearer {token}"}


def test_employee_report_requires_authentication_and_permission(
    client: TestClient, employee_report_uow: EmployeeReportTestUow
) -> None:
    path = "/api/v1/reports/employees"
    assert client.get(path).status_code == 401
    employee_report_uow.allowed = False
    assert client.get(path, headers=_headers()).status_code == 403
    assert employee_report_uow.permission_checks == [(95, "report.employee.read")]


def test_employee_report_has_exact_safe_projection_and_defaults(
    client: TestClient, employee_report_uow: EmployeeReportTestUow
) -> None:
    response = client.get("/api/v1/reports/employees", headers=_headers())
    assert response.status_code == 200, response.text
    body = response.json()
    fields = {
        "employee_id", "employee_code", "first_name", "last_name",
        "department_id", "department_name", "designation_id", "designation_name",
        "joining_date", "employment_end_date", "employment_status",
    }
    assert set(body) == {"employees", "pagination"}
    assert set(body["employees"][0]) == fields
    assert {"user_id", "email", "manager_employee_id", "password_hash"}.isdisjoint(fields)
    assert [row["employee_id"] for row in body["employees"]] == [10, 12, 20]
    assert body["employees"][0]["department_name"] == "Finance"
    assert body["pagination"] == {"limit": 50, "has_more": False, "next_cursor": None}
    assert employee_report_uow.calls[0]["limit"] == 51


@pytest.mark.parametrize(
    "params,expected",
    [
        ({"employee_code": "EMP-12"}, [12]),
        ({"department_id": 5}, [10, 12, 20]),
        ({"designation_id": 6}, [10, 12, 20]),
        ({"employment_status": "TERMINATED"}, [20]),
        ({"department_id": 999}, []),
        ({"employee_code": "EMP"}, []),
    ],
)
def test_employee_report_filters_are_exact(
    client: TestClient,
    employee_report_uow: EmployeeReportTestUow,
    params: dict[str, object],
    expected: list[int],
) -> None:
    response = client.get("/api/v1/reports/employees", params=params, headers=_headers())
    assert response.status_code == 200, response.text
    assert [row["employee_id"] for row in response.json()["employees"]] == expected


@pytest.mark.parametrize(
    "params",
    [
        {"limit": 0}, {"limit": 101}, {"department_id": 0},
        {"designation_id": -1}, {"employment_status": "ON_LEAVE"},
        {"employee_code": ""},
    ],
)
def test_employee_report_rejects_invalid_query_parameters(
    client: TestClient,
    employee_report_uow: EmployeeReportTestUow,
    params: dict[str, object],
) -> None:
    response = client.get("/api/v1/reports/employees", params=params, headers=_headers())
    assert response.status_code == 422
    assert employee_report_uow.calls == []


@pytest.mark.parametrize("limit", [1, 100])
def test_employee_report_accepts_limit_boundaries(
    client: TestClient, employee_report_uow: EmployeeReportTestUow, limit: int
) -> None:
    response = client.get(
        "/api/v1/reports/employees", params={"limit": limit}, headers=_headers()
    )
    assert response.status_code == 200
    assert response.json()["pagination"]["limit"] == limit
    assert employee_report_uow.calls[0]["limit"] == limit + 1


def test_employee_report_cursor_paginates_and_rejects_filter_mismatch(
    client: TestClient, employee_report_uow: EmployeeReportTestUow
) -> None:
    first = client.get(
        "/api/v1/reports/employees", params={"limit": 1}, headers=_headers()
    )
    assert first.status_code == 200
    first_body = first.json()
    assert [item["employee_id"] for item in first_body["employees"]] == [10]
    cursor = first_body["pagination"]["next_cursor"]
    assert cursor
    second = client.get(
        "/api/v1/reports/employees", params={"limit": 1, "cursor": cursor}, headers=_headers()
    )
    assert second.status_code == 200
    assert [item["employee_id"] for item in second.json()["employees"]] == [12]
    assert second.json()["pagination"]["has_more"] is True
    third = client.get(
        "/api/v1/reports/employees",
        params={"limit": 1, "cursor": second.json()["pagination"]["next_cursor"]},
        headers=_headers(),
    )
    assert third.status_code == 200
    assert [item["employee_id"] for item in third.json()["employees"]] == [20]
    assert third.json()["pagination"] == {
        "limit": 1, "has_more": False, "next_cursor": None
    }
    assert third.json()["pagination"]["next_cursor"] is None
    mismatch = client.get(
        "/api/v1/reports/employees",
        params={"limit": 1, "cursor": cursor, "employment_status": "ACTIVE"},
        headers=_headers(),
    )
    malformed = client.get(
        "/api/v1/reports/employees", params={"cursor": "bad"}, headers=_headers()
    )
    assert mismatch.status_code == 422
    assert malformed.status_code == 422
