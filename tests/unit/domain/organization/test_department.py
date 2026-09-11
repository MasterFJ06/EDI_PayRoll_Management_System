import pytest

from app.domain.organization.department import Department
from app.domain.shared.exceptions import BusinessRuleViolation


def test_department_can_be_created() -> None:
    department = Department(
        department_id=None,
        department_code=" IT ",
        department_name=" Information Technology ",
    )

    assert department.id is None
    assert department.department_code == "IT"
    assert department.department_name == "Information Technology"
    assert department.status == Department.ACTIVE


def test_department_normalizes_status() -> None:
    department = Department(
        department_id=None,
        department_code="IT",
        department_name="Information Technology",
        status=" inactive ",
    )

    assert department.status == Department.INACTIVE


def test_department_rejects_blank_code() -> None:
    with pytest.raises(BusinessRuleViolation):
        Department(
            department_id=None,
            department_code="   ",
            department_name="Information Technology",
        )


def test_department_rejects_blank_name() -> None:
    with pytest.raises(BusinessRuleViolation):
        Department(
            department_id=None,
            department_code="IT",
            department_name="   ",
        )


def test_department_rejects_invalid_status() -> None:
    with pytest.raises(BusinessRuleViolation):
        Department(
            department_id=None,
            department_code="IT",
            department_name="Information Technology",
            status="DELETED",
        )


def test_department_can_be_deactivated() -> None:
    department = Department(
        department_id=1,
        department_code="IT",
        department_name="Information Technology",
    )

    department.deactivate()

    assert department.status == Department.INACTIVE


def test_department_can_be_activated() -> None:
    department = Department(
        department_id=1,
        department_code="IT",
        department_name="Information Technology",
        status=Department.INACTIVE,
    )

    department.activate()

    assert department.status == Department.ACTIVE


def test_department_can_be_renamed() -> None:
    department = Department(
        department_id=1,
        department_code="IT",
        department_name="Information Technology",
    )

    department.rename("Engineering")

    assert department.department_name == "Engineering"


def test_department_can_change_code() -> None:
    department = Department(
        department_id=1,
        department_code="IT",
        department_name="Information Technology",
    )

    department.change_code("ENG")

    assert department.department_code == "ENG"


def test_department_rejects_blank_rename() -> None:
    department = Department(
        department_id=1,
        department_code="IT",
        department_name="Information Technology",
    )

    with pytest.raises(BusinessRuleViolation):
        department.rename("   ")


def test_department_rejects_blank_code_change() -> None:
    department = Department(
        department_id=1,
        department_code="IT",
        department_name="Information Technology",
    )

    with pytest.raises(BusinessRuleViolation):
        department.change_code("   ")