from datetime import date, datetime
from decimal import Decimal, localcontext
from types import SimpleNamespace

import pytest

from app.application.workforce.overtime_derivation_service import OvertimeDerivationService
from app.domain.organization.work_calendar import CalendarDateOverride, WeeklyRule, WorkCalendarVersion
from app.domain.shared.exceptions import BusinessRuleViolation
from app.domain.workforce.overtime import OvertimePolicyVersion


class FakeUow:
    def __init__(self, attendance: SimpleNamespace, *, zone: str = "UTC", holidays: set[date] | None = None):
        self.attendance = SimpleNamespace(get_by_id=lambda _id: attendance)
        self.work_calendars = CalendarRepo(zone, holidays or set())
        self.overtime_policies = SimpleNamespace(get_applicable=lambda day: OvertimePolicyVersion(
            1, date(2020, 1, 1), None, Decimal("1.5000"), 7, 11))
        self.employee_salary_assignments = SimpleNamespace(get_applicable_for_employee=lambda *_args: [
            SimpleNamespace(salary_revision_id=4, effective_from=date(2020, 1, 1), effective_to=None)
        ])
        self.salary_revisions = SimpleNamespace(get_by_id=lambda _id: SimpleNamespace(
            salary_revision_id=4, effective_from=date(2020, 1, 1), effective_to=None))
        self.salary_revision_components = SimpleNamespace(get_by_revision=lambda _id: [
            SimpleNamespace(salary_component_id=8, is_overtime_base=True, calculation_type="FIXED", fixed_amount=Decimal("44000.00"))
        ])
        self.salary_components = SimpleNamespace(get_by_ids=lambda _ids: [
            SimpleNamespace(salary_component_id=8, component_type="EARNING")
        ])


class CalendarRepo:
    def __init__(self, zone: str, holidays: set[date]):
        self.version = WorkCalendarVersion(
            1, date(2020, 1, 1), None, zone, 7,
            tuple(WeeklyRule(day, "WORKING_DAY" if day <= 5 else "NON_WORKING_DAY", 480 if day <= 5 else 0)
                  for day in range(1, 8)), version_id=2)
        self.holidays = holidays

    def get_applicable(self, _day):
        return self.version

    def get_override(self, _version_id, day):
        if day in self.holidays:
            return CalendarDateOverride(2, day, "HOLIDAY", "Holiday", override_id=3)
        return None


def attendance(day: date, start: datetime | None, end: datetime | None, status: str = "PRESENT"):
    return SimpleNamespace(attendance_id=3, employee_id=9, attendance_date=day,
                           check_in_time=start, check_out_time=end, attendance_status=status)


def derive(item, *, zone="UTC", holidays=None):
    return OvertimeDerivationService(FakeUow(item, zone=zone, holidays=holidays)).derive_attendance(3, item.attendance_date.year, item.attendance_date.month)


def test_working_day_calculates_one_hour_ot_with_full_month_working_day_denominator():
    results, anomalies = derive(attendance(date(2026, 3, 4), datetime(2026, 3, 4, 8), datetime(2026, 3, 4, 17)))
    assert not anomalies
    assert len(results) == 1
    assert results[0].overtime_minutes == Decimal(60)
    assert results[0].overtime_hours == Decimal(1)
    assert results[0].working_day_denominator == 22
    assert results[0].hourly_rate == Decimal(250)
    assert results[0].amount == Decimal("250.00")


def test_fractional_hour_uses_exact_minutes_until_final_rounding():
    results, _ = derive(attendance(date(2026, 3, 4), datetime(2026, 3, 4, 8), datetime(2026, 3, 4, 17, 35)))
    assert results[0].overtime_minutes == Decimal(95)
    with localcontext() as context:
        context.prec = 50
        assert results[0].overtime_hours == Decimal(95) / Decimal(60)
    assert results[0].amount == Decimal("395.83")


def test_one_minute_ot_is_preserved_and_final_amount_uses_half_up():
    item = attendance(date(2026, 3, 4), datetime(2026, 3, 4, 8), datetime(2026, 3, 4, 16, 1))
    uow = FakeUow(item)
    uow.salary_revision_components.get_by_revision = lambda _revision_id: [
        SimpleNamespace(salary_component_id=8, is_overtime_base=True, calculation_type="FIXED",
                        fixed_amount=Decimal("264.00"))
    ]
    results, _ = OvertimeDerivationService(uow).derive_attendance(3, 2026, 3)
    assert results[0].overtime_minutes == Decimal(1)
    assert results[0].amount == Decimal("0.03")
    assert results[0].time_zone == "UTC"


@pytest.mark.parametrize("start,end", [
    (datetime(2026, 3, 4, 8), datetime(2026, 3, 4, 16)),
    (datetime(2026, 3, 4, 8), datetime(2026, 3, 4, 15, 59)),
])
def test_working_day_at_or_under_480_has_no_ot(start: datetime, end: datetime):
    results, anomalies = derive(attendance(date(2026, 3, 4), start, end))
    assert results == () and anomalies == ()


def test_non_working_day_uses_all_worked_minutes_and_policy_multiplier():
    item = attendance(date(2026, 3, 7), datetime(2026, 3, 7, 10), datetime(2026, 3, 7, 11))
    results, _ = derive(item)
    assert results[0].overtime_minutes == Decimal(60)
    assert results[0].multiplier == Decimal("1.5000")
    assert results[0].amount == Decimal("375.00")


