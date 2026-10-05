from decimal import Decimal

from app.domain.shared.entity import Entity
from app.domain.shared.exceptions import BusinessRuleViolation


class PayrollResult(Entity[int | None]):
    def __init__(
        self,
        payroll_result_id: int | None,
        payroll_run_id: int,
        employee_id: int,
        salary_assignment_id: int,
        gross_earnings: Decimal,
        total_deductions: Decimal,
        net_salary: Decimal,
    ) -> None:
        if min(payroll_run_id, employee_id, salary_assignment_id) <= 0:
            raise BusinessRuleViolation("Payroll reference IDs must be positive.")
        gross = Decimal(gross_earnings)
        deductions = Decimal(total_deductions)
        net = Decimal(net_salary)
        if not gross.is_finite() or not deductions.is_finite() or not net.is_finite():
            raise BusinessRuleViolation("Payroll amounts must be finite decimals.")
        if gross < 0 or deductions < 0:
            raise BusinessRuleViolation("Payroll earnings and deductions cannot be negative.")
        if net != gross - deductions:
            raise BusinessRuleViolation(
                "Net salary must equal gross earnings minus total deductions."
            )
        super().__init__(payroll_result_id)
        self.payroll_run_id = payroll_run_id
        self.employee_id = employee_id
        self.salary_assignment_id = salary_assignment_id
        self.gross_earnings = gross
        self.total_deductions = deductions
        self.net_salary = net
