from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from app.application.leave.leave_balance_service import LeaveBalanceService
from app.application.leave.leave_request_service import LeaveRequestService
from app.application.leave.leave_type_service import LeaveTypeService
from app.application.leave.schemas import (
    LeaveBalanceCreateRequest,
    LeaveRequestCreateRequest,
    LeaveTypeCreateRequest,
)
from app.domain.shared.exceptions import BusinessRuleViolation
from app.domain.organization.work_calendar import WeeklyRule, WorkCalendarVersion


def make_uow() -> MagicMock:
    uow = MagicMock()
    uow.employees.get_by_id.return_value = object()
    uow.leave_types.get_by_id.return_value = object()
    uow.leave_types.get_by_code.return_value = None
    uow.leave_types.get_by_name.return_value = None
    uow.leave_balances.get_by_employee_type_year.return_value = None
    uow.leave_requests.add.side_effect = lambda model: setattr(model, "leave_request_id", 3)
    uow.leave_balances.add.side_effect = lambda model: setattr(model, "leave_balance_id", 4)
    uow.leave_types.add.side_effect = lambda model: setattr(model, "leave_type_id", 2)
    uow.employees.get_by_user_id.return_value = type("Employee", (), {"employee_id": 8})()
    uow.employees.get_by_id_for_update.return_value = object()
    uow.work_calendars.get_applicable.return_value = WorkCalendarVersion(
        1,
        date(2026, 1, 1),
        date(2026, 12, 31),
        "UTC",
        1,
        tuple(WeeklyRule(day, "WORKING_DAY", 480) for day in range(1, 8)),
        version_id=1,
    )
    uow.work_calendars.get_override.return_value = None
    uow.leave_requests.add_days.return_value = None
    uow.leave_requests.get_days.return_value = []
    return uow


def test_create_leave_type_commits_and_returns_response() -> None:
    uow = make_uow()

    result = LeaveTypeService(uow).create(
        LeaveTypeCreateRequest(leave_type_code="ANNUAL", leave_type_name="Annual Leave", payroll_treatment="PAID")
        , actor_user_id=1, correlation_id="test"
    )

    assert result.leave_type_id == 2
    assert result.leave_type_code == "ANNUAL"
    uow.leave_types.add.assert_called_once()
    assert uow.audit_events.add.call_args.args[0].action_type == "LEAVE_TYPE_CREATED"
    assert uow.audit_events.add.call_args.args[0].actor_user_id == 1
    uow.commit.assert_called_once()


@pytest.mark.parametrize("duplicate", ["code", "name"])
def test_create_leave_type_rejects_duplicates(duplicate: str) -> None:
    uow = make_uow()
    getattr(uow.leave_types, f"get_by_{duplicate}").return_value = object()

    with pytest.raises(BusinessRuleViolation):
        LeaveTypeService(uow).create(
            LeaveTypeCreateRequest(leave_type_code="ANNUAL", leave_type_name="Annual Leave", payroll_treatment="PAID")
            , actor_user_id=1, correlation_id="test"
        )

    uow.leave_types.add.assert_not_called()
    uow.commit.assert_not_called()


def test_create_leave_balance_commits() -> None:
    uow = make_uow()
    result = LeaveBalanceService(uow).create(
        LeaveBalanceCreateRequest(
            employee_id=5,
            leave_type_id=2,
            balance_year=2026,
            allocated_days=Decimal("20.00"),
            used_days=Decimal("2.00"),
        )
    )

    assert result.leave_balance_id == 4
    assert result.allocated_days == Decimal("20.00")
    uow.leave_balances.add.assert_called_once()
    uow.commit.assert_called_once()


