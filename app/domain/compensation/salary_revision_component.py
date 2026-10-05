from decimal import Decimal

from app.domain.shared.entity import Entity
from app.domain.shared.exceptions import BusinessRuleViolation


class SalaryRevisionComponent(Entity[tuple[int, int]]):
    FIXED = "FIXED"
    PERCENTAGE = "PERCENTAGE"
    VALID_CALCULATION_TYPES = {FIXED, PERCENTAGE}

    def __init__(
        self,
        salary_revision_id: int,
        salary_component_id: int,
        calculation_type: str,
        fixed_amount: Decimal | None = None,
        percentage_value: Decimal | None = None,
        base_component_id: int | None = None,
    ) -> None:
        if salary_revision_id <= 0 or salary_component_id <= 0:
            raise BusinessRuleViolation("Salary revision and component IDs must be positive.")
        normalized_type = calculation_type.strip().upper()
        if normalized_type not in self.VALID_CALCULATION_TYPES:
            raise BusinessRuleViolation("Calculation type must be FIXED or PERCENTAGE.")
        amount = Decimal(fixed_amount) if fixed_amount is not None else None
        percentage = Decimal(percentage_value) if percentage_value is not None else None
        if normalized_type == self.FIXED:
            valid = amount is not None and amount >= 0 and percentage is None and base_component_id is None
        else:
            valid = amount is None and percentage is not None and percentage >= 0 and base_component_id is not None
        if not valid:
            raise BusinessRuleViolation("Salary revision component values do not match its calculation type.")
        if base_component_id is not None and base_component_id <= 0:
            raise BusinessRuleViolation("Base component ID must be positive.")
        if base_component_id == salary_component_id:
            raise BusinessRuleViolation("A salary component cannot be its own base component.")
        super().__init__((salary_revision_id, salary_component_id))
        self.salary_revision_id = salary_revision_id
        self.salary_component_id = salary_component_id
        self.calculation_type = normalized_type
        self.fixed_amount = amount
        self.percentage_value = percentage
        self.base_component_id = base_component_id
