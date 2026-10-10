from dataclasses import replace
from datetime import date, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.application.payroll.workforce_snapshot_materializer import (
    WorkforceSnapshotMaterializer,
)
from app.application.workforce.payroll_input_contracts import (
    AttendanceInput,
    CalendarDayInput,
    CompensationSegmentInput,
    LeaveAllocationInput,
    OvertimePolicyInput,
    WorkforceInputCondition,
    WorkforcePayrollInputResult,
)
from app.application.compensation.contracts import SalaryComponentSnapshot
from app.domain.workforce.overtime import OvertimeAnomaly


def _inputs(*, conditions=()):
    day = date(2026, 10, 8)
    component = SalaryComponentSnapshot(
        salary_component_id=42,
        component_name="Base salary",
        component_type="EARNING",
        calculation_type="FIXED",
        is_overtime_base=True,
        fixed_amount=Decimal("1200.00"),
        percentage_value=None,
        base_component_id=None,
    )
    return WorkforcePayrollInputResult(
        employee_id=7,
        range_start=day,
        range_end=day,
        attendance=(AttendanceInput(7, day, None, None, None, None),),
        leave_allocations=(
            LeaveAllocationInput(
                20, 7, 5, "UNPAID", "APPROVED", day, Decimal("0.50")
            ),
        ),
        calendar_days=(CalendarDayInput(3, 2, day, "WORKING_DAY", 480, "Asia/Kolkata"),),
        overtime_policies=(
            OvertimePolicyInput(
                day, 9, 4, date(2026, 1, 1), None, Decimal("1.5000")
            ),
        ),
        compensation_segments=(
            CompensationSegmentInput(
                7, 30, 31, day, day, (component,), (component,), ()
            ),
        ),
        anomalies=(OvertimeAnomaly("MISSING_ATTENDANCE", "No row", None, day),),
        conditions=tuple(conditions),
    )


def _materializer(result):
    uow = MagicMock()
    eligibility = SimpleNamespace(
        eligible_employees=(
            SimpleNamespace(
                employee_id=7,
                applicable_employment_start=result.range_start,
                applicable_employment_end=result.range_end,
            ),
        )
    )
    with patch(
        "app.application.payroll.workforce_snapshot_materializer.WorkforcePayrollInputReader"
    ) as reader_type:
        reader_type.return_value.read.return_value = result
        reader_type.return_value.calendar.working_day_count.return_value = 22
        materializer = WorkforceSnapshotMaterializer(uow)
    return uow, materializer, eligibility, reader_type


def test_materializer_captures_immutable_decision30_input_categories():
    timestamp = datetime(2026, 10, 8, 12, 0, 0, 123456)
    uow, materializer, eligibility, reader_type = _materializer(_inputs())

    result = materializer.collect(
        payroll_run_id=80,
        attempt_number=3,
        payroll_year=2026,
        payroll_month=10,
        snapshot_at=timestamp,
        eligibility=eligibility,
    )

    reader_type.return_value.read.assert_called_once_with(
        7, date(2026, 10, 8), date(2026, 10, 8)
    )
    assert len(result.snapshots) == 1
    row = result.snapshots[0]
    assert (row.payroll_run_id, row.employee_id, row.attempt_number) == (80, 7, 3)
    assert row.snapshot_at == timestamp
    assert row.snapshot["snapshot_format_version"] == 1
    assert row.snapshot["snapshot_at"] == timestamp.isoformat()
    assert row.snapshot["payroll_period"] == {"year": 2026, "month": 10}
    assert row.snapshot["monthly_working_day_count"] == 22
    assert row.snapshot["attendance"][0]["effective_status"] == "PRESENT"
    assert row.snapshot["attendance"][0]["missing_attendance"] is True
    assert row.snapshot["leave_allocations"][0]["payable_effect"]["applies"] is True
    assert row.snapshot["calendar_days"][0]["calendar_version_number"] == 2
    assert row.snapshot["overtime_policies"][0]["policy_version_number"] == 4
    segment = row.snapshot["compensation_segments"][0]
    assert segment["salary_assignment_id"] == 30
    assert segment["salary_revision_id"] == 31
    assert segment["overtime_base_components"][0]["salary_component_id"] == 42
    assert segment["overtime_base_components"][0]["overtime_base_amount"] == "1200.00"
    assert row.snapshot["anomalies"][0]["code"] == "MISSING_ATTENDANCE"
    assert row.snapshot["rule_metadata"]["financial_calculation"] == "not_performed"
    reader_type.return_value.calendar.working_day_count.assert_called_once_with(2026, 10)
    assert result.pending_issues == ()
    uow.payroll_results.add.assert_not_called()
    uow.payroll_result_components.add.assert_not_called()


