from datetime import date, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.application.compensation.contracts import (
    EmployeeCompensationSnapshot,
    EmployeeSalaryAssignmentSnapshot,
    SalaryComponentSnapshot,
    SalaryRevisionSnapshot,
)
from app.application.compensation.segmentation import CompensationSegment
from app.application.payroll.payroll_financial_calculator import (
    PayrollCalculationError,
    PayrollFinancialCalculationService,
    _calculate_employee,
)
from app.application.payroll.payroll_processing_orchestrator import (
    PayrollProcessingOrchestrator,
)
from app.domain.payroll.payroll_run_workforce_snapshot import (
    PayrollRunWorkforceSnapshot,
)
from app.domain.shared.exceptions import BusinessRuleViolation


def _component(
    component_id,
    *,
    kind="EARNING",
    mode="FIXED",
    amount="22000.00",
    rate=None,
    base=None,
    overtime=False,
):
    return SalaryComponentSnapshot(
        salary_component_id=component_id,
        component_name=f"Component {component_id}",
        component_type=kind,
        calculation_type=mode,
        is_overtime_base=overtime,
        fixed_amount=None if mode == "PERCENTAGE" else Decimal(amount),
        percentage_value=Decimal(rate) if rate is not None else None,
        base_component_id=base,
    )


def _segment(start, end, components):
    assignment = EmployeeSalaryAssignmentSnapshot(10, 20, start, end)
    revision = SalaryRevisionSnapshot(
        20,
        30,
        1,
        start,
        end,
        tuple(components),
    )
    return CompensationSegment(
        7,
        start,
        end,
        EmployeeCompensationSnapshot(7, assignment, revision),
    )


def _snapshot(
    dates,
    *,
    attendance=None,
    leave=(),
    classifications=None,
    policies=None,
    monthly_working_days=None,
    anomalies=(),
    timezones=None,
):
    attendance = attendance or {}
    classifications = classifications or {}
    policies = policies or {}
    timezones = timezones or {}
    calendar_days = []
    attendance_rows = []
    overtime_policies = []
    for day in dates:
        classification = classifications.get(day, "WORKING_DAY")
        calendar_days.append(
            {
                "date": day.isoformat(),
                "classification": classification,
                "timezone": timezones.get(day, "UTC"),
                "calendar_version_id": 1,
                "calendar_version_number": 1,
                "scheduled_minutes": 480 if classification == "WORKING_DAY" else 0,
            }
        )
        status, check_in, check_out = attendance.get(day, (None, None, None))
        if status is not None and check_in is None and check_out is None:
            check_in = f"{day.isoformat()}T08:00:00"
            check_out = f"{day.isoformat()}T16:00:00"
        missing = status is None
        attendance_rows.append(
            {
                "date": day.isoformat(),
                "attendance_id": None if missing else 100 + day.day,
                "status": status,
                "effective_status": "PRESENT" if missing else status,
                "missing_attendance": missing,
                "check_in": check_in,
                "check_out": check_out,
            }
        )
        multiplier = policies.get(day)
        overtime_policies.append(
            {
                "date": day.isoformat(),
                "policy_version_id": 3 if multiplier is not None else None,
                "policy_version_number": 1 if multiplier is not None else None,
                "multiplier": multiplier,
            }
        )
    payload = {
        "employee_id": 7,
        "attempt_number": 1,
        "monthly_working_day_count": monthly_working_days
        if monthly_working_days is not None
        else sum(classification == "WORKING_DAY" for classification in classifications.values())
        if classifications
        else len(dates),
        "processing_range": {"start": dates[0].isoformat(), "end": dates[-1].isoformat()},
        "calendar_days": calendar_days,
        "attendance": attendance_rows,
        "leave_allocations": list(leave),
        "overtime_policies": overtime_policies,
        "anomalies": [],
        "rule_metadata": {"financial_calculation": "not_performed"},
        "input_conditions": [],
    }
    payload["anomalies"] = list(anomalies)
    return PayrollRunWorkforceSnapshot(
        payroll_run_id=5,
        employee_id=7,
        attempt_number=1,
        snapshot_at=datetime(2026, 1, 1),
        snapshot=payload,
    )


