from datetime import date
from decimal import Decimal

import pytest

from app.domain.leave.leave_request import LeaveRequest
from app.domain.leave.leave_request_day import LeaveRequestDay
from app.domain.leave.leave_type import LeaveType
from app.domain.shared.exceptions import BusinessRuleViolation


@pytest.mark.parametrize("treatment", ["PAID", "UNPAID"])
def test_leave_type_accepts_explicit_treatment(treatment: str) -> None:
    leave_type = LeaveType(None, "ANNUAL", "Annual", payroll_treatment=treatment)
    assert leave_type.payroll_treatment == treatment


@pytest.mark.parametrize("treatment", [None, "", "UNKNOWN", "paid-ish"])
def test_leave_type_rejects_missing_or_invalid_treatment(treatment: str | None) -> None:
    with pytest.raises(BusinessRuleViolation):
        LeaveType(None, "ANNUAL", "Annual", payroll_treatment=treatment)


@pytest.mark.parametrize(
    "fraction",
    [Decimal("0.00"), Decimal("1.01"), Decimal("0.001"), Decimal("NaN")],
)
def test_leave_request_day_rejects_invalid_fraction(fraction: Decimal) -> None:
    with pytest.raises(BusinessRuleViolation):
        LeaveRequestDay(date(2026, 10, 12), fraction)


def test_leave_request_day_accepts_decimal_hundredths() -> None:
    allocation = LeaveRequestDay(date(2026, 10, 12), Decimal("0.37"))
    assert allocation.day_fraction == Decimal("0.37")


@pytest.mark.parametrize(
    ("start", "target", "allowed"),
    [
        ("PENDING", "APPROVED", True),
        ("PENDING", "REJECTED", True),
        ("PENDING", "CANCELLED", True),
        ("APPROVED", "CANCELLED", True),
        ("REJECTED", "APPROVED", False),
        ("CANCELLED", "APPROVED", False),
        ("APPROVED", "APPROVED", False),
        ("REJECTED", "CANCELLED", False),
    ],
)
def test_leave_lifecycle_transition_matrix(start: str, target: str, allowed: bool) -> None:
    if allowed:
        LeaveRequest.ensure_transition(start, target)
    else:
        with pytest.raises(BusinessRuleViolation):
            LeaveRequest.ensure_transition(start, target)
