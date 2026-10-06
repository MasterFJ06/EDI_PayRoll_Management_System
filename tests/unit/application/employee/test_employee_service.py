from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.application.employee.employee_service import EmployeeService
from app.application.employee.schemas import EmployeeCreateRequest
from app.domain.shared.exceptions import BusinessRuleViolation


def create_request(**overrides) -> EmployeeCreateRequest:
    data = {
        "employee_code": "EMP001",
        "user_id": 1,
        "first_name": "John",
        "last_name": "Doe",
        "department_id": 10,
        "designation_id": 20,
        "manager_employee_id": None,
        "joining_date": date(2026, 1, 1),
    }
    data.update(overrides)
    return EmployeeCreateRequest(**data)


def create_uow():
    uow = Mock()

    uow.employees = Mock()
    uow.users = Mock()
    uow.departments = Mock()
    uow.designations = Mock()

    return uow


def configure_valid_dependencies(uow):
    uow.employees.get_by_code.return_value = None
    uow.employees.get_by_user_id.return_value = None

    uow.users.get_by_id.return_value = SimpleNamespace(
        user_id=1,
        status="ACTIVE",
    )

    uow.departments.get_by_id.return_value = SimpleNamespace(
        department_id=10,
        status="ACTIVE",
    )

    uow.designations.get_by_id.return_value = SimpleNamespace(
        designation_id=20,
        status="ACTIVE",
    )


def test_create_employee():
    uow = create_uow()
    configure_valid_dependencies(uow)

    def add_employee(employee):
        employee.employee_id = 100
        return employee

    uow.employees.add.side_effect = add_employee

    service = EmployeeService(uow)

    result = service.create(create_request())

    assert result.employee_id == 100
    assert result.employee_code == "EMP001"
    assert result.first_name == "John"
    assert result.last_name == "Doe"
    assert result.user_id == 1
    assert result.department_id == 10
    assert result.designation_id == 20
    assert result.employment_status == "ACTIVE"

    uow.employees.add.assert_called_once()
    uow.commit.assert_called_once()


def test_create_employee_without_user():
    uow = create_uow()
    configure_valid_dependencies(uow)

    def add_employee(employee):
        employee.employee_id = 101
        return employee

    uow.employees.add.side_effect = add_employee

    service = EmployeeService(uow)

    result = service.create(
        create_request(user_id=None)
    )

    assert result.employee_id == 101
    assert result.user_id is None
    uow.users.get_by_id.assert_not_called()


def test_create_employee_rejects_duplicate_employee_code():
    uow = create_uow()
    configure_valid_dependencies(uow)

    uow.employees.get_by_code.return_value = SimpleNamespace(
        employee_id=50,
        employee_code="EMP001",
    )

    service = EmployeeService(uow)

    with pytest.raises(BusinessRuleViolation, match="Employee code already exists"):
        service.create(create_request())

    uow.employees.add.assert_not_called()
    uow.commit.assert_not_called()


def test_create_employee_rejects_nonexistent_user():
    uow = create_uow()
    configure_valid_dependencies(uow)

    uow.users.get_by_id.return_value = None

    service = EmployeeService(uow)

    with pytest.raises(BusinessRuleViolation, match="User does not exist"):
        service.create(create_request())

    uow.employees.add.assert_not_called()
    uow.commit.assert_not_called()


def test_create_employee_rejects_user_already_assigned():
    uow = create_uow()
    configure_valid_dependencies(uow)

    uow.employees.get_by_user_id.return_value = SimpleNamespace(
        employee_id=50,
        user_id=1,
    )

    service = EmployeeService(uow)

    with pytest.raises(
        BusinessRuleViolation,
        match="User is already assigned to an employee",
    ):
        service.create(create_request())

    uow.employees.add.assert_not_called()
    uow.commit.assert_not_called()


def test_create_employee_rejects_nonexistent_department():
    uow = create_uow()
    configure_valid_dependencies(uow)

    uow.departments.get_by_id.return_value = None

    service = EmployeeService(uow)

    with pytest.raises(
        BusinessRuleViolation,
        match="Department does not exist",
    ):
        service.create(create_request())

    uow.employees.add.assert_not_called()
    uow.commit.assert_not_called()


def test_create_employee_rejects_nonexistent_designation():
    uow = create_uow()
    configure_valid_dependencies(uow)

    uow.designations.get_by_id.return_value = None

    service = EmployeeService(uow)

    with pytest.raises(
        BusinessRuleViolation,
        match="Designation does not exist",
    ):
        service.create(create_request())

    uow.employees.add.assert_not_called()
    uow.commit.assert_not_called()


def test_create_employee_rejects_nonexistent_manager():
    uow = create_uow()
    configure_valid_dependencies(uow)

    uow.employees.get_by_id.return_value = None

    service = EmployeeService(uow)

    with pytest.raises(
        BusinessRuleViolation,
        match="Manager employee does not exist",
    ):
        service.create(
            create_request(manager_employee_id=25)
        )

    uow.employees.add.assert_not_called()
    uow.commit.assert_not_called()


def test_create_employee_rejects_terminated_manager():
    uow = create_uow()
    configure_valid_dependencies(uow)

    uow.employees.get_by_id.return_value = SimpleNamespace(
        employee_id=25,
        employment_status="TERMINATED",
    )

    service = EmployeeService(uow)

    with pytest.raises(
        BusinessRuleViolation,
        match="terminated employee cannot be assigned as a manager",
    ):
        service.create(
            create_request(manager_employee_id=25)
        )

    uow.employees.add.assert_not_called()
    uow.commit.assert_not_called()


def test_create_employee_accepts_active_manager():
    uow = create_uow()
    configure_valid_dependencies(uow)

    uow.employees.get_by_id.return_value = SimpleNamespace(
        employee_id=25,
        employment_status="ACTIVE",
    )

    def add_employee(employee):
        employee.employee_id = 102
        return employee

    uow.employees.add.side_effect = add_employee

    service = EmployeeService(uow)

    result = service.create(
        create_request(manager_employee_id=25)
    )

    assert result.employee_id == 102
    assert result.manager_employee_id == 25
    uow.commit.assert_called_once()