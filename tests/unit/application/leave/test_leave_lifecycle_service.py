from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.application.leave.leave_request_service import LeaveRequestService
from app.application.leave.schemas import LeaveRequestCreateRequest
from app.domain.organization.work_calendar import WeeklyRule, WorkCalendarVersion
from app.domain.shared.exceptions import BusinessRuleViolation
from app.infrastructure.persistence.models.leave_request import LeaveRequestModel


def make_uow(*, status: str = "PENDING", treatment: str | None = "PAID") -> MagicMock:
    uow = MagicMock()
    uow.employees.get_by_id.return_value = SimpleNamespace(employee_id=5)
    uow.employees.get_by_id_for_update.return_value = SimpleNamespace(employee_id=5)
    uow.employees.get_by_user_id.return_value = SimpleNamespace(employee_id=8)
    uow.leave_types.get_by_id.return_value = SimpleNamespace(
        leave_type_id=2, payroll_treatment=treatment
    )
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
    model = LeaveRequestModel(
        leave_request_id=11,
        employee_id=5,
        leave_type_id=2,
        start_date=date(2026, 10, 12),
        end_date=date(2026, 10, 13),
        requested_days=Decimal("2.00"),
        reason="Personal",
        status=status,
        reviewed_by_employee_id=8 if status == "APPROVED" else None,
        reviewed_at=datetime(2026, 10, 1) if status == "APPROVED" else None,
        review_comment=None,
    )
    days = [
        SimpleNamespace(leave_date=date(2026, 10, day), day_fraction=Decimal("1.00"))
        for day in (12, 13)
    ]
    uow.leave_requests.get_by_id.return_value = model
    uow.leave_requests.get_days.return_value = days
    uow.leave_requests.find_approved_conflicts.return_value = []
    uow.leave_requests.transition_status.side_effect = (
        lambda request_id, expected, target, reviewer=None, at=None, comment=None:
        _transition(model, expected, target, reviewer, at, comment)
    )
    uow.leave_requests.add.side_effect = lambda req: setattr(req, "leave_request_id", 11)
    uow.leave_requests.add_days.return_value = None
    return uow


def _transition(model, expected, target, reviewer, reviewed_at, comment) -> bool:
    if model.status != expected:
        return False
    model.status = target
    if target in {"APPROVED", "REJECTED"}:
        model.reviewed_by_employee_id = reviewer
        model.reviewed_at = reviewed_at
        model.review_comment = comment
    return True


def payload(**changes) -> LeaveRequestCreateRequest:
    values = {
        "employee_id": 5,
        "leave_type_id": 2,
        "start_date": date(2026, 10, 12),
        "end_date": date(2026, 10, 13),
        "requested_days": Decimal("2.00"),
        "allocations": [
            {"leave_date": date(2026, 10, 12), "day_fraction": Decimal("1.00")},
            {"leave_date": date(2026, 10, 13), "day_fraction": Decimal("1.00")},
        ],
    }
    values.update(changes)
    return LeaveRequestCreateRequest(**values)


def test_create_request_is_pending_with_atomic_decimal_allocations_and_audit() -> None:
    uow = make_uow()
    response = LeaveRequestService(uow).create(payload(), 44, "request-1")
    assert response.status == "PENDING"
    assert len(response.allocations) == 2
    assert sum((item.day_fraction for item in response.allocations), Decimal("0.00")) == Decimal("2.00")
    assert uow.leave_requests.add_days.call_args.args[0] == 11
    event = uow.audit_events.add.call_args.args[0]
    assert event.action_type == "LEAVE_REQUEST_CREATED"
    assert event.actor_user_id == 44
    assert event.correlation_id == "request-1"
    uow.commit.assert_called_once()


def test_create_rejects_incorrect_allocation_total() -> None:
    uow = make_uow()
    with pytest.raises(BusinessRuleViolation, match="must equal requested_days"):
        LeaveRequestService(uow).create(
            payload(allocations=[{"leave_date": date(2026, 10, 12), "day_fraction": Decimal("1.00")}]),
            44,
            None,
        )
    uow.leave_requests.add.assert_not_called()