@pytest.mark.parametrize("missing", ["employee", "leave_type", "duplicate"])
def test_create_leave_balance_rejects_missing_reference_or_duplicate(missing: str) -> None:
    uow = make_uow()
    if missing == "employee":
        uow.employees.get_by_id.return_value = None
    elif missing == "leave_type":
        uow.leave_types.get_by_id.return_value = None
    else:
        uow.leave_balances.get_by_employee_type_year.return_value = object()

    with pytest.raises(BusinessRuleViolation):
        LeaveBalanceService(uow).create(
            LeaveBalanceCreateRequest(
                employee_id=5,
                leave_type_id=2,
                balance_year=2026,
                allocated_days=Decimal("1.00"),
            )
        )

    uow.leave_balances.add.assert_not_called()
    uow.commit.assert_not_called()


def test_create_leave_balance_rejects_used_days_above_allocation() -> None:
    uow = make_uow()
    with pytest.raises(BusinessRuleViolation, match="cannot exceed"):
        LeaveBalanceService(uow).create(
            LeaveBalanceCreateRequest(
                employee_id=5,
                leave_type_id=2,
                balance_year=2026,
                allocated_days=Decimal("1.00"),
                used_days=Decimal("2.00"),
            )
        )
    uow.commit.assert_not_called()


def test_create_leave_request_commits_pending_request() -> None:
    uow = make_uow()
    result = LeaveRequestService(uow).create(
        LeaveRequestCreateRequest(
            employee_id=5,
            leave_type_id=2,
            start_date=date(2026, 10, 1),
            end_date=date(2026, 10, 2),
            requested_days=Decimal("1.00"),
            allocations=[{"leave_date": date(2026, 10, 1), "day_fraction": Decimal("1.00")}],
        ),
        actor_user_id=1,
        correlation_id="test",
    )

    assert result.leave_request_id == 3
    assert result.status == "PENDING"
    uow.leave_requests.add.assert_called_once()
    uow.leave_requests.add_days.assert_called_once()
    uow.commit.assert_called_once()


@pytest.mark.parametrize("missing", ["employee", "leave_type"])
def test_create_leave_request_rejects_missing_reference(missing: str) -> None:
    uow = make_uow()
    request_values: dict[str, object] = {
        "employee_id": 5,
        "leave_type_id": 2,
        "start_date": date(2026, 10, 1),
        "end_date": date(2026, 10, 2),
        "requested_days": Decimal("1.00"),
        "allocations": [{"leave_date": date(2026, 10, 1), "day_fraction": Decimal("1.00")}],
    }
    if missing == "employee":
        uow.employees.get_by_id.return_value = None
    elif missing == "leave_type":
        uow.leave_types.get_by_id.return_value = None

    with pytest.raises(BusinessRuleViolation):
        LeaveRequestService(uow).create(
            LeaveRequestCreateRequest(**request_values), actor_user_id=1, correlation_id=None
        )

    uow.leave_requests.add.assert_not_called()
    uow.commit.assert_not_called()


@pytest.mark.parametrize(
    "changes",
    [{"end_date": date(2026, 9, 30)}],
)
def test_create_leave_request_rejects_invalid_request(changes: dict[str, object]) -> None:
    uow = make_uow()
    values: dict[str, object] = {
        "employee_id": 5,
        "leave_type_id": 2,
        "start_date": date(2026, 10, 1),
        "end_date": date(2026, 10, 2),
        "requested_days": Decimal("2.00"),
        "allocations": [
            {"leave_date": date(2026, 10, 1), "day_fraction": Decimal("1.00")},
            {"leave_date": date(2026, 10, 2), "day_fraction": Decimal("1.00")},
        ],
    }
    values.update(changes)
    with pytest.raises(BusinessRuleViolation):
        LeaveRequestService(uow).create(
            LeaveRequestCreateRequest(**values), actor_user_id=1, correlation_id=None
        )
    uow.leave_requests.add.assert_not_called()
    uow.commit.assert_not_called()


def test_create_leave_request_schema_requires_allocations() -> None:
    with pytest.raises(ValidationError):
        LeaveRequestCreateRequest(
            employee_id=5,
            leave_type_id=2,
            start_date=date(2026, 10, 1),
            end_date=date(2026, 10, 2),
            requested_days=Decimal("1.00"),
            allocations=[],
        )
