from calendar import monthrange
from datetime import date

from sqlalchemy.exc import IntegrityError

from app.application.common.unit_of_work import UnitOfWork
from app.application.organization.work_calendar_schemas import (
    WorkCalendarDateOverrideCreateRequest,
    WorkCalendarDateOverrideResponse,
    WorkCalendarDayResponse,
    WorkCalendarVersionCreateRequest,
    WorkCalendarVersionResponse,
    WorkCalendarWeeklyRuleResponse,
)
from app.domain.organization.work_calendar import (
    HOLIDAY,
    NON_WORKING_DAY,
    WORKING_DAY,
    CalendarDateOverride,
    CalendarDay,
    WeeklyRule,
    WorkCalendarVersion,
)
from app.domain.shared.exceptions import BusinessRuleViolation
from app.infrastructure.persistence.models.audit_event import AuditEventModel
from app.infrastructure.persistence.models.audit_event_change import (
    AuditEventChangeModel,
)


class WorkCalendarService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def create_version(
        self,
        request: WorkCalendarVersionCreateRequest,
        actor_user_id: int,
        correlation_id: str | None,
    ) -> WorkCalendarVersionResponse:
        rules = tuple(
            WeeklyRule(
                iso_weekday=rule.iso_weekday,
                classification=rule.classification,
                scheduled_minutes=rule.scheduled_minutes,
            )
            for rule in request.weekly_rules
        )
        version = WorkCalendarVersion(
            version_number=request.version_number,
            effective_from=request.effective_from,
            effective_to=request.effective_to,
            time_zone=request.time_zone,
            created_by_user_id=actor_user_id,
            replaces_version_id=request.replaces_version_id,
            weekly_rules=rules,
        )
        if self.uow.work_calendars.has_effective_date_overlap(
            version.effective_from, version.effective_to
        ):
            raise BusinessRuleViolation(
                "Work Calendar effective dates overlap an existing version."
            )
        if version.replaces_version_id is not None:
            replaced = self.uow.work_calendars.get_by_id(version.replaces_version_id)
            if replaced is None:
                raise BusinessRuleViolation("Replacement Work Calendar version was not found.")
            self._require_failed_payroll_runs(
                version.effective_from, version.effective_to
            )

        try:
            created = self.uow.work_calendars.add_version(version)
            self.uow.audit_events.add(
                AuditEventModel(
                    actor_user_id=actor_user_id,
                    action_type=(
                        "WORK_CALENDAR_VERSION_REPLACED"
                        if version.replaces_version_id is not None
                        else "WORK_CALENDAR_VERSION_CREATED"
                    ),
                    resource_type="WORK_CALENDAR_VERSION",
                    resource_id=created.version_id,
                    correlation_id=correlation_id,
                ),
                [
                    AuditEventChangeModel(
                        field_name="version_number",
                        old_value=None,
                        new_value=str(created.version_number),
                    ),
                    AuditEventChangeModel(
                        field_name="effective_period",
                        old_value=None,
                        new_value=self._period_text(
                            created.effective_from, created.effective_to
                        ),
                    ),
                    AuditEventChangeModel(
                        field_name="time_zone",
                        old_value=None,
                        new_value=created.time_zone,
                    ),
                    AuditEventChangeModel(
                        field_name="replaces_version_id",
                        old_value=None,
                        new_value=(
                            str(created.replaces_version_id)
                            if created.replaces_version_id is not None
                            else None
                        ),
                    ),
                ],
            )
            self.uow.commit()
        except IntegrityError as exc:
            self.uow.rollback()
            raise BusinessRuleViolation(
                "Work Calendar version number or weekly weekday already exists."
            ) from exc
        return self._version_response(created, [])

    def get_version(self, version_id: int) -> WorkCalendarVersionResponse | None:
        version = self.uow.work_calendars.get_by_id(version_id)
        if version is None:
            return None
        overrides = self.uow.work_calendars.get_overrides(version_id)
        return self._version_response(version, overrides)

    def create_date_override(
        self,
        version_id: int,
        request: WorkCalendarDateOverrideCreateRequest,
        actor_user_id: int,
        correlation_id: str | None,
    ) -> WorkCalendarDateOverrideResponse:
        version = self.uow.work_calendars.get_by_id(version_id)
        if version is None:
            raise BusinessRuleViolation("Work Calendar version was not found.")
        if not version.applies_on(request.override_date):
            raise BusinessRuleViolation(
                "Date override must be within the Work Calendar version's effective period."
            )
        if self.uow.work_calendars.get_override(version_id, request.override_date):
            raise BusinessRuleViolation(
                "A date override already exists for this Work Calendar date."
            )
        override = CalendarDateOverride(
            work_calendar_version_id=version_id,
            override_date=request.override_date,
            classification=request.classification,
            label=request.label,
        )
        self._require_failed_payroll_runs(request.override_date, request.override_date)
        try:
            created = self.uow.work_calendars.add_override(override)
            self.uow.audit_events.add(
                AuditEventModel(
                    actor_user_id=actor_user_id,
                    action_type="WORK_CALENDAR_DATE_OVERRIDE_CREATED",
                    resource_type="WORK_CALENDAR_VERSION",
                    resource_id=version_id,
                    correlation_id=correlation_id,
                ),
                [
                    AuditEventChangeModel(
                        field_name="override_date",
                        old_value=None,
                        new_value=created.override_date.isoformat(),
                    ),
                    AuditEventChangeModel(
                        field_name="classification",
                        old_value=None,
                        new_value=created.classification,
                    ),
                    AuditEventChangeModel(
                        field_name="label",
                        old_value=None,
                        new_value=created.label,
                    ),
                ],
            )
            self.uow.commit()
        except IntegrityError as exc:
            self.uow.rollback()
            raise BusinessRuleViolation(
                "A date override already exists for this Work Calendar date."
            ) from exc
        return self._override_response(created)

    def classify_date(self, day: date) -> WorkCalendarDayResponse:
        version = self.uow.work_calendars.get_applicable(day)
        if version is None or version.version_id is None:
            raise BusinessRuleViolation("No Work Calendar version applies to this date.")
        override = self.uow.work_calendars.get_override(version.version_id, day)
        if override is not None:
            classification = override.classification
            label = override.label
            minutes = 480 if classification == WORKING_DAY else 0
        else:
            rule = version.rule_for(day)
            classification = rule.classification
            label = None
            minutes = rule.scheduled_minutes
        result = CalendarDay(
            work_calendar_version_id=version.version_id,
            calendar_version_number=version.version_number,
            calendar_date=day,
            time_zone=version.time_zone,
            classification=classification,
            scheduled_minutes=minutes,
            label=label,
        )
        return WorkCalendarDayResponse.model_validate(result.__dict__)

    def working_day_count(self, year: int, month: int) -> int:
        if not 1 <= month <= 12:
            raise BusinessRuleViolation("Month must be between 1 and 12.")
        day_count = monthrange(year, month)[1]
        return sum(
            self.classify_date(date(year, month, day)).classification == WORKING_DAY
            for day in range(1, day_count + 1)
        )

    def _require_failed_payroll_runs(
        self, start_date: date, end_date: date | None
    ) -> None:
        statuses = self.uow.payroll_runs.get_statuses_overlapping_dates(
            start_date, end_date
        )
        if any(status != "FAILED" for status in statuses):
            raise BusinessRuleViolation(
                "Work Calendar correction is allowed only when every affected Payroll Run is FAILED."
            )

    @classmethod
    def _version_response(
        cls,
        version: WorkCalendarVersion,
        overrides: list[CalendarDateOverride],
    ) -> WorkCalendarVersionResponse:
        if version.version_id is None:
            raise RuntimeError("Persisted Work Calendar version has no identifier.")
        return WorkCalendarVersionResponse(
            work_calendar_version_id=version.version_id,
            version_number=version.version_number,
            effective_from=version.effective_from,
            effective_to=version.effective_to,
            time_zone=version.time_zone,
            created_by_user_id=version.created_by_user_id,
            replaces_version_id=version.replaces_version_id,
            weekly_rules=[
                WorkCalendarWeeklyRuleResponse(
                    iso_weekday=rule.iso_weekday,
                    classification=rule.classification,
                    scheduled_minutes=rule.scheduled_minutes,
                )
                for rule in version.weekly_rules
            ],
            date_overrides=[cls._override_response(item) for item in overrides],
        )

    @staticmethod
    def _override_response(
        override: CalendarDateOverride,
    ) -> WorkCalendarDateOverrideResponse:
        if override.override_id is None:
            raise RuntimeError("Persisted Work Calendar override has no identifier.")
        return WorkCalendarDateOverrideResponse(
            work_calendar_date_override_id=override.override_id,
            work_calendar_version_id=override.work_calendar_version_id,
            override_date=override.override_date,
            classification=override.classification,
            label=override.label,
        )

    @staticmethod
    def _period_text(start: date, end: date | None) -> str:
        return f"{start.isoformat()}..{end.isoformat() if end else 'open'}"
