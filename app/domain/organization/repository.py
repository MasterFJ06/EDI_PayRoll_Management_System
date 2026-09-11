from abc import abstractmethod

from app.domain.organization.department import Department
from app.domain.organization.designation import Designation
from app.domain.shared.repository import Repository


class DepartmentRepository(Repository[Department, int]):
    """Repository contract for department domain entities."""

    @abstractmethod
    def get_by_code(self, department_code: str) -> Department | None:
        raise NotImplementedError

    @abstractmethod
    def get_by_name(self, department_name: str) -> Department | None:
        raise NotImplementedError


class DesignationRepository(Repository[Designation, int]):
    """Repository contract for designation domain entities."""

    @abstractmethod
    def get_by_code(self, designation_code: str) -> Designation | None:
        raise NotImplementedError

    @abstractmethod
    def get_by_name(self, designation_name: str) -> Designation | None:
        raise NotImplementedError