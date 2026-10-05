from abc import ABC, abstractmethod

from app.domain.compensation.employee_salary_assignment import EmployeeSalaryAssignment
from app.domain.compensation.salary_component import SalaryComponent
from app.domain.compensation.salary_revision import SalaryRevision
from app.domain.compensation.salary_revision_component import SalaryRevisionComponent
from app.domain.compensation.salary_structure import SalaryStructure


class SalaryStructureRepository(ABC):
    @abstractmethod
    def get_by_id(self, salary_structure_id: int) -> SalaryStructure | None: ...

    @abstractmethod
    def get_by_code(self, structure_code: str) -> SalaryStructure | None: ...

    @abstractmethod
    def add(self, structure: SalaryStructure) -> SalaryStructure: ...


class SalaryComponentRepository(ABC):
    @abstractmethod
    def get_by_id(self, salary_component_id: int) -> SalaryComponent | None: ...

    @abstractmethod
    def get_by_code(self, component_code: str) -> SalaryComponent | None: ...

    @abstractmethod
    def add(self, component: SalaryComponent) -> SalaryComponent: ...


class SalaryRevisionRepository(ABC):
    @abstractmethod
    def get_by_id(self, salary_revision_id: int) -> SalaryRevision | None: ...

    @abstractmethod
    def get_by_structure_and_number(
        self, salary_structure_id: int, revision_number: int
    ) -> SalaryRevision | None: ...

    @abstractmethod
    def add(self, revision: SalaryRevision) -> SalaryRevision: ...


class SalaryRevisionComponentRepository(ABC):
    @abstractmethod
    def get_by_revision_and_component(
        self, salary_revision_id: int, salary_component_id: int
    ) -> SalaryRevisionComponent | None: ...

    @abstractmethod
    def add(self, component: SalaryRevisionComponent) -> SalaryRevisionComponent: ...


class EmployeeSalaryAssignmentRepository(ABC):
    @abstractmethod
    def get_by_id(self, salary_assignment_id: int) -> EmployeeSalaryAssignment | None: ...

    @abstractmethod
    def add(self, assignment: EmployeeSalaryAssignment) -> EmployeeSalaryAssignment: ...
