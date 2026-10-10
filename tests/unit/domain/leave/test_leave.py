from datetime import date, datetime
from decimal import Decimal

import pytest

from app.domain.leave.leave_balance import LeaveBalance
from app.domain.leave.leave_request import LeaveRequest
from app.domain.leave.leave_type import LeaveType
from app.domain.shared.exceptions import BusinessRuleViolation


def test_leave_type_construction_normalizes_values() -> None:
    leave_type = LeaveType(None, " ANNUAL ", " Annual Leave ", " paid leave ", "PAID")

    assert leave_type.leave_type_code == "ANNUAL"
    assert leave_type.leave_type_name == "Annual Leave"
    assert leave_type.description == "paid leave"
    assert leave_type.payroll_treatment == "PAID"
    assert leave_type.is_active is True


@pytest.mark.parametrize(
    "values",
    [
        {"leave_type_code": " "},
        {"leave_type_name": " "},
        {"leave_type_code": "x" * 31},
        {"leave_type_name": "x" * 101},
        {"description": "x" * 501},
        {"payroll_treatment": "UNKNOWN"},
        {"payroll_treatment": None},
    ],
)
def test_leave_type_rejects_invalid_values(values: dict[str, str]) -> None:
    args = {
        "leave_type_id": None,
        "leave_type_code": "ANNUAL",
        "leave_type_name": "Annual Leave",
        "description": None,
        "payroll_treatment": "PAID",
        "is_active": True,
    }
    args.update(values)
    with pytest.raises(BusinessRuleViolation):
        LeaveType(**args)


def test_leave_balance_construction() -> None:
    balance = LeaveBalance(None, 5, 2, 2026, Decimal("20.00"), Decimal("2.50"))

    assert balance.allocated_days == Decimal("20.00")
    assert balance.used_days == Decimal("2.50")


@pytest.mark.parametrize(
    ("allocated", "used", "message"),
    [
        ("-1", "0", "Allocated leave days cannot be negative"),
        ("1", "-1", "Used leave days cannot be negative"),
        ("1", "2", "Used leave days cannot exceed allocated days"),
    ],
)
def test_leave_balance_rejects_invalid_days(
    allocated: str, used: str, message: str
) -> None:
    with pytest.raises(BusinessRuleViolation, match=message):
        LeaveBalance(None, 5, 2, 2026, Decimal(allocated), Decimal(used))


def test_leave_request_construction() -> None:
    request = LeaveRequest(
        None, 5, 2, date(2026, 10, 1), date(2026, 10, 2), Decimal("1.50")
    )

    assert request.status == LeaveRequest.PENDING
    assert request.requested_days == Decimal("1.50")


def test_leave_request_accepts_reviewed_approval() -> None:
    reviewed_at = datetime(2026, 9, 20, 12, 0)
    request = LeaveRequest(
        None,
        5,
        2,
        date(2026, 10, 1),
        date(2026, 10, 2),
        Decimal("2.00"),
        status="approved",
        reviewed_by_employee_id=8,
        reviewed_at=reviewed_at,
    )

    assert request.status == LeaveRequest.APPROVED
    assert request.reviewed_at == reviewed_at


@pytest.mark.parametrize(
    "changes",
    [
        {"end_date": date(2026, 9, 30)},
        {"requested_days": Decimal("0")},
        {"status": "UNKNOWN"},
        {"reviewed_by_employee_id": 8},
        {"reviewed_at": datetime(2026, 9, 20)},
        {"status": "APPROVED"},
        {"status": "REJECTED", "reviewed_by_employee_id": 8},
    ],
)
def test_leave_request_rejects_schema_invalid_state(changes: dict[str, object]) -> None:
    args: dict[str, object] = {
        "leave_request_id": None,
        "employee_id": 5,
        "leave_type_id": 2,
        "start_date": date(2026, 10, 1),
        "end_date": date(2026, 10, 2),
        "requested_days": Decimal("1.00"),
    }
    args.update(changes)
    with pytest.raises(BusinessRuleViolation):
        LeaveRequest(**args)
