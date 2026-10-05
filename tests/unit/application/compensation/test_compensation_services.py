from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from app.application.compensation.employee_salary_assignment_service import (
    EmployeeSalaryAssignmentService,
)
from app.application.compensation.salary_component_service import SalaryComponentService
from app.application.compensation.salary_revision_component_service import (
    SalaryRevisionComponentService,
)
from app.application.compensation.salary_revision_service import SalaryRevisionService
from app.application.compensation.salary_structure_service import SalaryStructureService
from app.application.compensation.schemas import (
    EmployeeSalaryAssignmentCreateRequest,
    SalaryComponentCreateRequest,
    SalaryRevisionComponentCreateRequest,
    SalaryRevisionCreateRequest,
    SalaryStructureCreateRequest,
)
from app.domain.shared.exceptions import BusinessRuleViolation


def make_uow() -> MagicMock:
    uow = MagicMock()
    uow.salary_structures.get_by_id.return_value = object()
    uow.salary_structures.get_by_code.return_value = None
    uow.salary_components.get_by_id.return_value = object()
    uow.salary_components.get_by_code.return_value = None
    uow.salary_revisions.get_by_id.return_value = object()
    uow.salary_revisions.get_by_structure_and_number.return_value = None
    uow.salary_revision_components.get_by_revision_and_component.return_value = None
    uow.employees.get_by_id.return_value = object()
    uow.salary_structures.add.side_effect = lambda model: setattr(model, "salary_structure_id", 1)
    uow.salary_components.add.side_effect = lambda model: setattr(model, "salary_component_id", 2)
    uow.salary_revisions.add.side_effect = lambda model: setattr(model, "salary_revision_id", 3)
    uow.employee_salary_assignments.add.side_effect = lambda model: setattr(model, "salary_assignment_id", 5)
    return uow


@pytest.mark.parametrize(
    ("request_type", "required_fields"),
    [
        (SalaryStructureCreateRequest, {"structure_code", "structure_name"}),
        (
            SalaryComponentCreateRequest,
            {"component_code", "component_name", "component_type"},
        ),
        (
            SalaryRevisionCreateRequest,
            {"salary_structure_id", "revision_number", "effective_from"},
        ),
        (
            SalaryRevisionComponentCreateRequest,
            {"salary_revision_id", "salary_component_id", "calculation_type"},
        ),
        (
            EmployeeSalaryAssignmentCreateRequest,
            {"employee_id", "salary_revision_id", "effective_from"},
        ),
    ],
)
def test_compensation_create_schemas_require_mandatory_fields(
    request_type: type,
    required_fields: set[str],
) -> None:
    with pytest.raises(ValidationError) as error:
        request_type()

    missing_fields = {entry["loc"][0] for entry in error.value.errors()}
    assert required_fields <= missing_fields


def test_create_salary_structure_commits() -> None:
    uow = make_uow()
    result = SalaryStructureService(uow).create(
        SalaryStructureCreateRequest(structure_code="BASE", structure_name="Base Plan")
    )

    assert result.salary_structure_id == 1
    assert result.status == "ACTIVE"
    uow.salary_structures.add.assert_called_once()
    uow.commit.assert_called_once()


def test_create_salary_structure_rejects_duplicate_code_without_commit() -> None:
    uow = make_uow()
    uow.salary_structures.get_by_code.return_value = object()

    with pytest.raises(BusinessRuleViolation, match="code is already registered"):
        SalaryStructureService(uow).create(
            SalaryStructureCreateRequest(structure_code="BASE", structure_name="Base Plan")
        )

    uow.salary_structures.add.assert_not_called()
    uow.commit.assert_not_called()


def test_create_salary_component_commits() -> None:
    uow = make_uow()
    result = SalaryComponentService(uow).create(
        SalaryComponentCreateRequest(
            component_code="BASIC", component_name="Basic Pay", component_type="EARNING"
        )
    )

    assert result.salary_component_id == 2
    assert result.component_type == "EARNING"
    uow.salary_components.add.assert_called_once()
    uow.commit.assert_called_once()


def test_create_salary_component_rejects_duplicate_code_without_commit() -> None:
    uow = make_uow()
    uow.salary_components.get_by_code.return_value = object()

    with pytest.raises(BusinessRuleViolation, match="code is already registered"):
        SalaryComponentService(uow).create(
            SalaryComponentCreateRequest(
                component_code="BASIC", component_name="Basic Pay", component_type="EARNING"
            )
        )

    uow.salary_components.add.assert_not_called()
    uow.commit.assert_not_called()


def test_create_salary_revision_commits() -> None:
    uow = make_uow()
    result = SalaryRevisionService(uow).create(
        SalaryRevisionCreateRequest(
            salary_structure_id=1,
            revision_number=1,
            effective_from=date(2026, 1, 1),
        )
    )

    assert result.salary_revision_id == 3
    uow.salary_revisions.add.assert_called_once()
    uow.commit.assert_called_once()