def _dates(count):
    return [date(2026, 1, day) for day in range(1, count + 1)]


def test_fixed_full_month_and_percentage_dependency_use_pre_workforce_amounts():
    dates = _dates(22)
    components = [
        _component(1, overtime=True),
        _component(2, mode="PERCENTAGE", amount="0", rate="20", base=1),
    ]
    segment = _segment(dates[0], dates[-1], components)
    result = _calculate_employee(
        5,
        7,
        1,
        [segment],
        10,
        _snapshot(dates, monthly_working_days=22),
    )
    assert [item.compensation_amount for item in result.components] == [
        Decimal("22000.00"),
        Decimal("4400.00"),
    ]
    assert result.gross_earnings == Decimal("26400.00")
    assert result.total_deductions == Decimal("0.00")
    assert result.net_salary == Decimal("26400.00")


def test_fixed_proration_rounds_before_percentage_dependency_base():
    dates = _dates(1)
    components = [
        _component(1, amount="0.05", overtime=True),
        _component(2, mode="PERCENTAGE", amount="0", rate="50", base=1),
    ]
    result = _calculate_employee(
        5, 7, 1, [_segment(dates[0], dates[0], components)], 10,
        _snapshot(dates, monthly_working_days=2),
    )
    assert result.components[0].compensation_amount == Decimal("0.03")
    assert result.components[1].compensation_amount == Decimal("0.02")
    segment_rows = result.workforce_snapshot["financial_calculation"]["segments"]
    assert segment_rows[0]["components"][1]["base_amount"] == "0.03"


def test_attendance_adjustment_rounds_at_segment_component_boundary():
    day = date(2026, 1, 5)
    result = _calculate_employee(
        5, 7, 1,
        [_segment(day, day, [_component(1, amount="0.05", overtime=True)])],
        10,
        _snapshot(
            [day], attendance={day: ("HALF_DAY", None, None)}, monthly_working_days=1
        ),
    )
    assert result.components[0].compensation_amount == Decimal("0.05")
    assert result.components[0].workforce_adjustment == Decimal("-0.02")
    assert result.components[0].final_amount == Decimal("0.03")


def test_segment_proration_and_unpaid_leave_adjust_multiple_earnings_after_dag():
    dates = _dates(15)
    unpaid_date = dates[0]
    components = [
        _component(1, overtime=True),
        _component(2, mode="PERCENTAGE", amount="0", rate="20", base=1),
    ]
    leave = [
        {
            "date": unpaid_date.isoformat(),
            "status": "APPROVED",
            "treatment": "UNPAID",
            "day_fraction": "1.00",
        }
    ]
    result = _calculate_employee(
        5,
        7,
        1,
        [_segment(dates[0], dates[-1], components)],
        10,
        _snapshot(dates, leave=leave, monthly_working_days=22),
    )
    basic, hra = result.components
    assert basic.compensation_amount == Decimal("15000.00")
    assert hra.compensation_amount == Decimal("3000.00")
    assert basic.workforce_adjustment == Decimal("-1000.00")
    assert hra.workforce_adjustment == Decimal("-200.00")
    assert basic.final_amount == Decimal("14000.00")
    assert hra.final_amount == Decimal("2800.00")


def test_multiple_compensation_segments_aggregate_to_one_real_component():
    dates = _dates(22)
    first = _segment(dates[0], dates[14], [_component(1, overtime=True)])
    second_component = _component(1, amount="11000.00", overtime=True)
    second = _segment(dates[15], dates[21], [second_component])
    result = _calculate_employee(
        5,
        7,
        1,
        [first, second],
        10,
        _snapshot(dates, monthly_working_days=22),
    )
    assert len(result.components) == 1
    assert result.components[0].compensation_amount == Decimal("18500.00")
    assert result.components[0].final_amount == Decimal("18500.00")


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("PRESENT", Decimal("1.00")),
        ("HALF_DAY", Decimal("0.50")),
        ("ABSENT", Decimal("0.00")),
        ("HOLIDAY", Decimal("1.00")),
    ],
)
def test_working_day_attendance_fraction(status, expected):
    day = date(2026, 1, 5)
    result = _calculate_employee(
        5,
        7,
        1,
        [_segment(day, day, [_component(1, overtime=True)])],
        10,
        _snapshot([day], attendance={day: (status, None, None)}, monthly_working_days=22),
    )
    assert result.components[0].final_amount == Decimal("22000.00") / 22 * expected


