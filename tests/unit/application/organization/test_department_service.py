import pytest

from app.application.organization.department_service import DepartmentService
from app.application.organization.schemas import DepartmentCreateRequest
from app.domain.shared.exceptions import BusinessRuleViolation
from app.infrastructure.persistence.models.department import Department


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


class FakeUnitOfWork:
    def __init__(self) -> None:
        self.departments = FakeDepartmentRepository()
        self.committed = False

    def commit(self) -> None:
        self.committed = True


def test_create_department() -> None:
    uow = FakeUnitOfWork()
    service = DepartmentService(uow)

    request = DepartmentCreateRequest(
        department_code="IT",
        department_name="Information Technology",
    )

    response = service.create(request)

    assert response.department_id == 1
    assert response.department_code == "IT"
    assert response.department_name == "Information Technology"
    assert response.status == "ACTIVE"
    assert uow.committed is True


def test_create_department_strips_code_and_name() -> None:
    uow = FakeUnitOfWork()
    service = DepartmentService(uow)

    request = DepartmentCreateRequest(
        department_code=" IT ",
        department_name=" Information Technology ",
    )

    response = service.create(request)

    assert response.department_code == "IT"
    assert response.department_name == "Information Technology"


def test_create_department_rejects_duplicate_code() -> None:
    uow = FakeUnitOfWork()
    existing_department = Department(
        department_code="IT",
        department_name="Information Technology",
        status="ACTIVE",
    )
    uow.departments.add(existing_department)

    service = DepartmentService(uow)

    request = DepartmentCreateRequest(
        department_code="IT",
        department_name="Another Department",
    )

    with pytest.raises(BusinessRuleViolation, match="code is already registered"):
        service.create(request)


def test_create_department_rejects_duplicate_name() -> None:
    uow = FakeUnitOfWork()
    existing_department = Department(
        department_code="IT",
        department_name="Information Technology",
        status="ACTIVE",
    )
    uow.departments.add(existing_department)

    service = DepartmentService(uow)

    request = DepartmentCreateRequest(
        department_code="TECH",
        department_name="Information Technology",
    )

    with pytest.raises(BusinessRuleViolation, match="name is already registered"):
        service.create(request)


def test_create_department_requires_started_unit_of_work() -> None:
    class UnstartedUnitOfWork:
        departments = None

    service = DepartmentService(UnstartedUnitOfWork())

    request = DepartmentCreateRequest(
        department_code="IT",
        department_name="Information Technology",
    )

    with pytest.raises(
        RuntimeError,
        match="Unit of Work has not been started",
    ):
        service.create(request)