@pytest.mark.parametrize(
    ("range_start", "range_end"),
    [
        (date(2026, 10, 1), date(2026, 10, 31)),
        (date(2026, 10, 15), date(2026, 10, 31)),
        (date(2026, 10, 1), date(2026, 10, 14)),
    ],
    ids=["full-month-employee", "mid-month-joiner", "mid-month-leaver"],
)
def test_monthly_working_day_count_is_full_month_and_calendar_days_stay_employee_scoped(
    range_start, range_end
):
    inputs = _inputs()
    dates = []
    current = range_start
    while current <= range_end:
        dates.append(current)
        current += timedelta(days=1)
    employee_calendar_days = tuple(
        CalendarDayInput(
            3,
            2,
            day,
            "WORKING_DAY" if day.weekday() < 5 else "NON_WORKING_DAY",
            480 if day.weekday() < 5 else 0,
            "Asia/Kolkata",
        )
        for day in dates
    )
    inputs = replace(
        inputs,
        range_start=range_start,
        range_end=range_end,
        calendar_days=employee_calendar_days,
    )
    _, materializer, eligibility, reader_type = _materializer(inputs)

    first = materializer.collect(
        payroll_run_id=80,
        attempt_number=3,
        payroll_year=2026,
        payroll_month=10,
        snapshot_at=datetime(2026, 10, 8, 12),
        eligibility=eligibility,
    )
    second = materializer.collect(
        payroll_run_id=80,
        attempt_number=3,
        payroll_year=2026,
        payroll_month=10,
        snapshot_at=datetime(2026, 10, 8, 12),
        eligibility=eligibility,
    )

    payload = first.snapshots[0].snapshot
    expected_month_count = sum(
        date(2026, 10, day).weekday() < 5 for day in range(1, 32)
    )
    employee_range_count = sum(
        item.classification == "WORKING_DAY" for item in employee_calendar_days
    )
    assert expected_month_count == 22
    assert payload["monthly_working_day_count"] == expected_month_count
    assert payload["monthly_working_day_count"] != employee_range_count or (
        range_start == date(2026, 10, 1) and range_end == date(2026, 10, 31)
    )
    assert [item["date"] for item in payload["calendar_days"]] == [
        day.isoformat() for day in dates
    ]
    assert second.snapshots[0].snapshot["monthly_working_day_count"] == payload[
        "monthly_working_day_count"
    ]
    assert reader_type.return_value.calendar.working_day_count.call_count == 2


def test_materializer_fences_issues_and_persists_snapshots_without_upsert():
    conditions = (
        WorkforceInputCondition(
            "MISSING_CALENDAR_CLASSIFICATION", "Missing calendar", 7, date(2026, 10, 8)
        ),
        WorkforceInputCondition(
            "INVALID_LEAVE_TREATMENT", "Invalid leave", 7, date(2026, 10, 8)
        ),
    )
    uow, materializer, eligibility, _ = _materializer(_inputs(conditions=conditions))
    result = materializer.collect(
        payroll_run_id=80,
        attempt_number=3,
        payroll_year=2026,
        payroll_month=10,
        snapshot_at=datetime(2026, 10, 8, 12),
        eligibility=eligibility,
    )
    assert [request.employee_id for request in result.pending_issues] == [None, 7]

    with patch(
        "app.application.payroll.workforce_snapshot_materializer.PayrollProcessingIssueService.create",
        side_effect=[SimpleNamespace(payroll_issue_id=51), SimpleNamespace(payroll_issue_id=52)],
    ) as create_issue:
        issue_ids = materializer.persist(result, 3)
    assert issue_ids == (51, 52)
    assert all(call.kwargs == {"commit": False} for call in create_issue.call_args_list)
    uow.payroll_run_workforce_snapshots.add.assert_called_once_with(
        result.snapshots[0], 3
    )
