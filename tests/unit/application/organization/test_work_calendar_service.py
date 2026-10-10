from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.application.organization.work_calendar_schemas import (
    WorkCalendarDateOverrideCreateRequest,
    WorkCalendarVersionCreateRequest,
)
from app.application.organization.work_calendar_service import WorkCalendarService
from app.domain.organization.work_calendar import (
    HOLIDAY,
    NON_WORKING_DAY,
    WORKING_DAY,
    CalendarDateOverride,
    WeeklyRule,
    WorkCalendarVersion,
)
from app.domain.shared.exceptions import BusinessRuleViolation


def weekly_rules() -> list[dict[str, object]]:
    return [
        {
            "iso_weekday": day,
            "classification": WORKING_DAY if day <= 5 else NON_WORKING_DAY,
            "scheduled_minutes": 480 if day <= 5 else 0,
        }
        for day in range(1, 8)
    ]


def request(version: int = 1) -> WorkCalendarVersionCreateRequest:
    return WorkCalendarVersionCreateRequest(
        version_number=version,
        effective_from=date(2026, 1, 1),
        effective_to=date(2026, 12, 31),
        time_zone="UTC",
        weekly_rules=weekly_rules(),
    )


def fake_uow() -> Mock:
    uow = Mock()
    uow.work_calendars.has_effective_date_overlap.return_value = False
    uow.payroll_runs.get_statuses_overlapping_dates.return_value = []
    uow.audit_events.add.return_value = None

    def add_version(value: WorkCalendarVersion) -> WorkCalendarVersion:
        return WorkCalendarVersion(
            version_number=value.version_number,
            effective_from=value.effective_from,
            effective_to=value.effective_to,
            time_zone=value.time_zone,
            created_by_user_id=value.created_by_user_id,
            weekly_rules=value.weekly_rules,
            version_id=41,
            replaces_version_id=value.replaces_version_id,
        )

    uow.work_calendars.add_version.side_effect = add_version
    return uow


def test_create_version_attributes_actor_and_audits_atomically() -> None:
    uow = fake_uow()
    response = WorkCalendarService(uow).create_version(request(), 9, "req-1")
    assert response.work_calendar_version_id == 41
    assert response.created_by_user_id == 9
    assert len(response.weekly_rules) == 7
    event = uow.audit_events.add.call_args.args[0]
    assert event.actor_user_id == 9
    assert event.action_type == "WORK_CALENDAR_VERSION_CREATED"
    uow.commit.assert_called_once()


def test_rejects_overlapping_version_without_persisting() -> None:
    uow = fake_uow()
    uow.work_calendars.has_effective_date_overlap.return_value = True
    with pytest.raises(BusinessRuleViolation, match="overlap"):
        WorkCalendarService(uow).create_version(request(), 9, None)
    uow.work_calendars.add_version.assert_not_called()
    uow.commit.assert_not_called()


@pytest.mark.parametrize("status", ["PROCESSING", "PROCESSED", "FINALIZED", "CREATED"])
def test_correction_requires_every_affected_run_failed(status: str) -> None:
    uow = fake_uow()
    version = WorkCalendarVersion(
        1, date(2026, 1, 1), date(2026, 12, 31), "UTC", 1,
        tuple(WeeklyRule(day, WORKING_DAY, 480) for day in range(1, 8)),
        version_id=2,
    )
    uow.work_calendars.get_by_id.return_value = version
    uow.work_calendars.get_override.return_value = None
    uow.payroll_runs.get_statuses_overlapping_dates.return_value = ["FAILED", status]
    command = WorkCalendarDateOverrideCreateRequest(
        override_date=date(2026, 2, 2), classification=HOLIDAY, label="Holiday"
    )
    with pytest.raises(BusinessRuleViolation, match="FAILED"):
        WorkCalendarService(uow).create_date_override(2, command, 9, None)
    uow.work_calendars.add_override.assert_not_called()
    uow.commit.assert_not_called()


