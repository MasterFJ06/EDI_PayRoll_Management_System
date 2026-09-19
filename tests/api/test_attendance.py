from datetime import date
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies.unit_of_work import get_unit_of_work
from app.main import app
from app.infrastructure.security.jwt import create_access_token


class FakeEmployeeRepository:
    def __init__(self):
        self.employees = [
            SimpleNamespace(
                employee_id=10,
                employee_code="EMP010",
                user_id=None,
                employment_status="ACTIVE",
            )
        ]

    def get_by_id(self, employee_id):
        return next(
            (
                employee
                for employee in self.employees
                if employee.employee_id == employee_id
            ),
            None,
        )


class FakeAttendanceRepository:
    def __init__(self):
        self.attendance_records = []

    def get_by_employee_and_date(
        self,
        employee_id,
        attendance_date,
    ):
        return next(
            (
                attendance
                for attendance in self.attendance_records
                if attendance.employee_id == employee_id
                and attendance.attendance_date == attendance_date
            ),
            None,
        )

    def add(self, attendance):
        attendance.attendance_id = len(self.attendance_records) + 1
        self.attendance_records.append(attendance)
        return attendance


class FakeUserRepository:
    def __init__(self):
        self.users = {
            1: SimpleNamespace(
                user_id=1,
                username="john",
                email="john@example.com",
                status="ACTIVE",
            )
        }

    def get_by_id(self, user_id):
        return self.users.get(user_id)


class FakeUnitOfWork:
    def __init__(self):
        self.employees = FakeEmployeeRepository()
        self.attendance = FakeAttendanceRepository()
        self.users = FakeUserRepository()

        self.committed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass

    def commit(self):
        self.committed = True

    def rollback(self):
        pass


@pytest.fixture
def fake_uow():
    uow = FakeUnitOfWork()

    app.dependency_overrides[get_unit_of_work] = lambda: uow

    yield uow

    app.dependency_overrides.clear()


@pytest.fixture
def client():
    return TestClient(app)


def authenticated_headers():
    token = create_access_token(
        user_id=1,
        username="john",
    )

    return {
        "Authorization": f"Bearer {token}",
    }


def attendance_payload(**overrides):
    payload = {
        "employee_id": 10,
        "attendance_date": "2026-09-19",
        "check_in_time": "2026-09-19T09:00:00",
        "check_out_time": "2026-09-19T18:00:00",
        "attendance_status": "PRESENT",
    }

    payload.update(overrides)
    return payload


def test_create_attendance_requires_authentication(
    client,
    fake_uow,
):
    response = client.post(
        "/api/v1/attendance",
        json=attendance_payload(),
    )

    assert response.status_code == 401


def test_create_attendance(
    client,
    fake_uow,
):
    response = client.post(
        "/api/v1/attendance",
        json=attendance_payload(),
        headers=authenticated_headers(),
    )

    assert response.status_code == 201

    data = response.json()

    assert data["attendance_id"] == 1
    assert data["employee_id"] == 10
    assert data["attendance_date"] == "2026-09-19"
    assert data["check_in_time"] == "2026-09-19T09:00:00"
    assert data["check_out_time"] == "2026-09-19T18:00:00"
    assert data["attendance_status"] == "PRESENT"

    assert fake_uow.committed is True


def test_create_attendance_without_check_times(
    client,
    fake_uow,
):
    response = client.post(
        "/api/v1/attendance",
        json=attendance_payload(
            attendance_status="ABSENT",
            check_in_time=None,
            check_out_time=None,
        ),
        headers=authenticated_headers(),
    )

    assert response.status_code == 201

    data = response.json()

    assert data["attendance_status"] == "ABSENT"
    assert data["check_in_time"] is None
    assert data["check_out_time"] is None


def test_create_attendance_rejects_nonexistent_employee(
    client,
    fake_uow,
):
    response = client.post(
        "/api/v1/attendance",
        json=attendance_payload(
            employee_id=999,
        ),
        headers=authenticated_headers(),
    )

    assert response.status_code == 409
    assert "Employee does not exist" in response.json()["detail"]


def test_create_attendance_rejects_duplicate_date(
    client,
    fake_uow,
):
    client.post(
        "/api/v1/attendance",
        json=attendance_payload(),
        headers=authenticated_headers(),
    )

    response = client.post(
        "/api/v1/attendance",
        json=attendance_payload(),
        headers=authenticated_headers(),
    )

    assert response.status_code == 409
    assert (
        "Attendance already exists for this employee and date"
        in response.json()["detail"]
    )


def test_create_attendance_rejects_invalid_status(
    client,
    fake_uow,
):
    response = client.post(
        "/api/v1/attendance",
        json=attendance_payload(
            attendance_status="INVALID",
        ),
        headers=authenticated_headers(),
    )

    assert response.status_code == 409
    assert (
        "Attendance status must be PRESENT, ABSENT, HALF_DAY, "
        "ON_LEAVE, or HOLIDAY"
        in response.json()["detail"]
    )


def test_create_attendance_rejects_checkout_before_checkin(
    client,
    fake_uow,
):
    response = client.post(
        "/api/v1/attendance",
        json=attendance_payload(
            check_in_time="2026-09-19T18:00:00",
            check_out_time="2026-09-19T09:00:00",
        ),
        headers=authenticated_headers(),
    )

    assert response.status_code == 409
    assert (
        "Check-out time cannot be earlier than check-in time"
        in response.json()["detail"]
    )


def test_create_attendance_rejects_invalid_employee_id(
    client,
    fake_uow,
):
    response = client.post(
        "/api/v1/attendance",
        json=attendance_payload(
            employee_id=0,
        ),
        headers=authenticated_headers(),
    )

    assert response.status_code == 422


def test_create_attendance_rejects_missing_status(
    client,
    fake_uow,
):
    payload = attendance_payload()
    del payload["attendance_status"]

    response = client.post(
        "/api/v1/attendance",
        json=payload,
        headers=authenticated_headers(),
    )

    assert response.status_code == 422