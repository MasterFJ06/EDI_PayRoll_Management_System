from datetime import date

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.domain.organization.work_calendar import (
    CalendarDateOverride,
    WeeklyRule,
    WorkCalendarVersion,
)
from app.domain.shared.exceptions import InvalidDomainState
from app.domain.organization.work_calendar_repository import (
    WorkCalendarRepository as WorkCalendarRepositoryContract,
)
from app.infrastructure.persistence.models.work_calendar_date_override import (
    WorkCalendarDateOverrideModel,
)
from app.infrastructure.persistence.models.work_calendar_version import (
    WorkCalendarVersionModel,
)
from app.infrastructure.persistence.models.work_calendar_weekly_rule import (
    WorkCalendarWeeklyRuleModel,
)


class SQLAlchemyWorkCalendarRepository(WorkCalendarRepositoryContract):
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, version_id: int) -> WorkCalendarVersion | None:
        model = self.session.get(WorkCalendarVersionModel, version_id)
        return self._to_version(model) if model is not None else None

    def get_applicable(self, day: date) -> WorkCalendarVersion | None:
        statement = select(WorkCalendarVersionModel).where(
            WorkCalendarVersionModel.effective_from <= day,
            or_(
                WorkCalendarVersionModel.effective_to.is_(None),
                WorkCalendarVersionModel.effective_to >= day,
            ),
        )
        models = list(self.session.scalars(statement))
        if len(models) > 1:
            raise InvalidDomainState("Overlapping Work Calendar versions are persisted.")
        return self._to_version(models[0]) if models else None

    def has_effective_date_overlap(
        self, effective_from: date, effective_to: date | None
    ) -> bool:
        conditions = [
            or_(
                WorkCalendarVersionModel.effective_to.is_(None),
                WorkCalendarVersionModel.effective_to >= effective_from,
            )
        ]
        if effective_to is not None:
            conditions.append(WorkCalendarVersionModel.effective_from <= effective_to)
        return self.session.scalar(
            select(WorkCalendarVersionModel.work_calendar_version_id)
            .where(and_(*conditions))
            .limit(1)
        ) is not None

    def add_version(self, version: WorkCalendarVersion) -> WorkCalendarVersion:
        model = WorkCalendarVersionModel(
            version_number=version.version_number,
            effective_from=version.effective_from,
            effective_to=version.effective_to,
            time_zone=version.time_zone,
            created_by_user_id=version.created_by_user_id,
            replaces_version_id=version.replaces_version_id,
        )
        self.session.add(model)
        self.session.flush()
        self.session.add_all(
            [
                WorkCalendarWeeklyRuleModel(
                    work_calendar_version_id=model.work_calendar_version_id,
                    iso_weekday=rule.iso_weekday,
                    classification=rule.classification,
                    scheduled_minutes=rule.scheduled_minutes,
                )
                for rule in version.weekly_rules
            ]
        )
        self.session.flush()
        return self._to_version(model)

    def get_override(
        self, version_id: int, override_date: date
    ) -> CalendarDateOverride | None:
        model = self.session.scalar(
            select(WorkCalendarDateOverrideModel).where(
                WorkCalendarDateOverrideModel.work_calendar_version_id == version_id,
                WorkCalendarDateOverrideModel.override_date == override_date,
            )
        )
        return self._to_override(model) if model is not None else None

    def get_overrides(self, version_id: int) -> list[CalendarDateOverride]:
        models = self.session.scalars(
            select(WorkCalendarDateOverrideModel)
            .where(WorkCalendarDateOverrideModel.work_calendar_version_id == version_id)
            .order_by(WorkCalendarDateOverrideModel.override_date)
        )
        return [self._to_override(model) for model in models]

    def add_override(
        self, override: CalendarDateOverride
    ) -> CalendarDateOverride:
        model = WorkCalendarDateOverrideModel(
            work_calendar_version_id=override.work_calendar_version_id,
            override_date=override.override_date,
            classification=override.classification,
            label=override.label,
        )
        self.session.add(model)
        self.session.flush()
        return self._to_override(model)

    def _to_version(
        self, model: WorkCalendarVersionModel
    ) -> WorkCalendarVersion:
        rows = self.session.scalars(
            select(WorkCalendarWeeklyRuleModel)
            .where(
                WorkCalendarWeeklyRuleModel.work_calendar_version_id
                == model.work_calendar_version_id
            )
            .order_by(WorkCalendarWeeklyRuleModel.iso_weekday)
        )
        rules = tuple(
            WeeklyRule(
                iso_weekday=row.iso_weekday,
                classification=row.classification,
                scheduled_minutes=row.scheduled_minutes,
            )
            for row in rows
        )
        return WorkCalendarVersion(
            version_id=model.work_calendar_version_id,
            version_number=model.version_number,
            effective_from=model.effective_from,
            effective_to=model.effective_to,
            time_zone=model.time_zone,
            created_by_user_id=model.created_by_user_id,
            replaces_version_id=model.replaces_version_id,
            weekly_rules=rules,
        )

    @staticmethod
    def _to_override(model: WorkCalendarDateOverrideModel) -> CalendarDateOverride:
        return CalendarDateOverride(
            override_id=model.work_calendar_date_override_id,
            work_calendar_version_id=model.work_calendar_version_id,
            override_date=model.override_date,
            classification=model.classification,
            label=model.label,
        )