def test_date_override_audits_and_commits_when_impacted_runs_failed() -> None:
    uow = fake_uow()
    version = WorkCalendarVersion(
        1, date(2026, 1, 1), date(2026, 12, 31), "UTC", 1,
        tuple(WeeklyRule(day, WORKING_DAY, 480) for day in range(1, 8)),
        version_id=2,
    )
    uow.work_calendars.get_by_id.return_value = version
    uow.work_calendars.get_override.return_value = None
    uow.payroll_runs.get_statuses_overlapping_dates.return_value = ["FAILED"]
    uow.work_calendars.add_override.side_effect = lambda value: CalendarDateOverride(
        value.work_calendar_version_id, value.override_date, value.classification,
        value.label, override_id=55,
    )
    command = WorkCalendarDateOverrideCreateRequest(
        override_date=date(2026, 2, 2), classification=HOLIDAY, label="Holiday"
    )
    response = WorkCalendarService(uow).create_date_override(2, command, 9, "req-2")
    assert response.work_calendar_date_override_id == 55
    assert response.classification == HOLIDAY
    assert uow.audit_events.add.call_args.args[0].actor_user_id == 9
    uow.commit.assert_called_once()


def test_override_rejects_missing_version() -> None:
    uow = fake_uow()
    uow.work_calendars.get_by_id.return_value = None
    command = WorkCalendarDateOverrideCreateRequest(
        override_date=date(2026, 2, 2), classification=HOLIDAY, label="Holiday"
    )
    with pytest.raises(BusinessRuleViolation, match="not found"):
        WorkCalendarService(uow).create_date_override(99, command, 9, None)
    uow.work_calendars.add_override.assert_not_called()


def test_override_rejects_date_outside_version_and_duplicate_date() -> None:
    uow = fake_uow()
    version = WorkCalendarVersion(
        1, date(2026, 1, 1), date(2026, 12, 31), "UTC", 1,
        tuple(WeeklyRule(day, WORKING_DAY, 480) for day in range(1, 8)),
        version_id=2,
    )
    uow.work_calendars.get_by_id.return_value = version
    outside = WorkCalendarDateOverrideCreateRequest(
        override_date=date(2027, 1, 1), classification=HOLIDAY, label="Holiday"
    )
    with pytest.raises(BusinessRuleViolation, match="within"):
        WorkCalendarService(uow).create_date_override(2, outside, 9, None)
    duplicate = WorkCalendarDateOverrideCreateRequest(
        override_date=date(2026, 2, 2), classification=HOLIDAY, label="Holiday"
    )
    uow.work_calendars.get_override.return_value = CalendarDateOverride(
        2, date(2026, 2, 2), HOLIDAY, "Holiday", override_id=8
    )
    with pytest.raises(BusinessRuleViolation, match="already exists"):
        WorkCalendarService(uow).create_date_override(2, duplicate, 9, None)
    uow.work_calendars.add_override.assert_not_called()


def test_classification_override_precedes_weekly_rule_and_working_count_uses_calendar() -> None:
    uow = fake_uow()
    version = WorkCalendarVersion(
        1, date(2026, 2, 1), date(2026, 2, 28), "UTC", 1,
        tuple(WeeklyRule(day, WORKING_DAY, 480) for day in range(1, 8)),
        version_id=3,
    )
    uow.work_calendars.get_applicable.return_value = version
    uow.work_calendars.get_override.side_effect = lambda _, day: (
        CalendarDateOverride(3, day, HOLIDAY, "Holiday", 1)
        if day == date(2026, 2, 2) else None
    )
    service = WorkCalendarService(uow)
    assert service.classify_date(date(2026, 2, 2)).scheduled_minutes == 0
    assert service.classify_date(date(2026, 2, 3)).time_zone == "UTC"
    assert service.working_day_count(2026, 2) == 27

