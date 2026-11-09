from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient

from app.api.dependencies.unit_of_work import get_unit_of_work
from app.infrastructure.security.jwt import create_access_token
from app.main import app


class FakeEmployeeRepo:
    def __init__(self):
        self.employees = [
            SimpleNamespace(
                employee_id=1,
                employee_code="EMP001",
                first_name="Farhan",
                last_name="Member",
                department_id=1,
                designation_id=1,
                user_id=2,
                employment_status="ACTIVE",
            )
        ]

    def get_all(self):
        return self.employees

    def get_by_id(self, emp_id):
        return next((e for e in self.employees if e.employee_id == emp_id), None)

    def get_by_code(self, code):
        return next((e for e in self.employees if e.employee_code == code), None)

    def get_by_user_id(self, user_id):
        return next((e for e in self.employees if e.user_id == user_id), None)

    def add(self, emp):
        self.employees.append(emp)
        return emp


class FakeLeaveRepo:
    def __init__(self):
        self.types = [
            SimpleNamespace(leave_type_id=1, leave_type_code="CASUAL", leave_type_name="Casual"),
            SimpleNamespace(leave_type_id=2, leave_type_code="SICK", leave_type_name="Sick"),
            SimpleNamespace(leave_type_id=3, leave_type_code="EARNED", leave_type_name="Earned"),
        ]
        self.requests = [
            SimpleNamespace(
                leave_request_id=1,
                employee_id=1,
                leave_type_id=1,
                start_date=date(2026, 11, 1),
                end_date=date(2026, 11, 2),
                requested_days=Decimal("2"),
                reason="Rest",
                status="PENDING",
                reviewed_by_employee_id=None,
                reviewed_at=None,
                created_at=datetime(2026, 10, 24),
            )
        ]
        self.balances = [
            SimpleNamespace(
                leave_balance_id=1,
                employee_id=1,
                leave_type_id=1,
                balance_year=2026,
                allocated_days=Decimal("12"),
                used_days=Decimal("5"),
            )
        ]

    def get_types(self):
        return self.types

    def get_type_by_id(self, type_id):
        return next((t for t in self.types if t.leave_type_id == type_id), None)

    def get_type_by_code(self, code):
        return next((t for t in self.types if t.leave_type_code == code), None)

    def add_type(self, lt):
        self.types.append(lt)
        return lt

    def get_requests(self, emp_id=None):
        if emp_id:
            return [r for r in self.requests if r.employee_id == emp_id]
        return self.requests

    def get_request_by_id(self, req_id):
        return next((r for r in self.requests if r.leave_request_id == req_id), None)

    def add_request(self, req):
        req.leave_request_id = len(self.requests) + 1
        self.requests.append(req)
        return req

    def update_request(self, req):
        return req

    def get_balances(self, emp_id=None):
        if emp_id:
            return [b for b in self.balances if b.employee_id == emp_id]
        return self.balances

    def add_balance(self, b):
        self.balances.append(b)
        return b


class FakeUserRepo:
    def __init__(self):
        self.user = SimpleNamespace(
            user_id=2,
            username="farhan.member",
            email="farhan@company.in",
            status="ACTIVE",
            linked_employee_id=1,
        )

    def get_by_id(self, uid):
        return self.user if uid == 2 else None

    def get_by_username(self, uname):
        return self.user if uname == "farhan.member" else None


class FakeRoleRepo:
    def get_user_roles(self, uid):
        return [SimpleNamespace(role_name="Employee")]


class FakeUnitOfWork:
    def __init__(self):
        self.employees = FakeEmployeeRepo()
        self.leaves = FakeLeaveRepo()
        self.users = FakeUserRepo()
        self.roles = FakeRoleRepo()
        self.session = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def commit(self):
        pass

    def rollback(self):
        pass


@pytest.fixture
def fake_client():
    uow = FakeUnitOfWork()
    app.dependency_overrides[get_unit_of_work] = lambda: uow

    client = TestClient(app)
    token = create_access_token(user_id=2, username="farhan.member")
    client.headers.update({"Authorization": f"Bearer {token}"})

    yield client

    app.dependency_overrides.clear()


def test_list_leaves_dual_casing(fake_client):
    res = fake_client.get("/api/v1/leaves")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 1
    first = data[0]
    # Check camelCase
    assert first["employeeId"] == "EMP001"
    assert first["leaveType"] == "Casual"
    assert first["startDate"] == "2026-11-01"
    assert first["totalDays"] == 2.0
    # Check snake_case
    assert first["employee_id"] == "EMP001"
    assert first["leave_type"] == "Casual"
    assert first["start_date"] == "2026-11-01"
    assert first["total_days"] == 2.0


def test_list_leave_balances_dual_casing(fake_client):
    res = fake_client.get("/api/v1/leave-balances?employee_id=EMP001")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 1
    first = data[0]
    assert first["employeeId"] == "EMP001"
    assert first["employee_id"] == "EMP001"
    assert first["leaveType"] == "Casual"
    assert first["leave_type"] == "Casual"
    assert first["balance"] == 7.0


def test_apply_leave_with_camel_case_payload(fake_client):
    payload = {
        "employeeId": "EMP001",
        "leaveType": "Sick",
        "startDate": "2026-11-10",
        "endDate": "2026-11-12",
        "totalDays": 3,
        "reason": "Doctor appointment and recovery",
    }
    res = fake_client.post("/api/v1/leaves", json=payload)
    assert res.status_code == 201
    created = res.json()
    assert created["employeeId"] == "EMP001"
    assert created["employee_id"] == "EMP001"
    assert created["leaveType"] == "Sick"
    assert created["leave_type"] == "Sick"
    assert created["status"] == "Pending"
    assert created["totalDays"] == 3.0


def test_apply_leave_defaults_to_authenticated_member(fake_client):
    # Member applies without specifying employeeId
    payload = {
        "leaveType": "Casual",
        "startDate": "2026-12-01",
        "endDate": "2026-12-02",
        "reason": "Personal time off",
    }
    res = fake_client.post("/api/v1/leaves", json=payload)
    assert res.status_code == 201
    created = res.json()
    assert created["employeeId"] == "EMP001"
    assert created["leaveType"] == "Casual"