@pytest.mark.parametrize("status", ["HALF_DAY", "ABSENT"])
def test_half_day_and_absent_do_not_derive_ot(status: str):
    results, anomalies = derive(attendance(date(2026, 3, 4), datetime(2026, 3, 4, 8), datetime(2026, 3, 4, 20), status))
    assert results == () and anomalies == ()


@pytest.mark.parametrize("start,end", [
    (None, datetime(2026, 3, 4, 18)),
    (datetime(2026, 3, 4, 8), None),
])
def test_missing_timestamp_is_nonblocking_anomaly(start, end):
    results, anomalies = derive(attendance(date(2026, 3, 4), start, end))
    assert results == ()
    assert anomalies[0].code == "MISSING_TIMESTAMP"


def test_reversed_and_excessive_durations_are_nonblocking_anomalies():
    reversed_result, reversed_anomaly = derive(attendance(date(2026, 3, 4), datetime(2026, 3, 4, 9), datetime(2026, 3, 4, 8)))
    long_result, long_anomaly = derive(attendance(date(2026, 3, 4), datetime(2026, 3, 4, 0), datetime(2026, 3, 5, 0, 1)))
    assert reversed_result == () and reversed_anomaly[0].code == "REVERSED_TIMESTAMPS"
    assert long_result == () and long_anomaly[0].code == "DURATION_EXCEEDS_24_HOURS"


def test_cross_midnight_resolves_each_calendar_date_independently():
    day2 = date(2026, 3, 6)
    item = attendance(date(2026, 3, 5), datetime(2026, 3, 5, 22), datetime(2026, 3, 6, 2))
    results, anomalies = derive(item, holidays={day2})
    assert not anomalies
    assert len(results) == 1
    assert results[0].attendance_date == date(2026, 3, 5)
    assert results[0].classification == "HOLIDAY"
    assert results[0].overtime_minutes == Decimal(120)


def test_cross_date_compensation_uses_revision_applicable_to_each_portion():
    item = attendance(date(2026, 3, 4), datetime(2026, 3, 4, 16), datetime(2026, 3, 5, 16))
    uow = FakeUow(item)
    uow.employee_salary_assignments.get_applicable_for_employee = lambda _employee_id, day: [
        SimpleNamespace(salary_revision_id=4 if day == date(2026, 3, 4) else 5,
                        effective_from=day, effective_to=None)
    ]
    uow.salary_revisions.get_by_id = lambda revision_id: SimpleNamespace(
        salary_revision_id=revision_id,
        effective_from=date(2026, 3, 4) if revision_id == 4 else date(2026, 3, 5),
        effective_to=None,
    )
    uow.salary_revision_components.get_by_revision = lambda revision_id: [
        SimpleNamespace(salary_component_id=8, is_overtime_base=True, calculation_type="FIXED",
                        fixed_amount=Decimal("44000.00") if revision_id == 4 else Decimal("22000.00"))
    ]
    results, anomalies = OvertimeDerivationService(uow).derive_attendance(3, 2026, 3)
    assert not anomalies
    assert len(results) == 1
    assert results[0].salary_revision_id == 5
    assert results[0].overtime_base_amount == Decimal("22000.00")
    assert results[0].overtime_minutes == Decimal(480)


@pytest.mark.parametrize("assignments", [[], [
    SimpleNamespace(salary_revision_id=4, effective_from=date(2020, 1, 1), effective_to=None),
    SimpleNamespace(salary_revision_id=5, effective_from=date(2020, 1, 1), effective_to=None),
]])
def test_missing_or_ambiguous_compensation_segment_does_not_fall_back(assignments):
    item = attendance(date(2026, 3, 4), datetime(2026, 3, 4, 8), datetime(2026, 3, 4, 17))
    uow = FakeUow(item)
    uow.employee_salary_assignments.get_applicable_for_employee = lambda *_args: assignments
    with pytest.raises(BusinessRuleViolation, match="Exactly one compensation assignment"):
        OvertimeDerivationService(uow).derive_attendance(3, 2026, 3)


def test_local_checkin_date_must_match_attendance_date():
    results, anomalies = derive(attendance(date(2026, 3, 4), datetime(2026, 3, 5, 8), datetime(2026, 3, 5, 18)))
    assert results == ()
    assert anomalies[0].code == "CHECK_IN_DATE_MISMATCH"


def test_ambiguous_dst_local_time_is_nonblocking_anomaly():
    item = attendance(date(2026, 11, 1), datetime(2026, 11, 1, 1, 30), datetime(2026, 11, 1, 2, 30))
    results, anomalies = derive(item, zone="America/New_York")
    assert results == ()
    assert anomalies[0].code == "AMBIGUOUS_LOCAL_TIME"


def test_nonexistent_dst_local_time_is_nonblocking_anomaly():
    item = attendance(date(2026, 3, 8), datetime(2026, 3, 8, 2, 30), datetime(2026, 3, 8, 4, 30))
    results, anomalies = derive(item, zone="America/New_York")
    assert results == ()
    assert anomalies[0].code == "NONEXISTENT_LOCAL_TIME"


def test_missing_policy_is_configuration_blocker_when_ot_exists():
    item = attendance(date(2026, 3, 4), datetime(2026, 3, 4, 8), datetime(2026, 3, 4, 17))
    uow = FakeUow(item)
    uow.overtime_policies.get_applicable = lambda _day: None
    with pytest.raises(BusinessRuleViolation, match="No overtime policy"):
        OvertimeDerivationService(uow).derive_attendance(3, 2026, 3)
