from abc import ABC, abstractmethod
from datetime import date

from app.domain.organization.work_calendar import (
    CalendarDateOverride,
    WorkCalendarVersion,
)


class WorkCalendarRepository(ABC):
    @abstractmethod
    def get_by_id(self, version_id: int) -> WorkCalendarVersion | None: ...

    @abstractmethod
    def get_applicable(self, day: date) -> WorkCalendarVersion | None: ...

    @abstractmethod
    def has_effective_date_overlap(
        self, effective_from: date, effective_to: date | None
    ) -> bool: ...

    @abstractmethod
    def add_version(self, version: WorkCalendarVersion) -> WorkCalendarVersion: ...

    @abstractmethod
    def get_override(
        self, version_id: int, override_date: date
    ) -> CalendarDateOverride | None: ...

    @abstractmethod
    def get_overrides(self, version_id: int) -> list[CalendarDateOverride]: ...

    @abstractmethod
    def add_override(
        self, override: CalendarDateOverride
    ) -> CalendarDateOverride: ...