@pytest.mark.parametrize("failure", ["missing_structure", "duplicate_revision"])
def test_create_salary_revision_rejects_failures_without_commit(failure: str) -> None:
    uow = make_uow()
    if failure == "missing_structure":
        uow.salary_structures.get_by_id.return_value = None
    else:
        uow.salary_revisions.get_by_structure_and_number.return_value = object()

    with pytest.raises(BusinessRuleViolation):
        SalaryRevisionService(uow).create(
            SalaryRevisionCreateRequest(
                salary_structure_id=1,
                revision_number=1,
                effective_from=date(2026, 1, 1),
            )
        )

    uow.salary_revisions.add.assert_not_called()
    uow.commit.assert_not_called()


def test_create_fixed_salary_revision_component_commits() -> None:
    uow = make_uow()
    result = SalaryRevisionComponentService(uow).create(
        SalaryRevisionComponentCreateRequest(
            salary_revision_id=3,
            salary_component_id=2,
            calculation_type="FIXED",
            fixed_amount=Decimal("5000.00"),
        )
    )

    assert result.salary_revision_id == 3
    assert result.fixed_amount == Decimal("5000.00")
    uow.salary_revision_components.add.assert_called_once()
    uow.commit.assert_called_once()


def test_create_percentage_salary_revision_component_validates_base_component() -> None:
    uow = make_uow()
    result = SalaryRevisionComponentService(uow).create(
        SalaryRevisionComponentCreateRequest(
            salary_revision_id=3,
            salary_component_id=2,
            calculation_type="PERCENTAGE",
            percentage_value=Decimal("10.0000"),
            base_component_id=4,
        )
    )

    assert result.percentage_value == Decimal("10.0000")
    uow.salary_components.get_by_id.assert_any_call(4)
    uow.commit.assert_called_once()


@pytest.mark.parametrize(
    "failure",
    ["missing_revision", "missing_component", "missing_base", "duplicate", "invalid_shape"],
)
def test_create_salary_revision_component_rejects_failures_without_commit(
    failure: str,
) -> None:
    uow = make_uow()
    values: dict[str, object] = {
        "salary_revision_id": 3,
        "salary_component_id": 2,
        "calculation_type": "FIXED",
        "fixed_amount": Decimal("500.00"),
    }
    if failure == "missing_revision":
        uow.salary_revisions.get_by_id.return_value = None
    elif failure == "missing_component":
        uow.salary_components.get_by_id.return_value = None
    elif failure == "missing_base":
        values = {
            "salary_revision_id": 3,
            "salary_component_id": 2,
            "calculation_type": "PERCENTAGE",
            "percentage_value": Decimal("10.0000"),
            "base_component_id": 4,
        }
        uow.salary_components.get_by_id.side_effect = [object(), None]
    elif failure == "duplicate":
        uow.salary_revision_components.get_by_revision_and_component.return_value = object()
    else:
        values = {
            "salary_revision_id": 3,
            "salary_component_id": 2,
            "calculation_type": "FIXED",
            "percentage_value": Decimal("10.0000"),
        }

    with pytest.raises(BusinessRuleViolation):
        SalaryRevisionComponentService(uow).create(
            SalaryRevisionComponentCreateRequest(**values)
        )

    uow.salary_revision_components.add.assert_not_called()
    uow.commit.assert_not_called()


def test_create_employee_salary_assignment_commits() -> None:
    uow = make_uow()
    result = EmployeeSalaryAssignmentService(uow).create(
        EmployeeSalaryAssignmentCreateRequest(
            employee_id=5,
            salary_revision_id=3,
            effective_from=date(2026, 1, 1),
        )
    )

    assert result.salary_assignment_id == 5
    uow.employees.get_by_id.assert_called_once_with(5)
    uow.employee_salary_assignments.add.assert_called_once()
    uow.commit.assert_called_once()


@pytest.mark.parametrize("missing", ["employee", "revision"])
def test_create_employee_salary_assignment_rejects_missing_reference_without_commit(
    missing: str,
) -> None:
    uow = make_uow()
    if missing == "employee":
        uow.employees.get_by_id.return_value = None
    else:
        uow.salary_revisions.get_by_id.return_value = None

    with pytest.raises(BusinessRuleViolation):
        EmployeeSalaryAssignmentService(uow).create(
            EmployeeSalaryAssignmentCreateRequest(
                employee_id=5,
                salary_revision_id=3,
                effective_from=date(2026, 1, 1),
            )
        )

    uow.employee_salary_assignments.add.assert_not_called()
    uow.commit.assert_not_called()


def test_create_employee_salary_assignment_rejects_reversed_dates_without_commit() -> None:
    uow = make_uow()
    with pytest.raises(BusinessRuleViolation, match="end date cannot precede"):
        EmployeeSalaryAssignmentService(uow).create(
            EmployeeSalaryAssignmentCreateRequest(
                employee_id=5,
                salary_revision_id=3,
                effective_from=date(2026, 1, 1),
                effective_to=date(2025, 12, 31),
            )
        )
    uow.commit.assert_not_called()
