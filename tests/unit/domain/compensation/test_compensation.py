from datetime import date
from decimal import Decimal

import pytest

from app.domain.compensation.employee_salary_assignment import EmployeeSalaryAssignment
from app.domain.compensation.salary_component import SalaryComponent
from app.domain.compensation.salary_revision import SalaryRevision
from app.domain.compensation.salary_revision_component import SalaryRevisionComponent
from app.domain.compensation.salary_structure import SalaryStructure
from app.domain.shared.exceptions import BusinessRuleViolation


def test_salary_structure_construction_and_status_behavior() -> None:
    structure = SalaryStructure(None, " BASE ", " Base Plan ", " Annual ")

    assert structure.structure_code == "BASE"
    assert structure.structure_name == "Base Plan"
    assert structure.description == "Annual"
    assert structure.status == "ACTIVE"
    structure.deactivate()
    assert structure.status == "INACTIVE"
    structure.activate()
    assert structure.status == "ACTIVE"


@pytest.mark.parametrize(
    "values",
    [
        {"structure_code": " "},
        {"structure_code": "x" * 31},
        {"structure_name": " "},
        {"structure_name": "x" * 101},
        {"description": "x" * 501},
        {"status": "SUSPENDED"},
    ],
)
def test_salary_structure_rejects_invalid_values(values: dict[str, str]) -> None:
    args: dict[str, object] = {
        "salary_structure_id": None,
        "structure_code": "BASE",
        "structure_name": "Base Plan",
        "description": None,
        "status": "ACTIVE",
    }
    args.update(values)
    with pytest.raises(BusinessRuleViolation):
        SalaryStructure(**args)


def test_salary_component_construction_and_status_behavior() -> None:
    component = SalaryComponent(None, " BASIC ", " Basic Pay ", "earning")

    assert component.component_code == "BASIC"
    assert component.component_name == "Basic Pay"
    assert component.component_type == "EARNING"
    component.deactivate()
    assert component.status == "INACTIVE"


@pytest.mark.parametrize(
    "values",
    [
        {"component_code": " "},
        {"component_name": " "},
        {"component_type": "BONUS"},
        {"status": "DISABLED"},
    ],
)
def test_salary_component_rejects_invalid_values(values: dict[str, str]) -> None:
    args: dict[str, object] = {
        "salary_component_id": None,
        "component_code": "BASIC",
        "component_name": "Basic Pay",
        "component_type": "EARNING",
        "status": "ACTIVE",
    }
    args.update(values)
    with pytest.raises(BusinessRuleViolation):
        SalaryComponent(**args)


def test_salary_revision_allows_schema_valid_zero_revision_number() -> None:
    revision = SalaryRevision(None, 1, 0, date(2026, 1, 1))

    assert revision.revision_number == 0
    assert revision.effective_to is None


@pytest.mark.parametrize(
    ("structure_id", "revision_number", "effective_to"),
    [
        (0, 1, None),
        (1, -1, None),
        (1, 4_294_967_296, None),
        (1, 1, date(2025, 12, 31)),
    ],
)
def test_salary_revision_rejects_invalid_values(
    structure_id: int, revision_number: int, effective_to: date | None
) -> None:
    with pytest.raises(BusinessRuleViolation):
        SalaryRevision(
            None, structure_id, revision_number, date(2026, 1, 1), effective_to
        )


def test_salary_revision_component_accepts_fixed_and_percentage_forms() -> None:
    fixed = SalaryRevisionComponent(1, 2, "fixed", fixed_amount=Decimal("100.00"))
    percentage = SalaryRevisionComponent(
        1,
        3,
        "PERCENTAGE",
        percentage_value=Decimal("10.0000"),
        base_component_id=2,
    )

    assert fixed.id == (1, 2)
    assert fixed.fixed_amount == Decimal("100.00")
    assert percentage.percentage_value == Decimal("10.0000")


@pytest.mark.parametrize(
    "values",
    [
        {"calculation_type": "OTHER"},
        {"calculation_type": "FIXED"},
        {"calculation_type": "FIXED", "fixed_amount": Decimal("-1")},
        {"calculation_type": "FIXED", "fixed_amount": Decimal("1"), "percentage_value": Decimal("2")},
        {"calculation_type": "PERCENTAGE", "percentage_value": Decimal("1")},
        {"calculation_type": "PERCENTAGE", "percentage_value": Decimal("-1"), "base_component_id": 2},
        {"calculation_type": "PERCENTAGE", "percentage_value": Decimal("1"), "base_component_id": 3},
    ],
)
def test_salary_revision_component_rejects_invalid_calculation_shape(
    values: dict[str, object],
) -> None:
    with pytest.raises(BusinessRuleViolation):
        SalaryRevisionComponent(1, 3, **values)


def test_employee_salary_assignment_construction() -> None:
    assignment = EmployeeSalaryAssignment(None, 5, 2, date(2026, 1, 1), date(2026, 12, 31))

    assert assignment.employee_id == 5
    assert assignment.salary_revision_id == 2
    assert assignment.effective_to == date(2026, 12, 31)


@pytest.mark.parametrize(
    ("employee_id", "revision_id", "effective_to"),
    [(0, 1, None), (1, 0, None), (1, 2, date(2025, 12, 31))],
)
def test_employee_salary_assignment_rejects_invalid_values(
    employee_id: int, revision_id: int, effective_to: date | None
) -> None:
    with pytest.raises(BusinessRuleViolation):
        EmployeeSalaryAssignment(
            None, employee_id, revision_id, date(2026, 1, 1), effective_to
        )
