from abc import ABC, abstractmethod
from datetime import date

from app.domain.workforce.overtime import OvertimePolicyVersion


class OvertimePolicyRepository(ABC):
    @abstractmethod
    def get_by_id(self, policy_id: int) -> OvertimePolicyVersion | None: ...

    @abstractmethod
    def get_applicable(self, day: date) -> OvertimePolicyVersion | None: ...

    @abstractmethod
    def has_effective_date_overlap(self, start: date, end: date | None) -> bool: ...

    @abstractmethod
    def add(self, policy: OvertimePolicyVersion) -> OvertimePolicyVersion: ...
