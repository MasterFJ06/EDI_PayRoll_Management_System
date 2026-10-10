from datetime import date
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, model_validator


WeeklyClassification = Literal["WORKING_DAY", "NON_WORKING_DAY"]
OverrideClassification = Literal["WORKING_DAY", "NON_WORKING_DAY", "HOLIDAY"]


class WorkCalendarWeeklyRuleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    iso_weekday: int = Field(ge=1, le=7)
    classification: WeeklyClassification
    scheduled_minutes: int = Field(ge=0, le=480)

    @model_validator(mode="after")
    def validate_minutes(self) -> "WorkCalendarWeeklyRuleRequest":
        expected = 480 if self.classification == "WORKING_DAY" else 0
        if self.scheduled_minutes != expected:
            raise ValueError(f"{self.classification} must schedule {expected} minutes.")
        return self


class WorkCalendarVersionCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version_number: int = Field(gt=0, le=4_294_967_295)
    effective_from: date
    effective_to: date | None = None
    time_zone: str = Field(min_length=1, max_length=64)
    replaces_version_id: int | None = Field(default=None, gt=0)
    weekly_rules: list[WorkCalendarWeeklyRuleRequest] = Field(min_length=7, max_length=7)

    @model_validator(mode="after")
    def validate_version(self) -> "WorkCalendarVersionCreateRequest":
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise ValueError("effective_to must not precede effective_from.")
        weekdays = [rule.iso_weekday for rule in self.weekly_rules]
        if len(set(weekdays)) != 7:
            raise ValueError("Exactly one weekly rule is required for each ISO weekday 1–7.")
        try:
            ZoneInfo(self.time_zone)
        except (ZoneInfoNotFoundError, ValueError, TypeError) as exc:
            raise ValueError("time_zone must be a valid IANA identifier.") from exc
        return self


class WorkCalendarDateOverrideCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    override_date: date
    classification: OverrideClassification
    label: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def validate_holiday_label(self) -> "WorkCalendarDateOverrideCreateRequest":
        if self.classification == "HOLIDAY" and not (self.label or "").strip():
            raise ValueError("HOLIDAY requires a non-blank label.")
        return self


class WorkCalendarWeeklyRuleResponse(BaseModel):
    iso_weekday: int
    classification: WeeklyClassification
    scheduled_minutes: int


class WorkCalendarDateOverrideResponse(BaseModel):
    work_calendar_date_override_id: int
    work_calendar_version_id: int
    override_date: date
    classification: OverrideClassification
    label: str | None


class WorkCalendarVersionResponse(BaseModel):
    work_calendar_version_id: int
    version_number: int
    effective_from: date
    effective_to: date | None
    time_zone: str
    created_by_user_id: int
    replaces_version_id: int | None
    weekly_rules: list[WorkCalendarWeeklyRuleResponse]
    date_overrides: list[WorkCalendarDateOverrideResponse]


class WorkCalendarDayResponse(BaseModel):
    work_calendar_version_id: int
    calendar_version_number: int
    calendar_date: date
    time_zone: str
    classification: OverrideClassification
    scheduled_minutes: int
    label: str | None
