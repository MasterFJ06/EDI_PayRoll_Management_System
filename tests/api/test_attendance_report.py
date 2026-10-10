from collections.abc import Generator
from datetime import date, datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies.unit_of_work import get_unit_of_work
from app.domain.attendance.attendance_report import AttendanceReportRecord
from app.infrastructure.security.jwt import create_access_token
from app.main import app


class AttendanceReportTestUow:
    def __init__(self) -> None:
        self.user = SimpleNamespace(
            user_id=95, username="attendance-report-api", status="ACTIVE"
        )
        self.users = SimpleNamespace(
            get_by_id=lambda user_id: self.user if user_id == 95 else None
        )
        self.allowed = True
        self.permission_checks: list[tuple[int, str]] = []
        self.authorization = SimpleNamespace(has_permission=self.has_permission)
        self.records = [
            AttendanceReportRecord(
                attendance_id=attendance_id,
                employee_id=employee_id,
                employee_code=f"EMP-{employee_id}",
                first_name="First",
                last_name=str(employee_id),
                department_id=5 if employee_id != 20 else 7,
                department_name="Finance" if employee_id != 20 else "Operations",
                designation_id=6 if employee_id != 20 else 9,
                designation_name="Analyst" if employee_id != 20 else "Clerk",
                attendance_date=day,
                attendance_status=attendance_status,
                check_in_time=None,
                check_out_time=datetime(2026, 2, 3, 17) if attendance_id == 12 else None,
            )
            for attendance_id, employee_id, day, attendance_status in (
                (10, 10, date(2026, 2, 3), "PRESENT"),
                (12, 12, date(2026, 2, 3), "ABSENT"),
                (20, 20, date(2026, 2, 4), "HOLIDAY"),
            )
        ]
        self.calls: list[dict[str, object]] = []
        self.attendance = SimpleNamespace(list_report_page=self.list_report_page)
        self.audit_writes: list[object] = []
        self.audit_events = SimpleNamespace(add=self.audit_writes.append)
        self.commits = 0

    def has_permission(self, user_id: int, permission_code: str) -> bool:
        self.permission_checks.append((user_id, permission_code))
        return self.allowed and permission_code == "report.attendance.read"

    def list_report_page(self, **kwargs):
        self.calls.append(kwargs)
        rows = [
            row
            for row in self.records
            if (kwargs["date_from"] is None or row.attendance_date >= kwargs["date_from"])
            and (kwargs["date_to"] is None or row.attendance_date <= kwargs["date_to"])
            and (kwargs["employee_id"] is None or row.employee_id == kwargs["employee_id"])
            and (kwargs["department_id"] is None or row.department_id == kwargs["department_id"])
            and (
                kwargs["attendance_status"] is None
                or row.attendance_status == kwargs["attendance_status"]
            )
            and (
                kwargs["after_attendance_date"] is None
                or (row.attendance_date, row.attendance_id)
                > (kwargs["after_attendance_date"], kwargs["after_attendance_id"])
            )
        ]
        rows.sort(key=lambda row: (row.attendance_date, row.attendance_id))
        return rows[: kwargs["limit"]]


@pytest.fixture
def attendance_report_uow() -> Generator[AttendanceReportTestUow, None, None]:
    uow = AttendanceReportTestUow()
    app.dependency_overrides[get_unit_of_work] = lambda: uow
    yield uow
    app.dependency_overrides.pop(get_unit_of_work, None)


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


def _headers() -> dict[str, str]:
    token = create_access_token(95, "attendance-report-api")
    return {"Authorization": f"Bearer {token}"}


def test_attendance_report_requires_authentication_and_permission(
    client: TestClient,
    attendance_report_uow: AttendanceReportTestUow,
) -> None:
    path = "/api/v1/reports/attendance"
    assert client.get(path).status_code == 401
    assert client.get(path, headers={"Authorization": "Bearer invalid"}).status_code == 401

    attendance_report_uow.allowed = False
    assert client.get(path, headers=_headers()).status_code == 403
    assert attendance_report_uow.permission_checks == [
        (95, "report.attendance.read")
    ]
    assert attendance_report_uow.calls == []


def test_attendance_report_has_exact_projection_defaults_and_no_audit_write(
    client: TestClient,
    attendance_report_uow: AttendanceReportTestUow,
) -> None:
    response = client.get("/api/v1/reports/attendance", headers=_headers())
    assert response.status_code == 200, response.text
    body = response.json()
    fields = {
        "attendance_id", "employee_id", "employee_code", "first_name", "last_name",
        "department_id", "department_name", "designation_id", "designation_name",
        "attendance_date", "attendance_status", "check_in_time", "check_out_time",
    }
    assert set(body) == {"attendance_records", "pagination"}
    assert set(body["attendance_records"][0]) == fields
    assert {
        "user_id", "email", "manager_employee_id", "password_hash", "phone_number"
    }.isdisjoint(fields)
    assert body["attendance_records"][0]["check_in_time"] is None
    assert body["attendance_records"][0]["check_out_time"] is None
    assert body["pagination"] == {"limit": 50, "has_more": False, "next_cursor": None}
    assert attendance_report_uow.calls[0]["limit"] == 51
    assert attendance_report_uow.audit_writes == []
    assert attendance_report_uow.commits == 0


