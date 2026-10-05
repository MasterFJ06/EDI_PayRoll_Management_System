from datetime import date

from app.domain.shared.entity import Entity
from app.domain.shared.exceptions import BusinessRuleViolation


class EmployeeSalaryAssignment(Entity[int | None]):
    def __init__(
        self,
        salary_assignment_id: int | None,
        employee_id: int,
        salary_revision_id: int,
        effective_from: date,
        effective_to: date | None = None,
    ) -> None:
        if employee_id <= 0 or salary_revision_id <= 0:
            raise BusinessRuleViolation("Employee and salary revision IDs must be positive.")
        if effective_to is not None and effective_to < effective_from:
            raise BusinessRuleViolation("Salary assignment end date cannot precede its start date.")
        super().__init__(salary_assignment_id)
        self.employee_id = employee_id
        self.salary_revision_id = salary_revision_id
        self.effective_from = effective_from
        self.effective_to = effective_to
