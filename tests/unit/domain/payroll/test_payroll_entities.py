from datetime import datetime
from decimal import Decimal

import pytest

from app.domain.payroll.payroll_processing_issue import PayrollProcessingIssue
from app.domain.payroll.payroll_result import PayrollResult
from app.domain.payroll.payroll_result_component import PayrollResultComponent
from app.domain.payroll.payroll_run import PayrollRun
from app.domain.payroll.payslip import Payslip
from app.domain.shared.exceptions import BusinessRuleViolation


def test_payroll_run_accepts_schema_status_values_and_period() -> None:
    run = PayrollRun(None, 65535, 12, 1, status="created")
    assert run.status == PayrollRun.CREATED
    assert run.payroll_year == 65535


@pytest.mark.parametrize(
    "kwargs",
    [
        {"payroll_year": -1},
        {"payroll_year": 65536},
        {"payroll_month": 0},
        {"payroll_month": 13},
        {"initiated_by_user_id": 0},
        {"status": "DRAFT"},
    ],
)
def test_payroll_run_rejects_values_outside_schema(kwargs: dict[str, object]) -> None:
    values: dict[str, object] = {
        "payroll_year": 2026,
        "payroll_month": 1,
        "initiated_by_user_id": 1,
    }
    values.update(kwargs)
    with pytest.raises(BusinessRuleViolation):
        PayrollRun(None, **values)  # type: ignore[arg-type]


def test_payroll_result_enforces_schema_amount_constraints_without_calculating() -> None:
    result = PayrollResult(
        None, 1, 2, 3, Decimal("100.00"), Decimal("20.00"), Decimal("80.00")
    )
    assert result.net_salary == Decimal("80.00")

    with pytest.raises(BusinessRuleViolation, match="Net salary"):
        PayrollResult(None, 1, 2, 3, Decimal("100.00"), Decimal("20.00"), Decimal("79.00"))
    with pytest.raises(BusinessRuleViolation, match="cannot be negative"):
        PayrollResult(None, 1, 2, 3, Decimal("-1"), Decimal("0"), Decimal("-1"))
    with pytest.raises(BusinessRuleViolation, match="finite"):
        PayrollResult(None, 1, 2, 3, Decimal("Infinity"), Decimal("0"), Decimal("Infinity"))


def test_payroll_result_component_validates_schema_type_amount_and_order() -> None:
    component = PayrollResultComponent(
        None, 1, 2, "earning", Decimal("25.00"), 4294967295
    )
    assert component.component_type == PayrollResultComponent.EARNING
    assert component.calculation_order == 4294967295
    with pytest.raises(BusinessRuleViolation):
        PayrollResultComponent(None, 1, 2, "BONUS", Decimal("1"), 0)
    with pytest.raises(BusinessRuleViolation):
        PayrollResultComponent(None, 1, 2, "DEDUCTION", Decimal("-1"), 0)
    with pytest.raises(BusinessRuleViolation):
        PayrollResultComponent(None, 1, 2, "EARNING", Decimal("1"), 4294967296)


def test_payroll_issue_enforces_status_resolution_check() -> None:
    assert PayrollProcessingIssue(None, 1, "ERR", "message").status == "OPEN"
    resolved_at = datetime(2026, 1, 1)
    issue = PayrollProcessingIssue(
        None, 1, "ERR", "message", status="resolved", resolved_at=resolved_at
    )
    assert issue.status == "RESOLVED"
    with pytest.raises(BusinessRuleViolation):
        PayrollProcessingIssue(None, 1, "ERR", "message", status="RESOLVED")
    with pytest.raises(BusinessRuleViolation):
        PayrollProcessingIssue(
            None, 1, "ERR", "message", status="OPEN", resolved_at=resolved_at
        )


def test_payslip_accepts_schema_fields_and_requires_positive_references() -> None:
    payslip = Payslip(None, 1, "", 2, "")
    assert payslip.payroll_result_id == 1
    assert payslip.document_path == ""
    with pytest.raises(BusinessRuleViolation):
        Payslip(None, 0, "P-1", 2, "/payslip.pdf")
