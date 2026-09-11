from app.domain.shared.entity import Entity
from app.domain.shared.exceptions import BusinessRuleViolation


class Designation(Entity[int]):
    """Domain entity representing an employee designation."""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"

    def __init__(
        self,
        designation_id: int | None,
        designation_code: str,
        designation_name: str,
        status: str = ACTIVE,
    ) -> None:
        normalized_code = designation_code.strip()
        normalized_name = designation_name.strip()
        normalized_status = status.strip().upper()

        if not normalized_code:
            raise BusinessRuleViolation(
                "Designation code cannot be blank."
            )

        if not normalized_name:
            raise BusinessRuleViolation(
                "Designation name cannot be blank."
            )

        if normalized_status not in {self.ACTIVE, self.INACTIVE}:
            raise BusinessRuleViolation(
                "Designation status must be ACTIVE or INACTIVE."
            )

        super().__init__(designation_id)

        self.designation_code = normalized_code
        self.designation_name = normalized_name
        self.status = normalized_status

    def activate(self) -> None:
        """Activate the designation."""
        self.status = self.ACTIVE

    def deactivate(self) -> None:
        """Deactivate the designation."""
        self.status = self.INACTIVE

    def rename(self, designation_name: str) -> None:
        """Change the designation name."""
        normalized_name = designation_name.strip()

        if not normalized_name:
            raise BusinessRuleViolation(
                "Designation name cannot be blank."
            )

        self.designation_name = normalized_name

    def change_code(self, designation_code: str) -> None:
        """Change the designation code."""
        normalized_code = designation_code.strip()

        if not normalized_code:
            raise BusinessRuleViolation(
                "Designation code cannot be blank."
            )

        self.designation_code = normalized_code