from dataclasses import dataclass
from datetime import date
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.domain.shared.exceptions import BusinessRuleViolation


WORKING_DAY = "WORKING_DAY"
NON_WORKING_DAY = "NON_WORKING_DAY"
HOLIDAY = "HOLIDAY"
WEEKLY_CLASSIFICATIONS = {WORKING_DAY, NON_WORKING_DAY}
OVERRIDE_CLASSIFICATIONS = {*WEEKLY_CLASSIFICATIONS, HOLIDAY}


@dataclass(frozen=True)
class WeeklyRule:
    iso_weekday: int
    classification: str
    scheduled_minutes: int

    def __post_init__(self) -> None:
        if not 1 <= self.iso_weekday <= 7:
            raise BusinessRuleViolation("ISO weekday must be between 1 and 7.")
        classification = self.classification.strip().upper()
        if classification not in WEEKLY_CLASSIFICATIONS:
            raise BusinessRuleViolation("Weekly classification is invalid.")
        expected_minutes = 480 if classification == WORKING_DAY else 0
        if self.scheduled_minutes != expected_minutes:
            raise BusinessRuleViolation(
                f"{classification} must schedule exactly {expected_minutes} minutes."
            )
        object.__setattr__(self, "classification", classification)


@dataclass(frozen=True)
class CalendarDateOverride:
    work_calendar_version_id: int
    override_date: date
    classification: str
    label: str | None = None
    override_id: int | None = None

    def __post_init__(self) -> None:
        classification = self.classification.strip().upper()
        if classification not in OVERRIDE_CLASSIFICATIONS:
            raise BusinessRuleViolation("Date override classification is invalid.")
        label = self.label.strip() if self.label is not None else None
        if classification == HOLIDAY and not label:
            raise BusinessRuleViolation("A holiday override requires a label.")
        object.__setattr__(self, "classification", classification)
        object.__setattr__(self, "label", label)


@dataclass(frozen=True)
class WorkCalendarVersion:
    version_number: int
    effective_from: date
    effective_to: date | None
    time_zone: str
    created_by_user_id: int
    weekly_rules: tuple[WeeklyRule, ...]
    version_id: int | None = None
    replaces_version_id: int | None = None

    def __post_init__(self) -> None:
        if self.version_number <= 0:
            raise BusinessRuleViolation("Calendar version number must be positive.")
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise BusinessRuleViolation("Calendar effective_to must not precede effective_from.")
        if self.created_by_user_id <= 0:
            raise BusinessRuleViolation("Calendar creator user ID must be positive.")
        if self.replaces_version_id is not None and self.replaces_version_id <= 0:
            raise BusinessRuleViolation("Replacement version ID must be positive.")
        try:
            ZoneInfo(self.time_zone)
        except (ZoneInfoNotFoundError, ValueError, TypeError) as exc:
            raise BusinessRuleViolation("Calendar time zone must be a valid IANA identifier.") from exc
        weekdays = [rule.iso_weekday for rule in self.weekly_rules]
        if len(weekdays) != 7 or set(weekdays) != set(range(1, 8)):
            raise BusinessRuleViolation(
                "A calendar version must contain exactly one rule for each ISO weekday 1–7."
            )

    def applies_on(self, day: date) -> bool:
        return self.effective_from <= day and (
            self.effective_to is None or day <= self.effective_to
        )

    def rule_for(self, day: date) -> WeeklyRule:
        return next(rule for rule in self.weekly_rules if rule.iso_weekday == day.isoweekday())


@dataclass(frozen=True)
class CalendarDay:
    work_calendar_version_id: int
    calendar_version_number: int
    calendar_date: date
    time_zone: str
    classification: str
    scheduled_minutes: int
    label: str | None = None
