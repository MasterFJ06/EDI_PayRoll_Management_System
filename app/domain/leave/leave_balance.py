from decimal import Decimal

from app.domain.shared.entity import Entity
from app.domain.shared.exceptions import BusinessRuleViolation


class LeaveBalance(Entity[int | None]):
    def __init__(
        self,
        leave_balance_id: int | None,
        employee_id: int,
        leave_type_id: int,
        balance_year: int,
        allocated_days: Decimal,
        used_days: Decimal,
    ) -> None:
        if employee_id <= 0 or leave_type_id <= 0:
            raise BusinessRuleViolation("Employee and leave type IDs must be positive.")
        if not 0 <= balance_year <= 65535:
            raise BusinessRuleViolation("Balance year must fit an unsigned small integer.")
        allocated = Decimal(allocated_days)
        used = Decimal(used_days)
        if allocated < 0:
            raise BusinessRuleViolation("Allocated leave days cannot be negative.")
        if used < 0:
            raise BusinessRuleViolation("Used leave days cannot be negative.")
        if used > allocated:
            raise BusinessRuleViolation("Used leave days cannot exceed allocated days.")
        super().__init__(leave_balance_id)
        self.employee_id = employee_id
        self.leave_type_id = leave_type_id
        self.balance_year = balance_year
        self.allocated_days = allocated
        self.used_days = used
