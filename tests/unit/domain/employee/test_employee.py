from datetime import date

import pytest

from app.domain.employee.employee import Employee
from app.domain.shared.exceptions import BusinessRuleViolation


def create_employee(**overrides) -> Employee:
    data = {
        "employee_id": 1,
        "employee_code": "EMP001",
        "first_name": "John",
        "last_name": "Doe",
        "department_id": 10,
        "designation_id": 20,
        "joining_date": date(2026, 1, 1),
    }
    data.update(overrides)
    return Employee(**data)


def test_employee_can_be_created():
    employee = create_employee()

    assert employee.id == 1
    assert employee.employee_code == "EMP001"
    assert employee.first_name == "John"
    assert employee.last_name == "Doe"
    assert employee.department_id == 10
    assert employee.designation_id == 20
    assert employee.joining_date == date(2026, 1, 1)
    assert employee.employment_status == Employee.ACTIVE


def test_employee_normalizes_text_fields():
    employee = create_employee(
        employee_code=" EMP001 ",
        first_name=" John ",
        last_name=" Doe ",
        employment_status=" inactive ",
    )

    assert employee.employee_code == "EMP001"
    assert employee.first_name == "John"
    assert employee.last_name == "Doe"
    assert employee.employment_status == Employee.INACTIVE


@pytest.mark.parametrize(
    "field,value",
    [
        ("employee_code", ""),
        ("employee_code", "   "),
        ("first_name", ""),
        ("first_name", "   "),
        ("last_name", ""),
        ("last_name", "   "),
    ],
)
def test_employee_rejects_blank_required_text(field, value):
    with pytest.raises(BusinessRuleViolation):
        create_employee(**{field: value})


@pytest.mark.parametrize(
    "status",
    ["", "UNKNOWN", "ACTIVE_INVALID", "TERMINATEDX"],
)
def test_employee_rejects_invalid_status(status):
    with pytest.raises(BusinessRuleViolation):
        create_employee(employment_status=status)


@pytest.mark.parametrize(
    "field",
    ["department_id", "designation_id"],
)
def test_employee_rejects_non_positive_organization_ids(field):
    with pytest.raises(BusinessRuleViolation):
        create_employee(**{field: 0})


def test_employee_cannot_be_own_manager():
    with pytest.raises(BusinessRuleViolation):
        create_employee(manager_employee_id=1)


def test_employee_can_have_no_manager():
    employee = create_employee(manager_employee_id=None)

    assert employee.manager_employee_id is None


def test_employee_can_assign_manager():
    employee = create_employee()

    employee.assign_manager(5)

    assert employee.manager_employee_id == 5


def test_employee_can_remove_manager():
    employee = create_employee(manager_employee_id=5)

    employee.assign_manager(None)

    assert employee.manager_employee_id is None


def test_employee_cannot_assign_self_as_manager():
    employee = create_employee()

    with pytest.raises(BusinessRuleViolation):
        employee.assign_manager(1)


def test_employee_can_activate():
    employee = create_employee(employment_status=Employee.INACTIVE)

    employee.activate()

    assert employee.employment_status == Employee.ACTIVE


def test_employee_can_deactivate():
    employee = create_employee()

    employee.deactivate()

    assert employee.employment_status == Employee.INACTIVE


def test_employee_can_terminate():
    employee = create_employee()

    employee.terminate()

    assert employee.employment_status == Employee.TERMINATED


def test_employee_can_change_department():
    employee = create_employee()

    employee.change_department(30)

    assert employee.department_id == 30


def test_employee_can_change_designation():
    employee = create_employee()

    employee.change_designation(40)

    assert employee.designation_id == 40


@pytest.mark.parametrize(
    "method",
    ["change_department", "change_designation"],
)
def test_employee_rejects_non_positive_new_organization_ids(method):
    employee = create_employee()

    with pytest.raises(BusinessRuleViolation):
        getattr(employee, method)(0)