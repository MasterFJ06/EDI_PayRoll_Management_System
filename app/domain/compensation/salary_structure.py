from app.domain.shared.entity import Entity
from app.domain.shared.exceptions import BusinessRuleViolation


class SalaryStructure(Entity[int]):
    """Domain entity representing a salary structure."""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"

    def __init__(
        self,
        salary_structure_id: int | None,
        structure_code: str,
        structure_name: str,
        description: str | None = None,
        status: str = ACTIVE,
    ) -> None:
        normalized_code = structure_code.strip()
        normalized_name = structure_name.strip()
        normalized_status = status.strip().upper()

        if not normalized_code:
            raise BusinessRuleViolation("Salary structure code cannot be blank.")
        if not normalized_name:
            raise BusinessRuleViolation("Salary structure name cannot be blank.")
        if normalized_status not in {self.ACTIVE, self.INACTIVE}:
            raise BusinessRuleViolation("Salary structure status must be ACTIVE or INACTIVE.")

        super().__init__(salary_structure_id)

        self.structure_code = normalized_code
        self.structure_name = normalized_name
        self.description = description
        self.status = normalized_status

    def activate(self) -> None:
        self.status = self.ACTIVE

    def deactivate(self) -> None:
        self.status = self.INACTIVE
