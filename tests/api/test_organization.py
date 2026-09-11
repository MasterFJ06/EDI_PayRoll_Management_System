from unittest.mock import Mock

from fastapi.testclient import TestClient

from app.api.dependencies.unit_of_work import get_unit_of_work
from app.infrastructure.persistence.models.department import Department
from app.infrastructure.persistence.models.designation import Designation
from app.infrastructure.security.jwt import create_access_token
from app.main import app


class FakeDepartmentRepository:
    def __init__(self) -> None:
        self.departments: list[Department] = []

    def get_by_code(self, department_code: str) -> Department | None:
        return next(
            (
                department
                for department in self.departments
                if department.department_code == department_code
            ),
            None,
        )

    def get_by_name(self, department_name: str) -> Department | None:
        return next(
            (
                department
                for department in self.departments
                if department.department_name == department_name
            ),
            None,
        )

    def add(self, department: Department) -> Department:
        department.department_id = len(self.departments) + 1
        self.departments.append(department)
        return department


class FakeDesignationRepository:
    def __init__(self) -> None:
        self.designations: list[Designation] = []

    def get_by_code(self, designation_code: str) -> Designation | None:
        return next(
            (
                designation
                for designation in self.designations
                if designation.designation_code == designation_code
            ),
            None,
        )

    def get_by_name(self, designation_name: str) -> Designation | None:
        return next(
            (
                designation
                for designation in self.designations
                if designation.designation_name == designation_name
            ),
            None,
        )

    def add(self, designation: Designation) -> Designation:
        designation.designation_id = len(self.designations) + 1
        self.designations.append(designation)
        return designation


def create_authenticated_client() -> TestClient:
    user = Mock()
    user.user_id = 1
    user.username = "john"
    user.status = "ACTIVE"

    uow = Mock()

    uow.users.get_by_id.return_value = user
    uow.departments = FakeDepartmentRepository()
    uow.designations = FakeDesignationRepository()

    def override_unit_of_work():
        yield uow

    app.dependency_overrides[get_unit_of_work] = override_unit_of_work

    token = create_access_token(
        user_id=user.user_id,
        username=user.username,
    )

    client = TestClient(app)
    client.headers.update(
        {"Authorization": f"Bearer {token}"}
    )

    return client


def teardown_function() -> None:
    app.dependency_overrides.clear()


def test_create_department() -> None:
    client = create_authenticated_client()

    response = client.post(
        "/api/v1/departments",
        json={
            "department_code": "IT",
            "department_name": "Information Technology",
        },
    )

    assert response.status_code == 201

    body = response.json()

    assert body["department_id"] == 1
    assert body["department_code"] == "IT"
    assert body["department_name"] == "Information Technology"
    assert body["status"] == "ACTIVE"


def test_create_designation() -> None:
    client = create_authenticated_client()

    response = client.post(
        "/api/v1/designations",
        json={
            "designation_code": "DEV",
            "designation_name": "Software Developer",
        },
    )

    assert response.status_code == 201

    body = response.json()

    assert body["designation_id"] == 1
    assert body["designation_code"] == "DEV"
    assert body["designation_name"] == "Software Developer"
    assert body["status"] == "ACTIVE"


def test_create_department_requires_authentication(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/departments",
        json={
            "department_code": "IT",
            "department_name": "Information Technology",
        },
    )

    assert response.status_code == 401


def test_create_designation_requires_authentication(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/designations",
        json={
            "designation_code": "DEV",
            "designation_name": "Software Developer",
        },
    )

    assert response.status_code == 401