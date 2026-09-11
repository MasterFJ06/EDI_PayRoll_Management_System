from datetime import date

from pydantic import BaseModel, Field


class EmployeeCreateRequest(BaseModel):
    employee_code: str = Field(min_length=1, max_length=30)
    user_id: int | None = Field(default=None, gt=0)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    department_id: int = Field(gt=0)
    designation_id: int = Field(gt=0)
    manager_employee_id: int | None = Field(default=None, gt=0)
    joining_date: date


class EmployeeResponse(BaseModel):
    employee_id: int
    employee_code: str
    user_id: int | None
    first_name: str
    last_name: str
    department_id: int
    designation_id: int
    manager_employee_id: int | None
    joining_date: date
    employment_status: str