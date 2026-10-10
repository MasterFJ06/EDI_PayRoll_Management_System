from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class SalaryComponentSnapshot:
    salary_component_id: int
    component_name: str
    component_type: str
    calculation_type: str
    is_overtime_base: bool
    fixed_amount: Decimal | None
    percentage_value: Decimal | None
    base_component_id: int | None


@dataclass(frozen=True)
class SalaryRevisionSnapshot:
    salary_revision_id: int
    salary_structure_id: int
    revision_number: int
    effective_from: date
    effective_to: date | None
    components: tuple[SalaryComponentSnapshot, ...]


@dataclass(frozen=True)
class EmployeeSalaryAssignmentSnapshot:
    salary_assignment_id: int
    salary_revision_id: int
    effective_from: date
    effective_to: date | None


@dataclass(frozen=True)
class EmployeeCompensationSnapshot:
    employee_id: int
    assignment: EmployeeSalaryAssignmentSnapshot
    revision: SalaryRevisionSnapshot
