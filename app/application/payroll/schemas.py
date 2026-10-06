from datetime import date, datetime
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field


class ProcessPayrollRequest(BaseModel):
    payrollMonth: str | None = Field(None, description="Month in YYYY-MM format")
    payroll_month: str | None = None

    def get_month_str(self) -> str:
        return self.payrollMonth or self.payroll_month or datetime.utcnow().strftime("%Y-%m")


class ValidatePayrollRequest(BaseModel):
    payrollMonth: str | None = None
    payroll_month: str | None = None

    def get_month_str(self) -> str:
        return self.payrollMonth or self.payroll_month or datetime.utcnow().strftime("%Y-%m")


class PayrollRecordResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: str
    payrollMonth: str = Field(alias="payroll_month")
    employeeId: str = Field(alias="employee_id")
    basicSalary: float = Field(alias="basic_salary")
    allowances: float = 0.0
    overtime: float = 0.0
    leaveDeductions: float = Field(default=0.0, alias="leave_deductions")
    tax: float = 0.0
    otherDeductions: float = Field(default=0.0, alias="other_deductions")
    grossSalary: float = Field(alias="gross_salary")
    totalDeductions: float = Field(alias="total_deductions")
    netSalary: float = Field(alias="net_salary")
    status: Literal["Draft", "Validated", "Processed", "Approved", "Paid"] = "Draft"
    generatedDate: str = Field(alias="generated_date")
    generatedBy: str = Field(alias="generated_by")


class PayrollValidationIssueResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: str
    employeeId: str = Field(alias="employee_id")
    validationType: str = Field(alias="validation_type")
    status: Literal["Open", "Resolved"] = "Open"
    message: str
    severity: Literal["Information", "Warning", "Error", "Critical"] = "Warning"
    timestamp: str
    validatedBy: str = Field(alias="validated_by")


class ResolveValidationIssueRequest(BaseModel):
    status: Literal["Open", "Resolved"] = "Resolved"


class PayslipResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: str
    payrollId: str = Field(alias="payroll_id")
    employeeId: str = Field(alias="employee_id")
    payrollMonth: str = Field(alias="payroll_month")
    basicSalary: float = Field(alias="basic_salary")
    allowances: float = 0.0
    deductions: float = 0.0
    grossSalary: float = Field(alias="gross_salary")
    netSalary: float = Field(alias="net_salary")
    generatedDate: str = Field(alias="generated_date")
    digitalSignature: str = Field(default="Payroll Administrator", alias="digital_signature")
    status: Literal["Generated", "Sent", "Downloaded"] = "Generated"


class CreatePayslipRequest(BaseModel):
    payrollId: str | None = None
    employeeId: str
    payrollMonth: str
    basicSalary: float
    allowances: float = 0.0
    deductions: float = 0.0
    grossSalary: float
    netSalary: float
    digitalSignature: str = "Payroll Administrator"
    status: str = "Generated"


class DeductionResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: str
    employeeId: str = Field(alias="employee_id")
    payrollId: str = Field(alias="payroll_id")
    type: Literal["PF", "ESI", "Professional Tax", "Income Tax", "Insurance", "Loan", "Other"]
    calculationMethod: Literal["Percentage", "Flat", "Slab"] = Field(alias="calculation_method")
    amount: float
    ruleApplied: str = Field(alias="rule_applied")
    effectiveDate: str = Field(alias="effective_date")
    status: Literal["Active", "Inactive"] = "Active"


class TaxRuleResponse(BaseModel):
    id: str
    rule_name: str
    regime: str
    slab_details: str
    applicable_year: str
    is_active: bool = True
