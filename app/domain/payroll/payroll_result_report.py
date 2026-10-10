from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class PayrollResultReportRecord:
    """Bounded projection for the employee Payroll Result report."""

    payroll_result_id: int
    payroll_run_id: int
    employee_id: int
    salary_assignment_id: int
    gross_earnings: Decimal
    total_deductions: Decimal
    net_salary: Decimal
    employee_code: str | None
    employee_name: str | None
