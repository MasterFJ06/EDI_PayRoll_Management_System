from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


SalaryStructureStatus = Literal["ACTIVE", "INACTIVE"]
SalaryComponentType = Literal["EARNING", "DEDUCTION"]
SalaryComponentStatus = Literal["ACTIVE", "INACTIVE"]
CalculationType = Literal["FIXED", "PERCENTAGE"]


class SalaryStructureCreateRequest(BaseModel):
    structure_code: str = Field(min_length=1, max_length=30)
    structure_name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    status: SalaryStructureStatus = "ACTIVE"


class SalaryStructureResponse(BaseModel):
    salary_structure_id: int
    structure_code: str
    structure_name: str
    description: str | None
    status: SalaryStructureStatus


class SalaryComponentCreateRequest(BaseModel):
    component_code: str = Field(min_length=1, max_length=30)
    component_name: str = Field(min_length=1, max_length=100)
    component_type: SalaryComponentType
    status: SalaryComponentStatus = "ACTIVE"


class SalaryComponentResponse(BaseModel):
    salary_component_id: int
    component_code: str
    component_name: str
    component_type: SalaryComponentType
    status: SalaryComponentStatus


class SalaryRevisionCreateRequest(BaseModel):
    salary_structure_id: int = Field(gt=0)
    revision_number: int = Field(ge=0, le=4_294_967_295)
    effective_from: date
    effective_to: date | None = None


class SalaryRevisionResponse(BaseModel):
    salary_revision_id: int
    salary_structure_id: int
    revision_number: int
    effective_from: date
    effective_to: date | None


class SalaryRevisionComponentCreateRequest(BaseModel):
    salary_revision_id: int = Field(gt=0)
    salary_component_id: int = Field(gt=0)
    calculation_type: CalculationType
    fixed_amount: Decimal | None = Field(default=None, ge=0, max_digits=15, decimal_places=2)
    percentage_value: Decimal | None = Field(default=None, ge=0, max_digits=8, decimal_places=4)
    base_component_id: int | None = Field(default=None, gt=0)


class SalaryRevisionComponentResponse(BaseModel):
    salary_revision_id: int
    salary_component_id: int
    calculation_type: CalculationType
    fixed_amount: Decimal | None
    percentage_value: Decimal | None
    base_component_id: int | None


class EmployeeSalaryAssignmentCreateRequest(BaseModel):
    employee_id: int = Field(gt=0)
    salary_revision_id: int = Field(gt=0)
    effective_from: date
    effective_to: date | None = None


class EmployeeSalaryAssignmentResponse(BaseModel):
    salary_assignment_id: int
    employee_id: int
    salary_revision_id: int
    effective_from: date
    effective_to: date | None
