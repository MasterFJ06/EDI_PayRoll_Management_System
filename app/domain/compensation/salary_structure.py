from app.domain.shared.entity import Entity
from app.domain.shared.exceptions import BusinessRuleViolation


class SalaryStructure(Entity[int | None]):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    VALID_STATUSES = {ACTIVE, INACTIVE}

    def __init__(
        self,
        salary_structure_id: int | None,
        structure_code: str,
        structure_name: str,
        description: str | None = None,
        status: str = ACTIVE,
    ) -> None:
        code = structure_code.strip()
        name = structure_name.strip()
        normalized_status = status.strip().upper()
        if not code or len(code) > 30:
            raise BusinessRuleViolation("Salary structure code must be between 1 and 30 characters.")
        if not name or len(name) > 100:
            raise BusinessRuleViolation("Salary structure name must be between 1 and 100 characters.")
        normalized_description = description.strip() if description is not None else None
        if normalized_description is not None and len(normalized_description) > 500:
            raise BusinessRuleViolation("Salary structure description cannot exceed 500 characters.")
        if normalized_status not in self.VALID_STATUSES:
            raise BusinessRuleViolation("Salary structure status must be ACTIVE or INACTIVE.")
        super().__init__(salary_structure_id)
        self.structure_code = code
        self.structure_name = name
        self.description = normalized_description
        self.status = normalized_status

    def activate(self) -> None:
        self.status = self.ACTIVE

    def deactivate(self) -> None:
        self.status = self.INACTIVE
