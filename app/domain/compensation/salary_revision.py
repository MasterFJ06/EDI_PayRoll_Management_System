from datetime import date

from app.domain.shared.entity import Entity
from app.domain.shared.exceptions import BusinessRuleViolation


class SalaryRevision(Entity[int | None]):
    def __init__(
        self,
        salary_revision_id: int | None,
        salary_structure_id: int,
        revision_number: int,
        effective_from: date,
        effective_to: date | None = None,
    ) -> None:
        if salary_structure_id <= 0:
            raise BusinessRuleViolation("Salary structure ID must be positive.")
        if not 0 <= revision_number <= 4_294_967_295:
            raise BusinessRuleViolation("Revision number must fit an unsigned integer.")
        if effective_to is not None and effective_to < effective_from:
            raise BusinessRuleViolation("Salary revision end date cannot precede its start date.")
        super().__init__(salary_revision_id)
        self.salary_structure_id = salary_structure_id
        self.revision_number = revision_number
        self.effective_from = effective_from
        self.effective_to = effective_to
