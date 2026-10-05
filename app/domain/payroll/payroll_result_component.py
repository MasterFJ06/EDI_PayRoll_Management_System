from decimal import Decimal

from app.domain.shared.entity import Entity
from app.domain.shared.exceptions import BusinessRuleViolation


class PayrollResultComponent(Entity[int | None]):
    EARNING = "EARNING"
    DEDUCTION = "DEDUCTION"
    VALID_TYPES = {EARNING, DEDUCTION}

    def __init__(
        self,
        payroll_result_component_id: int | None,
        payroll_result_id: int,
        salary_component_id: int,
        component_type: str,
        amount: Decimal,
        calculation_order: int,
    ) -> None:
        if payroll_result_id <= 0 or salary_component_id <= 0:
            raise BusinessRuleViolation("Payroll result and salary component IDs must be positive.")
        normalized_type = component_type.strip().upper()
        if normalized_type not in self.VALID_TYPES:
            raise BusinessRuleViolation("Payroll component type must be EARNING or DEDUCTION.")
        value = Decimal(amount)
        if not value.is_finite():
            raise BusinessRuleViolation("Payroll component amount must be a finite decimal.")
        if value < 0:
            raise BusinessRuleViolation("Payroll component amount cannot be negative.")
        if not 0 <= calculation_order <= 4294967295:
            raise BusinessRuleViolation("Calculation order must fit INT UNSIGNED.")
        super().__init__(payroll_result_component_id)
        self.payroll_result_id = payroll_result_id
        self.salary_component_id = salary_component_id
        self.component_type = normalized_type
        self.amount = value
        self.calculation_order = calculation_order
