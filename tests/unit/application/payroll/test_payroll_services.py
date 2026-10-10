from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.application.payroll.payroll_processing_issue_service import (
    PayrollProcessingIssueService,
)
from app.application.payroll.payroll_result_component_service import (
    PayrollResultComponentService,
)
from app.application.payroll.payroll_result_service import PayrollResultService
from app.application.payroll.payroll_run_service import PayrollRunService
from app.application.payroll.payslip_service import PayslipService
from app.application.payroll.payslip_service import _is_payslip_unique_conflict
from app.application.payroll.schemas import (
    PayrollProcessingIssueCreateRequest,
    PayrollResultComponentCreateRequest,
    PayrollResultCreateRequest,
    PayrollRunCreateRequest,
    PayslipCreateRequest,
)
from app.domain.shared.exceptions import BusinessRuleViolation
from sqlalchemy.exc import IntegrityError


def _uow() -> SimpleNamespace:
    repository_names = (
        "users",
        "employees",
        "employee_salary_assignments",
        "salary_components",
        "payroll_runs",
        "payroll_results",
        "payroll_result_components",
        "payroll_processing_issues",
        "payslips",
        "audit_events",
    )
    repos = {name: MagicMock() for name in repository_names}
    repos["payroll_runs"].lock_active_attempt.return_value = object()
    repos["payroll_runs"].lock_for_finalization.return_value = SimpleNamespace(
        payroll_run_id=1, status="FINALIZED"
    )
    for repo in repos.values():
        repo.get_by_id.return_value = object()
        repo.get_by_period.return_value = None
        repo.get_by_run_and_employee.return_value = None
        repo.get_by_result_and_component.return_value = None
        repo.get_by_result_id.return_value = None
        repo.get_by_number.return_value = None
        def add_model(model):
            setattr(model, {
                "PayrollRunModel": "payroll_run_id",
                "PayrollResultModel": "payroll_result_id",
                "PayrollResultComponentModel": "payroll_result_component_id",
                "PayrollProcessingIssueModel": "payroll_issue_id",
                "PayslipModel": "payslip_id",
            }[type(model).__name__], 9)
            if type(model).__name__ == "PayslipModel":
                model.generated_at = datetime(2026, 10, 10, 12, 0, 0)
            return model

        repo.add.side_effect = add_model
    repos["audit_events"].add.side_effect = None
    result = SimpleNamespace(payroll_result_id=1, payroll_run_id=1)
    repos["payroll_results"].get_by_id.return_value = result
    repos["payroll_results"].get_by_id_for_update.return_value = result
    return SimpleNamespace(**repos, commit=MagicMock(), rollback=MagicMock())


def test_create_payroll_run_defaults_to_schema_created_status_and_commits() -> None:
    uow = _uow()
    response = PayrollRunService(uow).create(
        PayrollRunCreateRequest(
            payroll_year=2026, payroll_month=10, initiated_by_user_id=3
        )
    )
    assert response.payroll_run_id == 9
    assert response.status == "CREATED"
    uow.payroll_runs.add.assert_called_once()
    uow.commit.assert_called_once()


def test_create_payroll_run_rejects_missing_user_and_duplicate_period() -> None:
    uow = _uow()
    uow.users.get_by_id.return_value = None
    with pytest.raises(BusinessRuleViolation, match="user does not exist"):
        PayrollRunService(uow).create(
            PayrollRunCreateRequest(payroll_year=2026, payroll_month=10, initiated_by_user_id=3)
        )
    uow.users.get_by_id.return_value = object()
    uow.payroll_runs.get_by_period.return_value = object()
    with pytest.raises(BusinessRuleViolation, match="already exists"):
        PayrollRunService(uow).create(
            PayrollRunCreateRequest(payroll_year=2026, payroll_month=10, initiated_by_user_id=3)
        )
    uow.commit.assert_not_called()


def test_create_payroll_result_persists_supplied_amounts_without_formula() -> None:
    uow = _uow()
    response = PayrollResultService(uow).create(
        PayrollResultCreateRequest(
            payroll_run_id=1,
            employee_id=2,
            salary_assignment_id=3,
            gross_earnings=Decimal("120.00"),
            total_deductions=Decimal("20.00"),
            net_salary=Decimal("100.00"),
        ),
        attempt_number=1,
    )
    model = uow.payroll_results.add.call_args.args[0]
    assert response.payroll_result_id == 9
    assert model.net_salary == Decimal("100.00")
    uow.commit.assert_called_once()


