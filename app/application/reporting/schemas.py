from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict


class FinalizedPayrollSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    payroll_run_id: int
    payroll_year: int
    payroll_month: int
    status: Literal["FINALIZED"]
    initiated_by_user_id: int
    employee_result_count: int
    total_gross_pay: Decimal
    total_deductions: Decimal
    total_net_pay: Decimal
