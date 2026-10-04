from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies.unit_of_work import get_unit_of_work
from app.infrastructure.security.jwt import create_access_token
from app.main import app


class FakeEmployeeRepository:
    def get_by_id(self, employee_id):
        if employee_id in {5, 8}:
            return SimpleNamespace(employee_id=employee_id)
        return None


class FakeUserRepository:
    def get_by_id(self, user_id):
        if user_id == 1:
            return SimpleNamespace(user_id=1, username="tester", status="ACTIVE")
        return None


class FakeLeaveTypeRepository:
    def __init__(self):
        self.leave_types = []

    def get_by_id(self, leave_type_id):
        return next(
            (item for item in self.leave_types if item.leave_type_id == leave_type_id),
            None,
        )

    def get_by_code(self, code):
        return next((item for item in self.leave_types if item.leave_type_code == code), None)

    def get_by_name(self, name):
        return next((item for item in self.leave_types if item.leave_type_name == name), None)

    def add(self, leave_type):
        leave_type.leave_type_id = len(self.leave_types) + 1
        self.leave_types.append(leave_type)
        return leave_type


class FakeLeaveBalanceRepository:
    def __init__(self):
        self.leave_balances = []

    def get_by_id(self, leave_balance_id):
        return next(
            (item for item in self.leave_balances if item.leave_balance_id == leave_balance_id),
            None,
        )

    def get_by_employee_type_year(self, employee_id, leave_type_id, balance_year):
        return next(
            (
                item
                for item in self.leave_balances
                if (item.employee_id, item.leave_type_id, item.balance_year)
                == (employee_id, leave_type_id, balance_year)
            ),
            None,
        )

    def add(self, balance):
        balance.leave_balance_id = len(self.leave_balances) + 1
        self.leave_balances.append(balance)
        return balance


class FakeLeaveRequestRepository:
    def __init__(self):
        self.leave_requests = []

    def get_by_id(self, leave_request_id):
        return next(
            (item for item in self.leave_requests if item.leave_request_id == leave_request_id),
            None,
        )

    def add(self, request):
        request.leave_request_id = len(self.leave_requests) + 1
        self.leave_requests.append(request)
        return request


class FakeUnitOfWork:
    def __init__(self):
        self.users = FakeUserRepository()
        self.employees = FakeEmployeeRepository()
        self.leave_types = FakeLeaveTypeRepository()
        self.leave_balances = FakeLeaveBalanceRepository()
        self.leave_requests = FakeLeaveRequestRepository()
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
    token = create_access_token(user_id=1, username="tester")
    return {"Authorization": f"Bearer {token}"}


def leave_type_payload(**overrides):
    return {
        "leave_type_code": "ANNUAL",
        "leave_type_name": "Annual Leave",
        "description": "Paid annual leave",
        "is_active": True,
        **overrides,
    }


def leave_balance_payload(**overrides):
    return {
        "employee_id": 5,
        "leave_type_id": 1,
        "balance_year": 2026,
        "allocated_days": "20.00",
        "used_days": "2.00",
        **overrides,
    }


def leave_request_payload(**overrides):
    return {
        "employee_id": 5,
        "leave_type_id": 1,
        "start_date": "2026-10-10",
        "end_date": "2026-10-11",
        "requested_days": "2.00",
        "reason": "Personal leave",
        **overrides,
    }


def seed_leave_type(uow: FakeUnitOfWork) -> None:
    uow.leave_types.add(
        SimpleNamespace(
            leave_type_id=1,
            leave_type_code="ANNUAL",
            leave_type_name="Annual Leave",
        )
    )


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        ("/api/v1/leave-types", leave_type_payload()),
        ("/api/v1/leave-balances", leave_balance_payload()),
        ("/api/v1/leave-requests", leave_request_payload()),
    ],
)
def test_leave_endpoints_require_authentication(client, fake_uow, path, payload):
    response = client.post(path, json=payload)

    assert response.status_code == 401


def test_create_leave_type(client, fake_uow):
    response = client.post(
        "/api/v1/leave-types",
        json=leave_type_payload(),
        headers=authenticated_headers(),
    )

    assert response.status_code == 201
    assert response.json()["leave_type_id"] == 1
    assert response.json()["leave_type_code"] == "ANNUAL"
    assert fake_uow.committed is True


def test_create_leave_type_rejects_invalid_request(client, fake_uow):
    response = client.post(
        "/api/v1/leave-types",
        json=leave_type_payload(leave_type_name=""),
        headers=authenticated_headers(),
    )

    assert response.status_code == 422
    assert fake_uow.committed is False


def test_create_leave_type_rejects_duplicate_key(client, fake_uow):
    headers = authenticated_headers()
    client.post("/api/v1/leave-types", json=leave_type_payload(), headers=headers)

    response = client.post(
        "/api/v1/leave-types",
        json=leave_type_payload(leave_type_name="Different Name"),
        headers=headers,
    )

    assert response.status_code == 409
    assert "code is already registered" in response.json()["detail"]