def test_missing_working_day_attendance_defaults_to_present():
    day = date(2026, 1, 5)
    result = _calculate_employee(
        5,
        7,
        1,
        [_segment(day, day, [_component(1, overtime=True)])],
        10,
        _snapshot([day], monthly_working_days=22),
    )
    assert result.components[0].final_amount == Decimal("1000.00")


@pytest.mark.parametrize(
    ("treatment", "fraction", "expected"),
    [
        ("PAID", "1.00", Decimal("1.00")),
        ("UNPAID", "1.00", Decimal("0.00")),
        ("PAID", "0.50", Decimal("0.50")),
        ("UNPAID", "0.50", Decimal("0.50")),
    ],
)
def test_on_leave_uses_approved_allocation_exactly(treatment, fraction, expected):
    day = date(2026, 1, 5)
    allocation = {
        "date": day.isoformat(),
        "status": "APPROVED",
        "treatment": treatment,
        "day_fraction": fraction,
    }
    result = _calculate_employee(
        5,
        7,
        1,
        [_segment(day, day, [_component(1, overtime=True)])],
        10,
        _snapshot(
            [day],
            attendance={day: ("ON_LEAVE", None, None)},
            leave=[allocation],
            monthly_working_days=22,
        ),
    )
    assert result.components[0].final_amount == Decimal("22000.00") / 22 * expected


@pytest.mark.parametrize("leave_status", ["PENDING", "REJECTED", None])
def test_on_leave_without_approved_allocation_is_blocking(leave_status):
    day = date(2026, 1, 5)
    leave = [] if leave_status is None else [
        {
            "date": day.isoformat(),
            "status": leave_status,
            "treatment": "PAID",
            "day_fraction": "1.00",
        }
    ]
    with pytest.raises(PayrollCalculationError, match="no unique approved Leave"):
        _calculate_employee(
            5,
            7,
            1,
            [_segment(day, day, [_component(1, overtime=True)])],
            10,
            _snapshot(
                [day],
                attendance={day: ("ON_LEAVE", None, None)},
                leave=leave,
                monthly_working_days=22,
            ),
        )


def test_work_calendar_nonworking_days_excluded_and_paid_leave_caps_at_one():
    days = [date(2026, 1, 5), date(2026, 1, 6)]
    components = [_component(1, overtime=True)]
    leave = [
        {
            "date": days[0].isoformat(),
            "status": "APPROVED",
            "treatment": "PAID",
            "day_fraction": "0.50",
        }
    ]
    snapshot = _snapshot(
        days,
        leave=leave,
        classifications={days[0]: "WORKING_DAY", days[1]: "HOLIDAY"},
        monthly_working_days=22,
    )
    result = _calculate_employee(
        5, 7, 1, [_segment(days[0], days[-1], components)], 10, snapshot
    )
    assert result.components[0].final_amount == Decimal("1000.00")


@pytest.mark.parametrize("status,treatment,expected", [
    ("PRESENT", "UNPAID", Decimal("0.00")),
    ("ABSENT", "UNPAID", Decimal("0.00")),
    ("PRESENT", "PAID", Decimal("1.00")),
])
def test_payable_fraction_is_floored_or_capped(status, treatment, expected):
    day = date(2026, 1, 5)
    allocation = {
        "date": day.isoformat(),
        "status": "APPROVED",
        "treatment": treatment,
        "day_fraction": "1.00",
    }
    result = _calculate_employee(
        5,
        7,
        1,
        [_segment(day, day, [_component(1, overtime=True)])],
        10,
        _snapshot(
            [day],
            attendance={day: (status, None, None)},
            leave=[allocation],
            monthly_working_days=22,
        ),
    )
    assert result.workforce_snapshot["financial_calculation"]["segments"][0][
        "segment_payable_fraction"
    ] == str(expected)


