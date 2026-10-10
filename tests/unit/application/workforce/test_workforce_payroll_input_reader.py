from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.application.workforce.workforce_payroll_input_reader import (
    WorkforcePayrollInputReader,
)
from app.domain.organization.work_calendar import (
    CalendarDateOverride,
    WeeklyRule,
    WorkCalendarVersion,
)
from app.domain.workforce.overtime import OvertimePolicyVersion


class FakeWorkforceUnitOfWork:
    def __init__(self, *, attendance=(), leave_rows=(), policies=(),
                 calendar_overrides=None, assignments=(), revisions=None,
                 revision_components=None, salary_components=None,
                 timezone="Asia/Kolkata"):
        self.attendance_rows = list(attendance)
        self.leave_rows = list(leave_rows)
        self.policy_rows = list(policies)
        self.calendar_overrides = calendar_overrides or {}
        self.assignments = list(assignments)
        self.revisions = revisions or {}
        self.revision_components = revision_components or {}
        self.salary_component_rows = salary_components or {}
        self.writes = 0
        self.payroll_processing_issues = SimpleNamespace(add=self._write)
        self.payroll_results = SimpleNamespace(add=self._write)
        self.payslips = SimpleNamespace(add=self._write)
        self.attendance = SimpleNamespace(get_for_employee_period=self._attendance)
        self.leave_requests = SimpleNamespace(
            get_approved_allocations_for_employee_period=self._approved_leave
        )
        version = WorkCalendarVersion(
            version_number=1,
            effective_from=date(2026, 1, 1),
            effective_to=None,
            time_zone=timezone,
            created_by_user_id=1,
            weekly_rules=tuple(
                WeeklyRule(day, "WORKING_DAY", 480) for day in range(1, 8)
            ),
            version_id=5,
        )
        self.work_calendars = SimpleNamespace(
            get_applicable=lambda day: version,
            get_override=lambda _version_id, day: self.calendar_overrides.get(day),
        )
        self.overtime_policies = SimpleNamespace(get_applicable=self._policy)
        self.employee_salary_assignments = SimpleNamespace(
            get_intersecting_for_employee=self._assignments
        )
        self.salary_revisions = SimpleNamespace(
            get_by_id=lambda revision_id: self.revisions.get(revision_id)
        )
        self.salary_revision_components = SimpleNamespace(
            get_by_revision=lambda revision_id: self.revision_components.get(
                revision_id, []
            )
        )
        self.salary_components = SimpleNamespace(get_by_ids=self._salary_components)

    def _attendance(self, employee_id, start, end):
        return [
            row for row in self.attendance_rows
            if row.employee_id == employee_id and start <= row.attendance_date <= end
        ]

    def _approved_leave(self, employee_id, start, end):
        return [
            row for row in self.leave_rows
            if row[0].employee_id == employee_id
            and row[0].status == "APPROVED"
            and start <= row[1].leave_date <= end
        ]

    def _policy(self, day):
        found = [policy for policy in self.policy_rows if policy.applies_on(day)]
        if len(found) > 1:
            from app.domain.shared.exceptions import InvalidDomainState
            raise InvalidDomainState("Overlapping overtime policy versions are persisted.")
        return found[0] if found else None

    def _assignments(self, employee_id, start, end):
        return [
            item for item in self.assignments
            if item.employee_id == employee_id
            and item.effective_from <= end
            and (item.effective_to is None or item.effective_to >= start)
        ]

    def _salary_components(self, component_ids):
        return [
            value for key, value in self.salary_component_rows.items()
            if key in component_ids
        ]

    def _write(self, *_args, **_kwargs):
        self.writes += 1


