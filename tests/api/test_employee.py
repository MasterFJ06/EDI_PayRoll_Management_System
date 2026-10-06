from datetime import date
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies.unit_of_work import get_unit_of_work
from app.main import app
from app.infrastructure.security.jwt import create_access_token


class FakeEmployeeRepository:
    def __init__(self):
        self.employees = []

    def get_by_code(self, employee_code):
        return next(
            (
                employee
                for employee in self.employees
                if employee.employee_code == employee_code
            ),
            None,
        )

    def get_by_user_id(self, user_id):
        return next(
            (
                employee
                for employee in self.employees
                if employee.user_id == user_id
            ),
            None,
        )

    def get_by_id(self, employee_id):
        return next(
            (
                employee
                for employee in self.employees
                if employee.employee_id == employee_id
            ),
            None,
        )

    def add(self, employee):
        employee.employee_id = len(self.employees) + 1
        self.employees.append(employee)
        return employee


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


class FakeDepartmentRepository:
    def get_by_id(self, department_id):
        if department_id == 10:
            return SimpleNamespace(
                department_id=10,
                department_code="IT",
                department_name="Information Technology",
                status="ACTIVE",
            )
        return None


class FakeDesignationRepository:
    def get_by_id(self, designation_id):
        if designation_id == 20:
            return SimpleNamespace(
                designation_id=20,
                designation_code="DEV",
                designation_name="Developer",
                status="ACTIVE",
            )
        return None


class FakeUnitOfWork:
    def __init__(self):
        self.employees = FakeEmployeeRepository()
        self.users = FakeUserRepository()
        self.departments = FakeDepartmentRepository()
        self.designations = FakeDesignationRepository()

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


def employee_payload(**overrides):
    payload = {
        "employee_code": "EMP001",
        "user_id": 1,
        "first_name": "John",
        "last_name": "Doe",
        "department_id": 10,
        "designation_id": 20,
        "manager_employee_id": None,
        "joining_date": "2026-01-01",
    }

    payload.update(overrides)
    return payload


def test_create_employee_requires_authentication(
    client,
    fake_uow,
):
    response = client.post(
        "/api/v1/employees",
        json=employee_payload(),
    )

    assert response.status_code == 401


def test_create_employee(
    client,
    fake_uow,
):
    response = client.post(
        "/api/v1/employees",
        json=employee_payload(),
        headers=authenticated_headers(),
    )

    assert response.status_code == 201

    data = response.json()

    assert data["employee_id"] == 1
    assert data["employee_code"] == "EMP001"
    assert data["user_id"] == 1
    assert data["first_name"] == "John"
    assert data["last_name"] == "Doe"
    assert data["department_id"] == 10
    assert data["designation_id"] == 20
    assert data["manager_employee_id"] is None
    assert data["joining_date"] == "2026-01-01"
    assert data["employment_status"] == "ACTIVE"

    assert fake_uow.committed is True


def test_create_employee_without_user(
    client,
    fake_uow,
):
    response = client.post(
        "/api/v1/employees",
        json=employee_payload(
            user_id=None,
            employee_code="EMP002",
        ),
        headers=authenticated_headers(),
    )

    assert response.status_code == 201

    data = response.json()

    assert data["user_id"] is None


def test_create_employee_rejects_duplicate_code(
    client,
    fake_uow,
):
    fake_uow.employees.add(
        SimpleNamespace(
            employee_id=1,
            employee_code="EMP001",
            user_id=None,
        )
    )

    response = client.post(
        "/api/v1/employees",
        json=employee_payload(),
        headers=authenticated_headers(),
    )

    assert response.status_code == 409
    assert "Employee code already exists" in response.json()["detail"]


def test_create_employee_rejects_nonexistent_user(
    client,
    fake_uow,
):
    response = client.post(
        "/api/v1/employees",
        json=employee_payload(
            user_id=999,
        ),
        headers=authenticated_headers(),
    )

    assert response.status_code == 409
    assert "User does not exist" in response.json()["detail"]


def test_create_employee_rejects_nonexistent_department(
    client,
    fake_uow,
):
    response = client.post(
        "/api/v1/employees",
        json=employee_payload(
            employee_code="EMP003",
            department_id=999,
        ),
        headers=authenticated_headers(),
    )

    assert response.status_code == 409
    assert "Department does not exist" in response.json()["detail"]


def test_create_employee_rejects_nonexistent_designation(
    client,
    fake_uow,
):
    response = client.post(
        "/api/v1/employees",
        json=employee_payload(
            employee_code="EMP004",
            designation_id=999,
        ),
        headers=authenticated_headers(),
    )

    assert response.status_code == 409
    assert "Designation does not exist" in response.json()["detail"]


def test_create_employee_rejects_nonexistent_manager(
    client,
    fake_uow,
):
    response = client.post(
        "/api/v1/employees",
        json=employee_payload(
            employee_code="EMP005",
            manager_employee_id=999,
        ),
        headers=authenticated_headers(),
    )

    assert response.status_code == 409
    assert "Manager employee does not exist" in response.json()["detail"]


def test_create_employee_rejects_terminated_manager(
    client,
    fake_uow,
):
    fake_uow.employees.employees.append(
        SimpleNamespace(
            employee_id=25,
            employee_code="MGR001",
            user_id=None,
            employment_status="TERMINATED",
        )
    )

    response = client.post(
        "/api/v1/employees",
        json=employee_payload(
            employee_code="EMP006",
            manager_employee_id=25,
        ),
        headers=authenticated_headers(),
    )

    assert response.status_code == 409
    assert (
        "terminated employee cannot be assigned as a manager"
        in response.json()["detail"]
    )


def test_create_employee_with_active_manager(
    client,
    fake_uow,
):
    fake_uow.employees.employees.append(
        SimpleNamespace(
            employee_id=25,
            employee_code="MGR001",
            user_id=None,
            employment_status="ACTIVE",
        )
    )

    response = client.post(
        "/api/v1/employees",
        json=employee_payload(
            employee_code="EMP007",
            manager_employee_id=25,
        ),
        headers=authenticated_headers(),
    )

    assert response.status_code == 201

    data = response.json()

    assert data["manager_employee_id"] == 25