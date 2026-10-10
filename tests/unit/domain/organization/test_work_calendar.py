from datetime import date

import pytest

from app.domain.organization.work_calendar import (
    HOLIDAY,
    NON_WORKING_DAY,
    WORKING_DAY,
    CalendarDateOverride,
    WeeklyRule,
    WorkCalendarVersion,
)
from app.domain.shared.exceptions import BusinessRuleViolation


def rules() -> tuple[WeeklyRule, ...]:
    return tuple(
        WeeklyRule(day, WORKING_DAY if day <= 5 else NON_WORKING_DAY, 480 if day <= 5 else 0)
        for day in range(1, 8)
    )


def test_version_requires_complete_iso_week_and_preserves_timezone() -> None:
    version = WorkCalendarVersion(1, date(2026, 1, 1), None, "UTC", 1, rules())
    assert version.time_zone == "UTC"
    assert version.rule_for(date(2026, 1, 3)).classification == NON_WORKING_DAY


@pytest.mark.parametrize(
    "weekly_rules",
    [rules()[:-1], rules()[:-1] + (WeeklyRule(5, WORKING_DAY, 480),)],
)
def test_version_rejects_missing_or_duplicate_weekday(weekly_rules: tuple[WeeklyRule, ...]) -> None:
    with pytest.raises(BusinessRuleViolation):
        WorkCalendarVersion(1, date(2026, 1, 1), None, "UTC", 1, weekly_rules)


def test_version_rejects_invalid_timezone_and_period() -> None:
    with pytest.raises(BusinessRuleViolation):
        WorkCalendarVersion(1, date(2026, 2, 1), date(2026, 1, 31), "UTC", 1, rules())
    with pytest.raises(BusinessRuleViolation):
        WorkCalendarVersion(1, date(2026, 1, 1), None, "Not/AZone", 1, rules())


def test_weekly_rules_enforce_minutes_and_classification() -> None:
    with pytest.raises(BusinessRuleViolation):
        WeeklyRule(1, WORKING_DAY, 0)
    with pytest.raises(BusinessRuleViolation):
        WeeklyRule(1, "HOLIDAY", 0)


def test_override_requires_holiday_label_and_normalizes_values() -> None:
    with pytest.raises(BusinessRuleViolation):
        CalendarDateOverride(1, date(2026, 1, 1), HOLIDAY)
    holiday = CalendarDateOverride(1, date(2026, 1, 1), "holiday", "  New Year  ")
    assert holiday.classification == HOLIDAY
    assert holiday.label == "New Year"


def test_effective_range_is_inclusive() -> None:
    version = WorkCalendarVersion(1, date(2026, 1, 1), date(2026, 1, 31), "UTC", 1, rules())
    assert version.applies_on(date(2026, 1, 31))
    assert not version.applies_on(date(2026, 2, 1))