def _compensation(*, designated=True, component_type="EARNING", calculation_type="FIXED"):
    assignment = SimpleNamespace(
        salary_assignment_id=20,
        employee_id=7,
        salary_revision_id=30,
        effective_from=date(2026, 1, 1),
        effective_to=None,
    )
    revision = SimpleNamespace(
        salary_revision_id=30,
        salary_structure_id=40,
        revision_number=1,
        effective_from=date(2026, 1, 1),
        effective_to=None,
    )
    revision_component = SimpleNamespace(
        salary_revision_id=30,
        salary_component_id=50,
        calculation_type=calculation_type,
        is_overtime_base=designated,
        fixed_amount=Decimal("1200.00") if calculation_type == "FIXED" else None,
        percentage_value=None if calculation_type == "FIXED" else Decimal("5.0"),
        base_component_id=None if calculation_type == "FIXED" else 51,
    )
    component = SimpleNamespace(
        salary_component_id=50,
        component_code="C50",
        component_name="Name Does Not Determine OT Base",
        component_type=component_type,
        status="ACTIVE",
    )
    component_rows = {50: component}
    if calculation_type == "PERCENTAGE":
        component_rows[51] = SimpleNamespace(
            salary_component_id=51,
            component_code="C51",
            component_name="Percentage Base",
            component_type="EARNING",
            status="ACTIVE",
        )
    return [assignment], {30: revision}, {30: [revision_component]}, component_rows


def test_reader_preserves_attendance_fields_range_boundaries_and_missing_rows():
    day1, day2, day3 = date(2026, 6, 1), date(2026, 6, 2), date(2026, 6, 3)
    row = SimpleNamespace(
        attendance_id=9,
        employee_id=7,
        attendance_date=day2,
        attendance_status="PRESENT",
        check_in_time=datetime(2026, 6, 2, 9),
        check_out_time=datetime(2026, 6, 2, 18),
    )
    uow = FakeWorkforceUnitOfWork(attendance=[row])
    result = WorkforcePayrollInputReader(uow).read(7, day1, day3)
    assert [item.attendance_date for item in result.attendance] == [day1, day2, day3]
    assert result.attendance[0].attendance_id is None
    assert result.attendance[0].status is None
    assert result.attendance[1].attendance_id == 9
    assert result.attendance[1].status == "PRESENT"
    assert result.attendance[1].check_in == row.check_in_time
    assert result.attendance[1].check_out == row.check_out_time
    assert [item.code for item in result.anomalies].count("MISSING_ATTENDANCE") == 2
    assert uow.writes == 0


def test_reader_attendance_is_employee_isolated_and_empty_range_is_explicit():
    day = date(2026, 6, 1)
    row = SimpleNamespace(
        attendance_id=10,
        employee_id=8,
        attendance_date=day,
        attendance_status="ABSENT",
        check_in_time=None,
        check_out_time=None,
    )
    result = WorkforcePayrollInputReader(
        FakeWorkforceUnitOfWork(attendance=[row])
    ).read(7, day, day)
    assert len(result.attendance) == 1
    assert result.attendance[0].attendance_id is None
    assert result.attendance[0].employee_id == 7


def test_reader_preserves_attendance_anomalies_without_calculating_ot():
    day, next_day = date(2026, 6, 1), date(2026, 6, 2)
    rows = [
        SimpleNamespace(attendance_id=1, employee_id=7, attendance_date=day,
                        attendance_status="PRESENT", check_in_time=None,
                        check_out_time=datetime(2026, 6, 1, 18)),
        SimpleNamespace(attendance_id=2, employee_id=7, attendance_date=next_day,
                        attendance_status="PRESENT", check_in_time=datetime(2026, 6, 2, 9),
                        check_out_time=datetime(2026, 6, 3, 10)),
    ]
    result = WorkforcePayrollInputReader(FakeWorkforceUnitOfWork(attendance=rows)).read(
        7, day, next_day
    )
    assert {item.code for item in result.anomalies} == {
        "MISSING_CHECK_IN", "OVER_24_HOURS"
    }