@pytest.mark.parametrize("status", ["PENDING", "REJECTED"])
def test_nonapproved_leave_is_ignored_for_regular_attendance(status):
    day = date(2026, 1, 5)
    allocation = {
        "date": day.isoformat(),
        "status": status,
        "treatment": "UNPAID",
        "day_fraction": "1.00",
    }
    result = _calculate_employee(
        5,
        7,
        1,
        [_segment(day, day, [_component(1, overtime=True)])],
        10,
        _snapshot(
            [day],
            attendance={day: ("PRESENT", None, None)},
            leave=[allocation],
            monthly_working_days=22,
        ),
    )
    assert result.components[0].final_amount == Decimal("1000.00")


def test_working_day_overtime_is_separate_from_leave_fraction_and_uses_frozen_denominator():
    day = date(2026, 1, 5)
    # ON_LEAVE proves OT does not inherit the regular earning payable fraction.
    attendance = {day: ("ON_LEAVE", "2026-01-05T08:00:00", "2026-01-05T17:00:00")}
    leave = [
        {
            "date": day.isoformat(),
            "status": "APPROVED",
            "treatment": "UNPAID",
            "day_fraction": "1.00",
        }
    ]
    result = _calculate_employee(
        5,
        7,
        1,
        [_segment(day, day, [_component(1, overtime=True)])],
        10,
        _snapshot(
            [day],
            attendance=attendance,
            leave=leave,
            monthly_working_days=22,
        ),
    )
    assert result.components[0].compensation_amount == Decimal("1000.00")
    assert result.components[0].workforce_adjustment == Decimal("-1000.00")
    assert result.components[0].overtime_adjustment == Decimal("125.00")


def test_ot_does_not_change_percentage_dependency_base():
    day = date(2026, 1, 5)
    components = [
        _component(1, amount="22000.00", overtime=True),
        _component(2, mode="PERCENTAGE", amount="0", rate="10", base=1),
    ]
    result = _calculate_employee(
        5, 7, 1, [_segment(day, day, components)], 10,
        _snapshot(
            [day],
            attendance={day: ("PRESENT", "2026-01-05T08:00:00", "2026-01-05T17:00:00")},
            monthly_working_days=22,
        ),
    )
    assert result.components[0].overtime_adjustment == Decimal("125.00")
    assert result.components[1].compensation_amount == Decimal("100.00")


def test_regular_and_nonworking_overtime_use_frozen_policy_and_full_month_rate():
    day = date(2026, 1, 5)
    working = _snapshot(
        [day],
        attendance={day: ("PRESENT", "2026-01-05T08:00:00", "2026-01-05T17:00:00")},
        monthly_working_days=22,
    )
    result = _calculate_employee(
        5, 7, 1, [_segment(day, day, [_component(1, overtime=True)])], 10, working
    )
    assert result.components[0].overtime_adjustment == Decimal("125.00")

    holiday = _snapshot(
        [day],
        attendance={day: ("PRESENT", "2026-01-05T08:00:00", "2026-01-05T09:00:00")},
        classifications={day: "HOLIDAY"},
        policies={day: "1.5000"},
        monthly_working_days=22,
    )
    result = _calculate_employee(
        5, 7, 1, [_segment(day, day, [_component(1, overtime=True)])], 10, holiday
    )
    assert result.components[0].overtime_adjustment == Decimal("187.50")