def test_attendance_report_filters_and_reversed_date_range_validation(
    client: TestClient,
    attendance_report_uow: AttendanceReportTestUow,
) -> None:
    response = client.get(
        "/api/v1/reports/attendance",
        params={
            "date_from": "2026-02-03",
            "date_to": "2026-02-03",
            "employee_id": 12,
            "department_id": 5,
            "attendance_status": "ABSENT",
        },
        headers=_headers(),
    )
    assert response.status_code == 200, response.text
    assert [row["attendance_id"] for row in response.json()["attendance_records"]] == [12]
    assert attendance_report_uow.calls[0] == {
        "date_from": date(2026, 2, 3),
        "date_to": date(2026, 2, 3),
        "employee_id": 12,
        "department_id": 5,
        "attendance_status": "ABSENT",
        "after_attendance_date": None,
        "after_attendance_id": None,
        "limit": 51,
    }

    reversed_range = client.get(
        "/api/v1/reports/attendance",
        params={"date_from": "2026-02-04", "date_to": "2026-02-03"},
        headers=_headers(),
    )
    assert reversed_range.status_code == 422
    for invalid_params in (
        {"employee_id": 0},
        {"department_id": -1},
        {"attendance_status": "UNKNOWN"},
        {"date_from": "not-a-date"},
        {"limit": 0},
        {"limit": 101},
    ):
        invalid = client.get(
            "/api/v1/reports/attendance", params=invalid_params, headers=_headers()
        )
        assert invalid.status_code == 422, (invalid_params, invalid.text)


@pytest.mark.parametrize(
    "params,expected_ids",
    [
        ({"date_from": "2026-02-04"}, [20]),
        ({"date_to": "2026-02-03"}, [10, 12]),
        ({"employee_id": 12}, [12]),
        ({"department_id": 7}, [20]),
        ({"attendance_status": "HOLIDAY"}, [20]),
    ],
)
def test_attendance_report_each_filter_is_applied(
    client: TestClient,
    attendance_report_uow: AttendanceReportTestUow,
    params: dict[str, object],
    expected_ids: list[int],
) -> None:
    response = client.get(
        "/api/v1/reports/attendance", params=params, headers=_headers()
    )
    assert response.status_code == 200, response.text
    assert [
        row["attendance_id"] for row in response.json()["attendance_records"]
    ] == expected_ids


@pytest.mark.parametrize("limit", [1, 100])
def test_attendance_report_accepts_limit_boundaries(
    client: TestClient,
    attendance_report_uow: AttendanceReportTestUow,
    limit: int,
) -> None:
    response = client.get(
        "/api/v1/reports/attendance", params={"limit": limit}, headers=_headers()
    )
    assert response.status_code == 200
    assert response.json()["pagination"]["limit"] == limit
    assert attendance_report_uow.calls[0]["limit"] == limit + 1


def test_attendance_report_cursor_paginates_and_rejects_invalid_cursors(
    client: TestClient,
    attendance_report_uow: AttendanceReportTestUow,
) -> None:
    params = {"limit": 1, "date_from": "2026-02-03", "date_to": "2026-02-03"}
    first = client.get("/api/v1/reports/attendance", params=params, headers=_headers())
    assert first.status_code == 200
    first_body = first.json()
    assert [row["attendance_id"] for row in first_body["attendance_records"]] == [10]
    cursor = first_body["pagination"]["next_cursor"]
    assert cursor

    second = client.get(
        "/api/v1/reports/attendance",
        params={**params, "cursor": cursor},
        headers=_headers(),
    )
    assert second.status_code == 200
    assert [row["attendance_id"] for row in second.json()["attendance_records"]] == [12]
    assert second.json()["pagination"]["has_more"] is False
    assert second.json()["pagination"]["next_cursor"] is None
    assert attendance_report_uow.calls[1]["after_attendance_date"] == date(2026, 2, 3)
    assert attendance_report_uow.calls[1]["after_attendance_id"] == 10

    for invalid_params in (
        {**params, "cursor": "malformed"},
        {**params, "cursor": cursor[:-1] + ("A" if cursor[-1] != "A" else "B")},
        {**params, "cursor": cursor, "attendance_status": "PRESENT"},
    ):
        invalid = client.get(
            "/api/v1/reports/attendance", params=invalid_params, headers=_headers()
        )
        assert invalid.status_code == 422