@pytest.mark.parametrize(
    ("day", "check_in", "check_out", "expected"),
    [
        (date(2026, 11, 1), datetime(2026, 11, 1, 1, 30),
         datetime(2026, 11, 1, 2, 30), "AMBIGUOUS_LOCAL_TIME"),
        (date(2026, 3, 8), datetime(2026, 3, 8, 2, 30),
         datetime(2026, 3, 8, 4, 30), "NONEXISTENT_LOCAL_TIME"),
    ],
)
def test_reader_reuses_phase4_dst_anomaly_detection(day, check_in, check_out, expected):
    row = SimpleNamespace(
        attendance_id=5,
        employee_id=7,
        attendance_date=day,
        attendance_status="PRESENT",
        check_in_time=check_in,
        check_out_time=check_out,
    )
    result = WorkforcePayrollInputReader(
        FakeWorkforceUnitOfWork(attendance=[row], timezone="America/New_York")
    ).read(7, day, day)
    assert expected in {item.code for item in result.anomalies}


def test_reader_keeps_approved_leave_per_date_and_fraction():
    start, end = date(2026, 6, 30), date(2026, 7, 1)
    request = SimpleNamespace(
        leave_request_id=4, employee_id=7, leave_type_id=3, status="APPROVED"
    )
    allocations = [
        (request, SimpleNamespace(leave_date=start, day_fraction=Decimal("0.50")),
         SimpleNamespace(payroll_treatment="PAID")),
        (request, SimpleNamespace(leave_date=end, day_fraction=Decimal("0.25")),
         SimpleNamespace(payroll_treatment="PAID")),
    ]
    pending = (SimpleNamespace(leave_request_id=5, employee_id=7, leave_type_id=3,
                               status="PENDING"),
               SimpleNamespace(leave_date=start, day_fraction=Decimal("1.00")),
               SimpleNamespace(payroll_treatment="PAID"))
    uow = FakeWorkforceUnitOfWork(leave_rows=[*allocations, pending])
    result = WorkforcePayrollInputReader(uow).read(7, start, end)
    assert [(item.leave_date, item.day_fraction) for item in result.leave_allocations] == [
        (start, Decimal("0.50")), (end, Decimal("0.25"))
    ]
    assert all(item.status == "APPROVED" for item in result.leave_allocations)
    assert all(item.payroll_treatment == "PAID" for item in result.leave_allocations)


def test_reader_reports_duplicate_approved_leave_allocations():
    day = date(2026, 6, 1)
    requests = [
        SimpleNamespace(leave_request_id=request_id, employee_id=7,
                        leave_type_id=3, status="APPROVED")
        for request_id in (4, 5)
    ]
    rows = [
        (request, SimpleNamespace(leave_date=day, day_fraction=Decimal("0.50")),
         SimpleNamespace(payroll_treatment="PAID"))
        for request in requests
    ]
    result = WorkforcePayrollInputReader(FakeWorkforceUnitOfWork(leave_rows=rows)).read(
        7, day, day
    )
    assert len(result.leave_allocations) == 2
    assert "APPROVED_LEAVE_ALLOCATION_CONFLICT" in {
        item.code for item in result.conditions
    }


@pytest.mark.parametrize("status", ["PENDING", "REJECTED", "CANCELLED"])
def test_reader_excludes_nonapproved_leave(status):
    day = date(2026, 6, 1)
    request = SimpleNamespace(
        leave_request_id=4, employee_id=7, leave_type_id=3, status=status
    )
    row = (request, SimpleNamespace(leave_date=day, day_fraction=Decimal("1.00")),
           SimpleNamespace(payroll_treatment="UNPAID"))
    result = WorkforcePayrollInputReader(FakeWorkforceUnitOfWork(leave_rows=[row])).read(
        7, day, day
    )
    assert result.leave_allocations == ()


def test_reader_preserves_invalid_leave_treatment_condition():
    day = date(2026, 6, 1)
    request = SimpleNamespace(
        leave_request_id=4, employee_id=7, leave_type_id=3, status="APPROVED"
    )
    row = (request, SimpleNamespace(leave_date=day, day_fraction=Decimal("0.5")), None)
    result = WorkforcePayrollInputReader(FakeWorkforceUnitOfWork(leave_rows=[row])).read(
        7, day, day
    )
    assert result.leave_allocations[0].payroll_treatment is None
    assert "INVALID_LEAVE_TREATMENT" in {item.code for item in result.conditions}


