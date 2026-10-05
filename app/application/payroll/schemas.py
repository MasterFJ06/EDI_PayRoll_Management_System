from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


PayrollRunStatus = Literal["CREATED", "PROCESSING", "FAILED", "PROCESSED", "FINALIZED"]
PayrollIssueStatus = Literal["OPEN", "RESOLVED"]
PayrollComponentType = Literal["EARNING", "DEDUCTION"]


class PayrollRunCreateRequest(BaseModel):
    payroll_year: int = Field(ge=0, le=65535)
    payroll_month: int = Field(ge=1, le=12)
    initiated_by_user_id: int = Field(gt=0)


class PayrollRunResponse(BaseModel):
    payroll_run_id: int
    payroll_year: int
    payroll_month: int
    status: PayrollRunStatus
    initiated_by_user_id: int


class PayrollResultCreateRequest(BaseModel):
    payroll_run_id: int = Field(gt=0)
    employee_id: int = Field(gt=0)
    salary_assignment_id: int = Field(gt=0)
    gross_earnings: Decimal = Field(ge=0, max_digits=15, decimal_places=2)
    total_deductions: Decimal = Field(ge=0, max_digits=15, decimal_places=2)
    net_salary: Decimal = Field(max_digits=15, decimal_places=2)


class PayrollResultResponse(BaseModel):
    payroll_result_id: int
    payroll_run_id: int
    employee_id: int
    salary_assignment_id: int
    gross_earnings: Decimal
    total_deductions: Decimal
    net_salary: Decimal


class PayrollResultComponentCreateRequest(BaseModel):
    payroll_result_id: int = Field(gt=0)
    salary_component_id: int = Field(gt=0)
    component_type: PayrollComponentType
    amount: Decimal = Field(ge=0, max_digits=15, decimal_places=2)
    calculation_order: int = Field(ge=0, le=4294967295)


class PayrollResultComponentResponse(BaseModel):
    payroll_result_component_id: int
    payroll_result_id: int
    salary_component_id: int
    component_type: PayrollComponentType
    amount: Decimal
    calculation_order: int


class PayrollProcessingIssueCreateRequest(BaseModel):
    payroll_run_id: int = Field(gt=0)
    employee_id: int | None = Field(default=None, gt=0)
    issue_code: str = Field(max_length=100)
    issue_message: str = Field(max_length=1000)
    status: PayrollIssueStatus = "OPEN"
    resolved_at: datetime | None = None


class PayrollProcessingIssueResponse(BaseModel):
    payroll_issue_id: int
    payroll_run_id: int
    employee_id: int | None
    issue_code: str
    issue_message: str
    status: PayrollIssueStatus
    resolved_at: datetime | None


class PayslipCreateRequest(BaseModel):
    payroll_result_id: int = Field(gt=0)
    payslip_number: str = Field(max_length=50)
    generated_by_user_id: int = Field(gt=0)
    document_path: str = Field(max_length=500)


class PayslipResponse(BaseModel):
    payslip_id: int
    payroll_result_id: int
    payslip_number: str
    generated_by_user_id: int
    document_path: str