def test_valid_overnight_overtime_is_split_by_calendar_date():
    days = [date(2026, 1, 5), date(2026, 1, 6)]
    snapshot = _snapshot(
        days,
        attendance={days[0]: ("PRESENT", "2026-01-05T22:00:00", "2026-01-06T02:00:00")},
        classifications={days[0]: "WORKING_DAY", days[1]: "HOLIDAY"},
        policies={days[1]: "1.5000"},
        monthly_working_days=22,
    )
    result = _calculate_employee(
        5, 7, 1, [_segment(days[0], days[1], [_component(1, overtime=True)])], 10, snapshot
    )
    assert result.components[0].overtime_adjustment == Decimal("375.00")
    overtime_rows = result.workforce_snapshot["financial_calculation"]["segments"][0]["overtime"]
    assert [row["overtime_date"] for row in overtime_rows] == ["2026-01-06"]
    assert overtime_rows[0]["overtime_minutes"] == "120"


def test_calendar_timezone_change_during_overnight_interval_blocks():
    days = [date(2026, 1, 5), date(2026, 1, 6)]
    snapshot = _snapshot(
        days,
        attendance={days[0]: ("PRESENT", "2026-01-05T22:00:00", "2026-01-06T02:00:00")},
        monthly_working_days=22,
        timezones={days[1]: "America/New_York"},
    )
    with pytest.raises(PayrollCalculationError) as error:
        _calculate_employee(
            5, 7, 1, [_segment(days[0], days[1], [_component(1, overtime=True)])], 10, snapshot
        )
    assert error.value.code == "CALENDAR_TIMEZONE_CHANGED_DURING_INTERVAL"


@pytest.mark.parametrize(
    ("check_in", "check_out", "expected_code"),
    [
        (None, "2026-01-05T17:00:00", "MISSING_CHECK_IN"),
        ("2026-01-05T08:00:00", None, "MISSING_CHECK_OUT"),
        ("2026-01-05T17:00:00", "2026-01-05T08:00:00", "INVALID_ATTENDANCE_INTERVAL"),
    ],
)
def test_unusable_attendance_intervals_block_calculation(check_in, check_out, expected_code):
    day = date(2026, 1, 5)
    with pytest.raises(PayrollCalculationError) as error:
        _calculate_employee(
            5, 7, 1, [_segment(day, day, [_component(1, overtime=True)])], 10,
            _snapshot(
                [day], attendance={day: ("PRESENT", check_in, check_out)},
                monthly_working_days=22,
            ),
        )
    assert error.value.code == expected_code


@pytest.mark.parametrize("code", ["AMBIGUOUS_LOCAL_TIME", "NONEXISTENT_LOCAL_TIME"])
def test_dst_timestamp_anomaly_remains_nonblocking_and_is_preserved(code):
    day = date(2026, 1, 5)
    anomaly = {
        "code": code,
        "message": "DST timestamp cannot be resolved uniquely.",
        "attendance_id": 105,
        "affected_date": day.isoformat(),
    }
    result = _calculate_employee(
        5, 7, 1, [_segment(day, day, [_component(1, overtime=True)])], 10,
        _snapshot(
            [day],
            attendance={day: ("PRESENT", "2026-01-05T08:00:00", "2026-01-05T17:00:00")},
            monthly_working_days=22,
            anomalies=[anomaly],
        ),
    )
    assert result.components[0].overtime_adjustment == Decimal("0.00")
    assert result.workforce_snapshot["anomalies"][0]["code"] == code


@pytest.mark.parametrize(
    "code",
    ["CHECK_IN_DATE_MISMATCH", "OVER_24_HOURS", "INVALID_ATTENDANCE_INTERVAL", "UNKNOWN_TIME_ANOMALY"],
)
def test_other_snapshot_timestamp_anomalies_block_calculation(code):
    day = date(2026, 1, 5)
    anomaly = {
        "code": code,
        "message": "Frozen timestamp anomaly.",
        "attendance_id": 105,
        "affected_date": day.isoformat(),
    }
    with pytest.raises(PayrollCalculationError) as error:
        _calculate_employee(
            5, 7, 1, [_segment(day, day, [_component(1, overtime=True)])], 10,
            _snapshot([day], monthly_working_days=22, anomalies=[anomaly]),
        )
    assert error.value.code == code