def test_reader_calendar_overrides_weekly_rule_and_preserves_timezone():
    day = date(2026, 6, 1)
    override = CalendarDateOverride(5, day, "HOLIDAY", "Holiday")
    result = WorkforcePayrollInputReader(
        FakeWorkforceUnitOfWork(calendar_overrides={day: override})
    ).read(7, day, day)
    assert len(result.calendar_days) == 1
    assert result.calendar_days[0].calendar_version_id == 5
    assert result.calendar_days[0].classification == "HOLIDAY"
    assert result.calendar_days[0].scheduled_minutes == 0
    assert result.calendar_days[0].timezone == "Asia/Kolkata"
    assert WorkforcePayrollInputReader(FakeWorkforceUnitOfWork()).calendar.working_day_count(
        2026, 6
    ) == 30


def test_month_working_day_count_uses_full_calendar_classification_and_overrides():
    holiday = date(2026, 10, 5)
    uow = FakeWorkforceUnitOfWork(
        calendar_overrides={holiday: CalendarDateOverride(5, holiday, "HOLIDAY", "Holiday")}
    )
    version = WorkCalendarVersion(
        version_number=1,
        effective_from=date(2026, 1, 1),
        effective_to=None,
        time_zone="Asia/Kolkata",
        created_by_user_id=1,
        weekly_rules=tuple(
            WeeklyRule(day, "WORKING_DAY" if day <= 5 else "NON_WORKING_DAY", 480 if day <= 5 else 0)
            for day in range(1, 8)
        ),
        version_id=5,
    )
    uow.work_calendars.get_applicable = lambda _day: version

    count = WorkforcePayrollInputReader(uow).calendar.working_day_count(2026, 10)

    assert count == 21


def test_reader_reports_missing_calendar_classification():
    day = date(2026, 6, 1)
    uow = FakeWorkforceUnitOfWork()
    uow.work_calendars.get_applicable = lambda _day: None
    result = WorkforcePayrollInputReader(uow).read(7, day, day)
    assert result.calendar_days == ()
    assert "MISSING_CALENDAR_CLASSIFICATION" in {item.code for item in result.conditions}


def test_reader_preserves_conflicting_calendar_condition():
    from app.domain.shared.exceptions import InvalidDomainState

    day = date(2026, 6, 1)
    uow = FakeWorkforceUnitOfWork()

    def conflicting_calendar(_day):
        raise InvalidDomainState("Overlapping Work Calendar versions are persisted.")

    uow.work_calendars.get_applicable = conflicting_calendar
    result = WorkforcePayrollInputReader(uow).read(7, day, day)
    assert "CONFLICTING_CALENDAR_CLASSIFICATION" in {
        item.code for item in result.conditions
    }


def test_reader_resolves_policy_inclusive_boundaries_and_missing_policy():
    start, end = date(2026, 6, 1), date(2026, 6, 3)
    policy = OvertimePolicyVersion(
        version_number=1,
        effective_from=start,
        effective_to=end,
        non_working_multiplier=Decimal("1.5000"),
        created_by_user_id=1,
        policy_id=7,
    )
    result = WorkforcePayrollInputReader(
        FakeWorkforceUnitOfWork(policies=[policy])
    ).read(7, start, end)
    assert [item.policy_id for item in result.overtime_policies] == [7, 7, 7]
    assert all(item.multiplier == Decimal("1.5000") for item in result.overtime_policies)

    no_policy = WorkforcePayrollInputReader(FakeWorkforceUnitOfWork()).read(
        7, start, start
    )
    assert no_policy.overtime_policies[0].policy_id is None
    assert "MISSING_OVERTIME_POLICY" in {item.code for item in no_policy.conditions}