def test_create_payroll_result_checks_references_and_unique_employee_per_run() -> None:
    uow = _uow()
    request = PayrollResultCreateRequest(
        payroll_run_id=1, employee_id=2, salary_assignment_id=3,
        gross_earnings=Decimal("10"), total_deductions=Decimal("0"), net_salary=Decimal("10"),
    )
    uow.payroll_runs.get_by_id.return_value = None
    with pytest.raises(BusinessRuleViolation, match="Payroll run"):
        PayrollResultService(uow).create(request, attempt_number=1)
    uow.payroll_runs.get_by_id.return_value = object()
    uow.employees.get_by_id.return_value = None
    with pytest.raises(BusinessRuleViolation, match="Employee"):
        PayrollResultService(uow).create(request, attempt_number=1)
    uow.employees.get_by_id.return_value = object()
    uow.employee_salary_assignments.get_by_id.return_value = None
    with pytest.raises(BusinessRuleViolation, match="assignment does not exist"):
        PayrollResultService(uow).create(request, attempt_number=1)
    uow.employee_salary_assignments.get_by_id.return_value = object()
    uow.payroll_results.get_by_run_and_employee.return_value = object()
    with pytest.raises(BusinessRuleViolation, match="already exists"):
        PayrollResultService(uow).create(request, attempt_number=1)
    uow.commit.assert_not_called()


def test_create_result_component_checks_definition_and_duplicate_key() -> None:
    uow = _uow()
    request = PayrollResultComponentCreateRequest(
        payroll_result_id=1,
        salary_component_id=2,
        component_type="EARNING",
        amount=Decimal("12.50"),
        calculation_order=0,
    )
    response = PayrollResultComponentService(uow).create(request, attempt_number=1)
    assert response.payroll_result_component_id == 9
    assert response.component_type == "EARNING"
    uow.commit.assert_called_once()

    uow = _uow()
    uow.salary_components.get_by_id.return_value = None
    with pytest.raises(BusinessRuleViolation, match="Salary component"):
        PayrollResultComponentService(uow).create(request, attempt_number=1)
    uow.commit.assert_not_called()

    uow = _uow()
    uow.payroll_result_components.get_by_result_and_component.return_value = object()
    with pytest.raises(BusinessRuleViolation, match="already recorded"):
        PayrollResultComponentService(uow).create(request, attempt_number=1)


def test_create_processing_issue_validates_references_and_schema_state() -> None:
    uow = _uow()
    response = PayrollProcessingIssueService(uow).create(
        PayrollProcessingIssueCreateRequest(
            payroll_run_id=1, employee_id=None, issue_code="QA", issue_message="Detected"
        ),
        attempt_number=1,
    )
    assert response.payroll_issue_id == 9
    assert response.status == "OPEN"
    uow.commit.assert_called_once()

    missing_run_uow = _uow()
    missing_run_uow.payroll_runs.get_by_id.return_value = None
    with pytest.raises(BusinessRuleViolation, match="Payroll run"):
        PayrollProcessingIssueService(missing_run_uow).create(
            PayrollProcessingIssueCreateRequest(
                payroll_run_id=1, issue_code="QA", issue_message="Detected"
            ),
            attempt_number=1,
        )
    missing_employee_uow = _uow()
    missing_employee_uow.employees.get_by_id.return_value = None
    with pytest.raises(BusinessRuleViolation, match="Employee"):
        PayrollProcessingIssueService(missing_employee_uow).create(
            PayrollProcessingIssueCreateRequest(
                payroll_run_id=1, employee_id=2, issue_code="QA", issue_message="Detected"
            ),
            attempt_number=1,
        )

    resolved_response = PayrollProcessingIssueService(_uow()).create(
        PayrollProcessingIssueCreateRequest(
            payroll_run_id=1,
            issue_code="QA",
            issue_message="Resolved during creation",
            status="RESOLVED",
            resolved_at=datetime(2026, 1, 1),
        ),
        attempt_number=1,
    )
    assert resolved_response.status == "RESOLVED"

    with pytest.raises(BusinessRuleViolation, match="resolution time"):
        PayrollProcessingIssueService(_uow()).create(
            PayrollProcessingIssueCreateRequest(
                payroll_run_id=1,
                issue_code="QA",
                issue_message="Detected",
                status="RESOLVED",
                resolved_at=None,
            ),
            attempt_number=1,
        )