def test_period_overtime_accumulates_intervals_before_half_up_rounding():
    days = [date(2026, 1, 5), date(2026, 1, 6)]
    attendance = {
        days[0]: ("PRESENT", "2026-01-05T08:00:00", "2026-01-05T16:00:01"),
        days[1]: ("PRESENT", "2026-01-06T08:00:00", "2026-01-06T16:00:01"),
    }
    result = _calculate_employee(
        5, 7, 1, [_segment(days[0], days[1], [_component(1, amount="141.12", overtime=True)])],
        10,
        _snapshot(days, attendance=attendance, monthly_working_days=1),
    )
    # Each interval contributes $0.0049; period aggregation rounds $0.0098 to $0.01.
    assert result.components[0].overtime_adjustment == Decimal("0.01")
    # A single interval with an exact half-cent period total proves ROUND_HALF_UP.
    half_cent_day = days[0]
    half_cent = _calculate_employee(
        5, 7, 1, [_segment(half_cent_day, half_cent_day, [_component(1, amount="144.00", overtime=True)])],
        10,
        _snapshot(
            [half_cent_day],
            attendance={half_cent_day: ("PRESENT", "2026-01-05T08:00:00", "2026-01-05T16:00:01")},
            monthly_working_days=1,
        ),
    )
    assert half_cent.components[0].overtime_adjustment == Decimal("0.01")


@pytest.mark.parametrize("components,code", [
    ([_component(1, mode="PERCENTAGE", amount="0", rate="10", base=99), _component(2, overtime=True)], "PERCENTAGE_BASE_MISSING"),
    ([_component(1, mode="PERCENTAGE", amount="0", rate="10", base=2), _component(2, mode="PERCENTAGE", amount="0", rate="10", base=1), _component(3, overtime=True)], "SALARY_COMPONENT_CYCLE"),
    ([_component(1)], "OVERTIME_BASE_MISSING"),
    ([_component(1, overtime=True), _component(2, overtime=True)], "OVERTIME_BASE_AMBIGUOUS"),
])
def test_invalid_component_dependencies_and_overtime_bases_are_blocking(components, code):
    day = date(2026, 1, 5)
    with pytest.raises(PayrollCalculationError) as error:
        _calculate_employee(
            5,
            7,
            1,
            [_segment(day, day, components)],
            10,
            _snapshot([day], monthly_working_days=22),
        )
    assert error.value.code == code


def test_deductions_gross_net_and_component_rounding():
    day = date(2026, 1, 5)
    components = [
        _component(1, amount="100.00", overtime=True),
        _component(2, kind="DEDUCTION", amount="33.335"),
    ]
    result = _calculate_employee(
        5,
        7,
        1,
        [_segment(day, day, components)],
        10,
        _snapshot([day], monthly_working_days=1),
    )
    assert result.gross_earnings == Decimal("100.00")
    assert result.total_deductions == Decimal("33.34")
    assert result.net_salary == Decimal("66.66")


class _MemoryRepository:
    def __init__(self, value=None, *, stale=False):
        self.value = value
        self.stale = stale
        self.items = []

    def get_by_id(self, *_args):
        return self.value

    def get_by_id_for_update(self, *_args):
        return self.value

    def get_by_run_and_employee(self, *_args):
        return None

    def get_by_result_and_component(self, *_args):
        return None

    def lock_active_attempt(self, *_args):
        return None if self.stale else self.value or object()

    def renew_active_attempt_lease(self, *_args):
        return not self.stale

    def add(self, item):
        if hasattr(item, "payroll_result_id") and getattr(item, "payroll_result_id") is None:
            item.payroll_result_id = 11
        if hasattr(item, "payroll_result_component_id"):
            item.payroll_result_component_id = len(self.items) + 21
        if hasattr(item, "payroll_issue_id"):
            item.payroll_issue_id = len(self.items) + 31
        self.items.append(item)
        self.value = item
        return item