def test_reader_preserves_conflicting_policy_condition():
    day = date(2026, 6, 1)
    policies = [
        OvertimePolicyVersion(1, day, None, Decimal("1.5"), 1, policy_id=1),
        OvertimePolicyVersion(2, day, None, Decimal("2.0"), 1, policy_id=2),
    ]
    result = WorkforcePayrollInputReader(
        FakeWorkforceUnitOfWork(policies=policies)
    ).read(7, day, day)
    assert result.overtime_policies[0].policy_id is None
    assert "CONFLICTING_OVERTIME_POLICY" in {item.code for item in result.conditions}


def test_reader_resolves_compensation_segments_and_ot_base_from_shared_contract():
    assignments, revisions, revision_components, components = _compensation()
    uow = FakeWorkforceUnitOfWork(
        assignments=assignments,
        revisions=revisions,
        revision_components=revision_components,
        salary_components=components,
    )
    day = date(2026, 6, 1)
    result = WorkforcePayrollInputReader(uow).read(7, day, day)
    segment = result.compensation_segments[0]
    assert segment.assignment_id == 20
    assert segment.salary_revision_id == 30
    assert (segment.segment_start, segment.segment_end) == (day, day)
    assert len(segment.overtime_base_components) == 1
    assert segment.overtime_base_components[0].is_overtime_base is True
    assert segment.overtime_base_components[0].fixed_amount == Decimal("1200.00")
    assert uow.writes == 0


def test_reader_preserves_multiple_compensation_segments_and_boundaries():
    first, second = date(2026, 6, 1), date(2026, 6, 2)
    assignments = [
        SimpleNamespace(salary_assignment_id=20, employee_id=7, salary_revision_id=30,
                        effective_from=first, effective_to=first),
        SimpleNamespace(salary_assignment_id=21, employee_id=7, salary_revision_id=31,
                        effective_from=second, effective_to=second),
    ]
    revisions = {
        30: SimpleNamespace(salary_revision_id=30, salary_structure_id=40,
                            revision_number=1, effective_from=first, effective_to=first),
        31: SimpleNamespace(salary_revision_id=31, salary_structure_id=40,
                            revision_number=2, effective_from=second, effective_to=second),
    }
    revision_components = {
        revision_id: [SimpleNamespace(
            salary_revision_id=revision_id,
            salary_component_id=component_id,
            calculation_type="FIXED",
            is_overtime_base=True,
            fixed_amount=Decimal("1200.00"),
            percentage_value=None,
            base_component_id=None,
        )]
        for revision_id, component_id in ((30, 50), (31, 51))
    }
    salary_components = {
        component_id: SimpleNamespace(
            salary_component_id=component_id,
            component_code=f"C{component_id}",
            component_name="Generic earning",
            component_type="EARNING",
            status="ACTIVE",
        )
        for component_id in (50, 51)
    }
    uow = FakeWorkforceUnitOfWork(
        assignments=assignments,
        revisions=revisions,
        revision_components=revision_components,
        salary_components=salary_components,
    )
    result = WorkforcePayrollInputReader(uow).read(7, first, second)
    assert [
        (item.assignment_id, item.salary_revision_id, item.segment_start, item.segment_end)
        for item in result.compensation_segments
    ] == [(20, 30, first, first), (21, 31, second, second)]
    assert uow.writes == 0


@pytest.mark.parametrize(
    ("designated", "component_type", "calculation_type", "expected"),
    [
        (False, "EARNING", "FIXED", "OVERTIME_BASE_MISSING"),
        (True, "DEDUCTION", "FIXED", "INVALID_OVERTIME_BASE_CONFIGURATION"),
        (True, "EARNING", "PERCENTAGE", "INVALID_OVERTIME_BASE_CONFIGURATION"),
    ],
)
def test_reader_returns_structured_invalid_ot_base_conditions(
    designated, component_type, calculation_type, expected
):
    assignments, revisions, revision_components, components = _compensation(
        designated=designated,
        component_type=component_type,
        calculation_type=calculation_type,
    )
    uow = FakeWorkforceUnitOfWork(
        assignments=assignments,
        revisions=revisions,
        revision_components=revision_components,
        salary_components=components,
    )
    day = date(2026, 6, 1)
    result = WorkforcePayrollInputReader(uow).read(7, day, day)
    assert expected in {item.code for item in result.conditions}
    assert uow.writes == 0