def test_generate_payslip_uses_finalized_result_and_authenticated_actor() -> None:
    uow = _uow()
    response = PayslipService(uow).generate(
        PayslipCreateRequest(
            payroll_run_id=1,
            payroll_result_id=1,
            payslip_number="PS-1",
        ),
        actor_user_id=2,
        correlation_id="request-1",
    )
    assert response.payslip_id == 9
    assert response.generated_by_user_id == 2
    assert response.document_path is None
    assert response.generated_at is not None
    model = uow.payslips.add.call_args.args[0]
    assert model.document_path is None
    event, changes = uow.audit_events.add.call_args.args
    assert event.action_type == "PAYSLIP_GENERATED"
    assert event.actor_user_id == 2
    assert event.correlation_id == "request-1"
    assert {change.field_name for change in changes} == {
        "payroll_run_id", "payroll_result_id"
    }
    assert all("amount" not in change.field_name for change in changes)
    uow.commit.assert_called_once()


@pytest.mark.parametrize("constraint", ["uq_payslip_result", "uq_payslip_number"])
def test_payslip_duplicate_classifier_is_limited_to_unique_constraints(
    constraint: str,
) -> None:
    duplicate = IntegrityError("INSERT", {}, Exception(f"Duplicate entry for key '{constraint}'"))
    unrelated = IntegrityError("INSERT", {}, Exception("foreign key constraint fails"))
    assert _is_payslip_unique_conflict(duplicate)
    assert not _is_payslip_unique_conflict(unrelated)

    uow = _uow()
    uow.payroll_results.get_by_id.return_value = None
    response = PayslipService(uow).generate(
        PayslipCreateRequest(
            payroll_run_id=1, payroll_result_id=1, payslip_number="PS-1"
        ),
        actor_user_id=2,
        correlation_id=None,
    )
    assert response is None
    uow.payslips.add.assert_not_called()

    uow = _uow()
    uow.payroll_runs.lock_for_finalization.return_value.status = "PROCESSED"
    with pytest.raises(BusinessRuleViolation, match="FINALIZED"):
        PayslipService(uow).generate(
            PayslipCreateRequest(
                payroll_run_id=1, payroll_result_id=1, payslip_number="PS-1"
            ), actor_user_id=2, correlation_id=None
        )

    uow = _uow()
    uow.payroll_results.get_by_id.return_value.payroll_run_id = 99
    assert PayslipService(uow).generate(
        PayslipCreateRequest(
            payroll_run_id=1, payroll_result_id=1, payslip_number="PS-1"
        ), actor_user_id=2, correlation_id=None
    ) is None

    uow = _uow()
    uow.payslips.get_by_result_id.return_value = object()
    with pytest.raises(BusinessRuleViolation, match="already exists"):
        PayslipService(uow).generate(
            PayslipCreateRequest(
                payroll_run_id=1, payroll_result_id=1, payslip_number="PS-1"
            ), actor_user_id=2, correlation_id=None
        )

    uow = _uow()
    uow.payslips.get_by_number.return_value = object()
    with pytest.raises(BusinessRuleViolation, match="number already exists"):
        PayslipService(uow).generate(
            PayslipCreateRequest(
                payroll_run_id=1, payroll_result_id=1, payslip_number="PS-1"
            ), actor_user_id=2, correlation_id=None
        )


def test_create_processing_issue_rejects_inactive_attempt() -> None:
    uow = _uow()
    uow.payroll_runs.lock_active_attempt.return_value = None
    with pytest.raises(BusinessRuleViolation, match="attempt is no longer active"):
        PayrollProcessingIssueService(uow).create(
            PayrollProcessingIssueCreateRequest(
                payroll_run_id=1, issue_code="QA", issue_message="Detected"
            ),
            attempt_number=1,
        )
    uow.payroll_processing_issues.add.assert_not_called()
    uow.commit.assert_not_called()
