from app.domain.shared.entity import Entity
from app.domain.shared.exceptions import BusinessRuleViolation


class Department(Entity[int]):
    """Domain entity representing an organizational department."""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"

    def __init__(
        self,
        department_id: int | None,
        department_code: str,
        department_name: str,
        status: str = ACTIVE,
    ) -> None:
        normalized_code = department_code.strip()
        normalized_name = department_name.strip()
        normalized_status = status.strip().upper()

        if not normalized_code:
            raise BusinessRuleViolation(
                "Department code cannot be blank."
            )

        if not normalized_name:
            raise BusinessRuleViolation(
                "Department name cannot be blank."
            )

        if normalized_status not in {self.ACTIVE, self.INACTIVE}:
            raise BusinessRuleViolation(
                "Department status must be ACTIVE or INACTIVE."
            )

        super().__init__(department_id)

        self.department_code = normalized_code
        self.department_name = normalized_name
        self.status = normalized_status

    def activate(self) -> None:
        """Activate the department."""
        self.status = self.ACTIVE

    def deactivate(self) -> None:
        """Deactivate the department."""
        self.status = self.INACTIVE

    def rename(self, department_name: str) -> None:
        """Change the department name."""
        normalized_name = department_name.strip()

        if not normalized_name:
            raise BusinessRuleViolation(
                "Department name cannot be blank."
            )

        self.department_name = normalized_name

    def change_code(self, department_code: str) -> None:
        """Change the department code."""
        normalized_code = department_code.strip()

        if not normalized_code:
            raise BusinessRuleViolation(
                "Department code cannot be blank."
            )

        self.department_code = normalized_code