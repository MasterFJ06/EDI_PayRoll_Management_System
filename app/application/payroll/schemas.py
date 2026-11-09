from datetime import date, datetime
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


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
    payrollMonth: str = ""
    employeeId: str = ""
    basicSalary: float = 0.0
    allowances: float = 0.0
    overtime: float = 0.0
    leaveDeductions: float = 0.0
    tax: float = 0.0
    otherDeductions: float = 0.0
    grossSalary: float = 0.0
    totalDeductions: float = 0.0
    netSalary: float = 0.0
    status: Literal["Draft", "Validated", "Processed", "Approved", "Paid"] = "Draft"
    generatedDate: str = ""
    generatedBy: str = ""

    # snake_case compatibility
    payroll_month: str = ""
    employee_id: str = ""
    basic_salary: float = 0.0
    leave_deductions: float = 0.0
    other_deductions: float = 0.0
    gross_salary: float = 0.0
    total_deductions: float = 0.0
    net_salary: float = 0.0
    generated_date: str = ""
    generated_by: str = ""

    @model_validator(mode="before")
    @classmethod
    def sync_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            mapping = {
                "payrollMonth": "payroll_month",
                "employeeId": "employee_id",
                "basicSalary": "basic_salary",
                "leaveDeductions": "leave_deductions",
                "otherDeductions": "other_deductions",
                "grossSalary": "gross_salary",
                "totalDeductions": "total_deductions",
                "netSalary": "net_salary",
                "generatedDate": "generated_date",
                "generatedBy": "generated_by",
            }
            for camel, snake in mapping.items():
                if camel in data and not data.get(snake):
                    data[snake] = data[camel]
                elif snake in data and not data.get(camel):
                    data[camel] = data[snake]
        return data


class PayrollValidationIssueResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: str
    employeeId: str = ""
    validationType: str = ""
    status: Literal["Open", "Resolved"] = "Open"
    message: str = ""
    severity: Literal["Information", "Warning", "Error", "Critical"] = "Warning"
    timestamp: str = ""
    validatedBy: str = ""

    # snake_case compatibility
    employee_id: str = ""
    validation_type: str = ""
    validated_by: str = ""

    @model_validator(mode="before")
    @classmethod
    def sync_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            mapping = {
                "employeeId": "employee_id",
                "validationType": "validation_type",
                "validatedBy": "validated_by",
            }
            for camel, snake in mapping.items():
                if camel in data and not data.get(snake):
                    data[snake] = data[camel]
                elif snake in data and not data.get(camel):
                    data[camel] = data[snake]
        return data


class ResolveValidationIssueRequest(BaseModel):
    status: Literal["Open", "Resolved"] = "Resolved"


class PayslipResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: str
    payrollId: str = ""
    employeeId: str = ""
    payrollMonth: str = ""
    basicSalary: float = 0.0
    allowances: float = 0.0
    deductions: float = 0.0
    grossSalary: float = 0.0
    netSalary: float = 0.0
    generatedDate: str = ""
    digitalSignature: str = "Payroll Administrator"
    status: Literal["Generated", "Sent", "Downloaded"] = "Generated"

    # snake_case compatibility
    payroll_id: str = ""
    employee_id: str = ""
    payroll_month: str = ""
    basic_salary: float = 0.0
    gross_salary: float = 0.0
    net_salary: float = 0.0
    generated_date: str = ""
    digital_signature: str = "Payroll Administrator"

    @model_validator(mode="before")
    @classmethod
    def sync_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            mapping = {
                "payrollId": "payroll_id",
                "employeeId": "employee_id",
                "payrollMonth": "payroll_month",
                "basicSalary": "basic_salary",
                "grossSalary": "gross_salary",
                "netSalary": "net_salary",
                "generatedDate": "generated_date",
                "digitalSignature": "digital_signature",
            }
            for camel, snake in mapping.items():
                if camel in data and not data.get(snake):
                    data[snake] = data[camel]
                elif snake in data and not data.get(camel):
                    data[camel] = data[snake]
        return data


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
    employeeId: str = ""
    payrollId: str = ""
    type: Literal["PF", "ESI", "Professional Tax", "Income Tax", "Insurance", "Loan", "Other"] = "PF"
    calculationMethod: Literal["Percentage", "Flat", "Slab"] = "Percentage"
    amount: float = 0.0
    ruleApplied: str = ""
    effectiveDate: str = ""
    status: Literal["Active", "Inactive"] = "Active"

    # snake_case compatibility
    employee_id: str = ""
    payroll_id: str = ""
    calculation_method: str = "Percentage"
    rule_applied: str = ""
    effective_date: str = ""

    @model_validator(mode="before")
    @classmethod
    def sync_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            mapping = {
                "employeeId": "employee_id",
                "payrollId": "payroll_id",
                "calculationMethod": "calculation_method",
                "ruleApplied": "rule_applied",
                "effectiveDate": "effective_date",
            }
            for camel, snake in mapping.items():
                if camel in data and not data.get(snake):
                    data[snake] = data[camel]
                elif snake in data and not data.get(camel):
                    data[camel] = data[snake]
        return data


class TaxRuleResponse(BaseModel):
    id: str
    rule_name: str
    regime: str
    slab_details: str
    applicable_year: str
    is_active: bool = True
