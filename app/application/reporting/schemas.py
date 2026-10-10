from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


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


class EmployeePayrollResultReportRow(BaseModel):
    payroll_result_id: int
    payroll_run_id: int
    employee_id: int
    salary_assignment_id: int
    gross_earnings: Decimal
    total_deductions: Decimal
    net_salary: Decimal
    employee_code: str | None
    employee_name: str | None


class PayrollResultsReportPagination(BaseModel):
    limit: int = Field(ge=1, le=100)
    has_more: bool
    next_cursor: str | None


class EmployeePayrollResultReportPage(BaseModel):
    payroll_run_id: int
    results: list[EmployeePayrollResultReportRow]
    pagination: PayrollResultsReportPagination


class EmployeeReportRow(BaseModel):
    employee_id: int
    employee_code: str
    first_name: str
    last_name: str
    department_id: int
    department_name: str | None
    designation_id: int
    designation_name: str | None
    joining_date: date
    employment_end_date: date | None
    employment_status: Literal["ACTIVE", "INACTIVE", "TERMINATED"]


class EmployeeReportPagination(BaseModel):
    limit: int = Field(ge=1, le=100)
    has_more: bool
    next_cursor: str | None


class EmployeeReportPage(BaseModel):
    employees: list[EmployeeReportRow]
    pagination: EmployeeReportPagination
