from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class PayrollResultComponentReportRecord:
    """Persisted component row with current labels for the payroll report."""

    payroll_result_component_id: int
    payroll_run_id: int
    payroll_result_id: int
    employee_id: int
    employee_code: str | None
    employee_name: str | None
    salary_component_id: int
    salary_component_definition_exists: bool
    component_code: str | None
    component_name: str | None
    component_type: str
    amount: Decimal
    calculation_order: int