def test_reader_reports_multiple_designated_ot_bases_without_selecting_one():
    assignments, revisions, revision_components, components = _compensation()
    revision_components[30].append(SimpleNamespace(
        salary_revision_id=30,
        salary_component_id=51,
        calculation_type="FIXED",
        is_overtime_base=True,
        fixed_amount=Decimal("500.00"),
        percentage_value=None,
        base_component_id=None,
    ))
    components[51] = SimpleNamespace(
        salary_component_id=51,
        component_code="C51",
        component_name="Another arbitrary name",
        component_type="EARNING",
        status="ACTIVE",
    )
    uow = FakeWorkforceUnitOfWork(
        assignments=assignments,
        revisions=revisions,
        revision_components=revision_components,
        salary_components=components,
    )
    day = date(2026, 6, 1)
    result = WorkforcePayrollInputReader(uow).read(7, day, day)
    segment = result.compensation_segments[0]
    assert len(segment.overtime_base_components) == 2
    assert "OVERTIME_BASE_AMBIGUOUS" in {item.code for item in segment.conditions}
    assert uow.writes == 0


def test_reader_preserves_compensation_gap_condition_without_payroll_issue():
    uow = FakeWorkforceUnitOfWork()
    day = date(2026, 6, 1)
    result = WorkforcePayrollInputReader(uow).read(7, day, day)
    assert "COMPENSATION_COVERAGE_GAP" in {item.code for item in result.conditions}
    assert uow.writes == 0


def test_integrated_reader_combines_sources_without_persistence():
    day = date(2026, 6, 1)
    attendance = SimpleNamespace(
        attendance_id=9,
        employee_id=7,
        attendance_date=day,
        attendance_status="PRESENT",
        check_in_time=datetime(2026, 6, 1, 9),
        check_out_time=datetime(2026, 6, 1, 18),
    )
    request = SimpleNamespace(
        leave_request_id=4, employee_id=7, leave_type_id=3, status="APPROVED"
    )
    leave = (
        request,
        SimpleNamespace(leave_date=day, day_fraction=Decimal("0.25")),
        SimpleNamespace(payroll_treatment="UNPAID"),
    )
    policy = OvertimePolicyVersion(1, day, day, Decimal("1.5"), 1, policy_id=7)
    assignments, revisions, revision_components, components = _compensation()
    uow = FakeWorkforceUnitOfWork(
        attendance=[attendance],
        leave_rows=[leave],
        policies=[policy],
        assignments=assignments,
        revisions=revisions,
        revision_components=revision_components,
        salary_components=components,
    )
    result = WorkforcePayrollInputReader(uow).read(7, day, day)
    assert result.attendance[0].attendance_id == 9
    assert result.leave_allocations[0].day_fraction == Decimal("0.25")
    assert result.calendar_days[0].classification == "WORKING_DAY"
    assert result.overtime_policies[0].policy_id == 7
    assert result.compensation_segments[0].overtime_base_components[0].fixed_amount == Decimal("1200.00")
    assert result.conditions == ()
    assert result.anomalies == ()
    assert uow.writes == 0


def test_reader_rejects_invalid_employee_or_range():
    reader = WorkforcePayrollInputReader(FakeWorkforceUnitOfWork())
    with pytest.raises(ValueError):
        reader.read(0, date(2026, 6, 1), date(2026, 6, 1))
    with pytest.raises(ValueError):
        reader.read(7, date(2026, 6, 2), date(2026, 6, 1))