def test_create_rejects_allocation_outside_request_period() -> None:
    uow = make_uow()
    with pytest.raises(BusinessRuleViolation, match="within the request"):
        LeaveRequestService(uow).create(
            payload(
                requested_days=Decimal("1.00"),
                allocations=[{"leave_date": date(2026, 10, 14), "day_fraction": Decimal("1.00")}],
            ),
            44,
            None,
        )
    uow.leave_requests.add.assert_not_called()


def test_create_allows_cross_month_allocations_without_prorating_aggregate() -> None:
    uow = make_uow()
    request = LeaveRequestCreateRequest(
        employee_id=5,
        leave_type_id=2,
        start_date=date(2026, 10, 30),
        end_date=date(2026, 11, 2),
        requested_days=Decimal("2.00"),
        allocations=[
            {"leave_date": date(2026, 10, 30), "day_fraction": Decimal("1.00")},
            {"leave_date": date(2026, 11, 2), "day_fraction": Decimal("1.00")},
        ],
    )
    response = LeaveRequestService(uow).create(request, 44, None)
    assert response.requested_days == Decimal("2.00")
    assert [day.leave_date for day in response.allocations] == [
        date(2026, 10, 30), date(2026, 11, 2)
    ]


def test_create_rejects_nonworking_or_holiday_calendar_day() -> None:
    uow = make_uow()
    uow.work_calendars.get_override.return_value = SimpleNamespace(
        classification="HOLIDAY", label="Holiday"
    )
    with pytest.raises(BusinessRuleViolation, match="not a WORKING_DAY"):
        LeaveRequestService(uow).create(
            payload(
                requested_days=Decimal("1.00"),
                allocations=[{"leave_date": date(2026, 10, 12), "day_fraction": Decimal("1.00")}],
            ),
            44,
            None,
        )


def test_approval_checks_treatment_locks_employee_and_audits() -> None:
    uow = make_uow()
    response = LeaveRequestService(uow).approve(11, 44, "approve-1", "Looks good")
    assert response.status == "APPROVED"
    assert response.reviewed_by_employee_id == 8
    uow.employees.get_by_id_for_update.assert_called_once_with(5)
    uow.leave_requests.find_approved_conflicts.assert_called_once()
    event = uow.audit_events.add.call_args.args[0]
    assert event.action_type == "LEAVE_REQUEST_APPROVED"
    assert event.actor_user_id == 44
    uow.commit.assert_called_once()


def test_approval_rejects_unresolved_leave_type_treatment() -> None:
    uow = make_uow(treatment=None)
    with pytest.raises(BusinessRuleViolation, match="unresolved"):
        LeaveRequestService(uow).approve(11, 44, None)
    uow.leave_requests.transition_status.assert_not_called()
    uow.commit.assert_not_called()


def test_approval_rejects_approved_overlap_but_pending_overlap_is_allowed_on_create() -> None:
    uow = make_uow()
    uow.leave_requests.find_approved_conflicts.return_value = [date(2026, 10, 12)]
    with pytest.raises(BusinessRuleViolation, match="Approved leave already exists"):
        LeaveRequestService(uow).approve(11, 44, None)
    uow.leave_requests.transition_status.assert_not_called()

    create_uow = make_uow()
    LeaveRequestService(create_uow).create(payload(), 44, None)
    create_uow.leave_requests.find_approved_conflicts.assert_not_called()


@pytest.mark.parametrize(
    ("status", "operation", "expected"),
    [
        ("PENDING", "reject", "REJECTED"),
        ("PENDING", "cancel", "CANCELLED"),
        ("APPROVED", "cancel", "CANCELLED"),
    ],
)
def test_reject_and_cancel_lifecycle_transitions_are_audited(status, operation, expected) -> None:
    uow = make_uow(status=status)
    service = LeaveRequestService(uow)
    response = getattr(service, operation)(11, 44, "transition")
    assert response.status == expected
    assert uow.audit_events.add.call_args.args[0].action_type == f"LEAVE_REQUEST_{expected}"
    uow.commit.assert_called_once()


def test_approval_fails_when_conditional_transition_loses_race() -> None:
    uow = make_uow()
    uow.leave_requests.transition_status.side_effect = None
    uow.leave_requests.transition_status.return_value = False
    with pytest.raises(BusinessRuleViolation, match="changed concurrently"):
        LeaveRequestService(uow).approve(11, 44, None)
    uow.audit_events.add.assert_not_called()
    uow.commit.assert_not_called()