def test_create_leave_type_returns_domain_failure(client, fake_uow):
    response = client.post(
        "/api/v1/leave-types",
        json=leave_type_payload(leave_type_code=" "),
        headers=authenticated_headers(),
    )

    assert response.status_code == 409
    assert "code cannot be blank" in response.json()["detail"]


def test_create_leave_balance(client, fake_uow):
    seed_leave_type(fake_uow)
    response = client.post(
        "/api/v1/leave-balances",
        json=leave_balance_payload(),
        headers=authenticated_headers(),
    )

    assert response.status_code == 201
    assert response.json()["leave_balance_id"] == 1
    assert response.json()["allocated_days"] == "20.00"
    assert fake_uow.committed is True


@pytest.mark.parametrize(
    ("payload", "detail"),
    [
        (leave_balance_payload(employee_id=999), "Employee does not exist"),
        (leave_balance_payload(leave_type_id=999), "Leave type does not exist"),
    ],
)
def test_create_leave_balance_rejects_missing_reference(client, fake_uow, payload, detail):
    response = client.post(
        "/api/v1/leave-balances",
        json=payload,
        headers=authenticated_headers(),
    )

    assert response.status_code == 409
    assert detail in response.json()["detail"]


@pytest.mark.parametrize(
    "payload",
    [
        leave_balance_payload(allocated_days="-1.00"),
        leave_balance_payload(used_days="-1.00"),
    ],
)
def test_create_leave_balance_rejects_invalid_numeric_fields(client, fake_uow, payload):
    response = client.post(
        "/api/v1/leave-balances",
        json=payload,
        headers=authenticated_headers(),
    )

    assert response.status_code == 422


def test_create_leave_balance_rejects_used_days_above_allocation(client, fake_uow):
    seed_leave_type(fake_uow)
    response = client.post(
        "/api/v1/leave-balances",
        json=leave_balance_payload(allocated_days="1.00", used_days="2.00"),
        headers=authenticated_headers(),
    )

    assert response.status_code == 409
    assert "cannot exceed" in response.json()["detail"]


def test_create_leave_request(client, fake_uow):
    seed_leave_type(fake_uow)
    response = client.post(
        "/api/v1/leave-requests",
        json=leave_request_payload(),
        headers=authenticated_headers(),
    )

    assert response.status_code == 201
    assert response.json()["leave_request_id"] == 1
    assert response.json()["status"] == "PENDING"
    assert response.json()["requested_days"] == "2.00"
    assert fake_uow.committed is True


@pytest.mark.parametrize(
    ("payload", "detail"),
    [
        (leave_request_payload(employee_id=999), "Employee does not exist"),
        (leave_request_payload(leave_type_id=999), "Leave type does not exist"),
    ],
)
def test_create_leave_request_rejects_missing_reference(client, fake_uow, payload, detail):
    response = client.post(
        "/api/v1/leave-requests",
        json=payload,
        headers=authenticated_headers(),
    )

    assert response.status_code == 409
    assert detail in response.json()["detail"]


def test_create_leave_request_rejects_invalid_date_range(client, fake_uow):
    seed_leave_type(fake_uow)
    response = client.post(
        "/api/v1/leave-requests",
        json=leave_request_payload(
            start_date="2026-10-12", end_date="2026-10-11"
        ),
        headers=authenticated_headers(),
    )

    assert response.status_code == 409
    assert "end date cannot precede start date" in response.json()["detail"]


@pytest.mark.parametrize(
    "changes",
    [
        {"requested_days": "0.00"},
        {"status": "NOT_A_STATUS"},
    ],
)
def test_create_leave_request_rejects_invalid_schema_values(client, fake_uow, changes):
    response = client.post(
        "/api/v1/leave-requests",
        json=leave_request_payload(**changes),
        headers=authenticated_headers(),
    )

    assert response.status_code == 422


def test_create_leave_request_rejects_inconsistent_review_fields(client, fake_uow):
    seed_leave_type(fake_uow)
    response = client.post(
        "/api/v1/leave-requests",
        json=leave_request_payload(status="APPROVED"),
        headers=authenticated_headers(),
    )

    assert response.status_code == 409
    assert "require reviewer and review time" in response.json()["detail"]


def test_create_leave_request_rejects_missing_reviewer_employee(client, fake_uow):
    seed_leave_type(fake_uow)
    response = client.post(
        "/api/v1/leave-requests",
        json=leave_request_payload(
            status="APPROVED",
            reviewed_by_employee_id=999,
            reviewed_at="2026-09-20T12:00:00",
        ),
        headers=authenticated_headers(),
    )

    assert response.status_code == 409
    assert "Reviewer employee does not exist" in response.json()["detail"]


def test_leave_routes_appear_in_generated_openapi(client):
    docs_response = client.get("/docs")
    schema_response = client.get("/openapi.json")

    assert docs_response.status_code == 200
    assert schema_response.status_code == 200
    schema = schema_response.json()
    for path in (
        "/api/v1/leave-types",
        "/api/v1/leave-balances",
        "/api/v1/leave-requests",
    ):
        operation = schema["paths"][path]["post"]
        assert operation["responses"]["201"]
        assert operation["security"]
        assert "Leave Management" in operation["tags"]
