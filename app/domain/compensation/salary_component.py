from app.domain.shared.entity import Entity
from app.domain.shared.exceptions import BusinessRuleViolation


class SalaryComponent(Entity[int | None]):
    EARNING = "EARNING"
    DEDUCTION = "DEDUCTION"
    VALID_TYPES = {EARNING, DEDUCTION}
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    VALID_STATUSES = {ACTIVE, INACTIVE}

    def __init__(
        self,
        salary_component_id: int | None,
        component_code: str,
        component_name: str,
        component_type: str,
        status: str = ACTIVE,
    ) -> None:
        code = component_code.strip()
        name = component_name.strip()
        normalized_type = component_type.strip().upper()
        normalized_status = status.strip().upper()
        if not code or len(code) > 30:
            raise BusinessRuleViolation("Salary component code must be between 1 and 30 characters.")
        if not name or len(name) > 100:
            raise BusinessRuleViolation("Salary component name must be between 1 and 100 characters.")
        if normalized_type not in self.VALID_TYPES:
            raise BusinessRuleViolation("Salary component type must be EARNING or DEDUCTION.")
        if normalized_status not in self.VALID_STATUSES:
            raise BusinessRuleViolation("Salary component status must be ACTIVE or INACTIVE.")
        super().__init__(salary_component_id)
        self.component_code = code
        self.component_name = name
        self.component_type = normalized_type
        self.status = normalized_status

    def activate(self) -> None:
        self.status = self.ACTIVE

    def deactivate(self) -> None:
        self.status = self.INACTIVE
