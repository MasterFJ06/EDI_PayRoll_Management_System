from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class SalaryStructureRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    employee_id: str | None = None
    employeeId: str | None = None
    basic: float
    hra: float | None = None
    da: float | None = None
    specialAllowance: float | None = None
    special_allowance: float | None = None
    travelAllowance: float | None = 1600.0
    medicalAllowance: float | None = 1250.0
    otherAllowances: float | None = 500.0
    providentFund: float | None = None
    professionalTax: float | None = 200.0
    bonus: float | None = 0.0
    overtimeRate: float | None = 350.0
    esi: float | None = None
    incomeTax: float | None = None
    insurance: float | None = 450.0
    loanDeduction: float | None = 0.0
    otherDeductions: float | None = 0.0
    effectiveFrom: str | None = "2026-04-01"
    effectiveTo: str | None = None
    revisionNumber: int | None = 1
    status: Literal["Active", "Superseded", "Draft"] = "Active"


class SalaryStructureResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: str
    employeeId: str = Field(alias="employee_id")
    basic: float
    hra: float
    da: float
    specialAllowance: float = Field(alias="special_allowance")
    travelAllowance: float = Field(default=1600.0, alias="travel_allowance")
    medicalAllowance: float = Field(default=1250.0, alias="medical_allowance")
    otherAllowances: float = Field(default=500.0, alias="other_allowances")
    providentFund: float = Field(alias="provident_fund")
    professionalTax: float = Field(default=200.0, alias="professional_tax")
    bonus: float = 0.0
    overtimeRate: float = Field(default=350.0, alias="overtime_rate")
    esi: float = 0.0
    incomeTax: float = Field(alias="income_tax")
    insurance: float = 450.0
    loanDeduction: float = Field(default=0.0, alias="loan_deduction")
    otherDeductions: float = Field(default=0.0, alias="other_deductions")
    effectiveFrom: str = Field(default="2026-04-01", alias="effective_from")
    effectiveTo: str | None = Field(default=None, alias="effective_to")
    revisionNumber: int = Field(default=1, alias="revision_number")
    status: Literal["Active", "Superseded", "Draft"] = "Active"