class _MemoryUow:
    def __init__(self, *, stale=False):
        self.payroll_runs = _MemoryRepository(SimpleNamespace(payroll_run_id=5), stale=stale)
        self.employees = _MemoryRepository(SimpleNamespace(employee_id=7))
        self.employee_salary_assignments = _MemoryRepository(SimpleNamespace(salary_assignment_id=10))
        self.payroll_results = _MemoryRepository()
        self.payroll_result_components = _MemoryRepository()
        self.payroll_processing_issues = _MemoryRepository()
        self.salary_components = _MemoryRepository(SimpleNamespace(salary_component_id=1))
        self.commits = 0
        self.rollbacks = 0

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def test_result_and_components_persist_in_one_commit_with_snapshot():
    dates = _dates(2)
    uow = _MemoryUow()
    service = PayrollFinancialCalculationService(uow)
    calculation = service.calculate_employee(
        5,
        7,
        1,
        [
            _segment(dates[0], dates[0], [_component(1, overtime=True)]),
            _segment(dates[1], dates[1], [_component(1, overtime=True)]),
        ],
        10,
        _snapshot(dates, monthly_working_days=22),
    )
    assert uow.commits == 1
    assert len(uow.payroll_results.items) == 1
    assert len(uow.payroll_result_components.items) == 1
    assert uow.payroll_results.items[0].workforce_calculation_snapshot[
        "financial_calculation"
    ]["calculation_status"] == "CALCULATED"
    assert uow.payroll_results.items[0].workforce_calculation_snapshot[
        "rule_metadata"
    ]["financial_calculation"] == "performed"
    assert calculation.workforce_snapshot["rule_metadata"][
        "financial_calculation"
    ] == "performed"
    assert _snapshot(dates, monthly_working_days=22).snapshot["rule_metadata"][
        "financial_calculation"
    ] == "not_performed"
    assert calculation.components[0].salary_component_id == 1


def test_stale_attempt_is_rejected_before_result_persistence():
    day = date(2026, 1, 5)
    uow = _MemoryUow(stale=True)
    service = PayrollFinancialCalculationService(uow)
    with pytest.raises(BusinessRuleViolation, match="attempt is no longer active"):
        service.calculate_employee(
            5,
            7,
            1,
            [_segment(day, day, [_component(1, overtime=True)])],
            10,
            _snapshot([day], monthly_working_days=22),
        )
    assert uow.commits == 0
    assert uow.payroll_results.items == []


@pytest.mark.parametrize(
    ("check_in", "check_out", "expected_issue_code"),
    [
        (None, "2026-01-05T17:00:00", "MISSING_CHECK_IN"),
        ("2026-01-05T08:00:00", None, "MISSING_CHECK_OUT"),
        ("2026-01-05T17:00:00", "2026-01-05T08:00:00", "INVALID_ATTENDANCE_INTERVAL"),
    ],
)
def test_blocking_ot_input_persists_open_issue_without_result(
    check_in, check_out, expected_issue_code
):
    day = date(2026, 1, 5)
    snapshot = _snapshot(
        [day],
        attendance={day: ("PRESENT", check_in, check_out)},
        monthly_working_days=22,
    )
    segment = _segment(day, day, [_component(1, overtime=True)])
    compensation = SimpleNamespace(
        employee_id=7,
        assignment=SimpleNamespace(salary_assignment_id=10),
    )
    eligibility = SimpleNamespace(eligible_employees=(SimpleNamespace(employee_id=7),))
    compensation_snapshot = SimpleNamespace(employees=(compensation,))
    segmentation = SimpleNamespace(blocked_employee_ids=(), segments=(segment,))
    uow = _MemoryUow()

    issue_ids = PayrollProcessingOrchestrator(uow)._calculate_employee_results(
        payroll_run_id=5,
        attempt_number=1,
        eligibility=eligibility,
        compensation_snapshot=compensation_snapshot,
        segmentation=segmentation,
        workforce_snapshots=(snapshot,),
    )

    assert issue_ids == (31,)
    assert uow.rollbacks == 1
    assert uow.commits == 1
    assert uow.payroll_results.items == []
    assert len(uow.payroll_processing_issues.items) == 1
    issue = uow.payroll_processing_issues.items[0]
    assert issue.employee_id == 7
    assert issue.issue_code == expected_issue_code
    assert issue.status == "OPEN"
