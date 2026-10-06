from datetime import date
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class EmployeeCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    employee_code: str | None = Field(default=None, min_length=1, max_length=30)
    employeeCode: str | None = None
    user_id: int | None = Field(default=None, gt=0)
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    firstName: str | None = None
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    lastName: str | None = None
    email: str | None = None
    phone: str | None = None
    dateOfBirth: str | None = None
    gender: str | None = "Male"
    department_id: int | None = None
    departmentId: str | int | None = None
    designation_id: int | None = None
    designationId: str | int | None = None
    manager_employee_id: int | None = None
    managerId: str | int | None = None
    employmentType: str | None = "Full-Time"
    joining_date: date | None = None
    joiningDate: str | date | None = None
    address: str | None = None
    emergencyContact: str | None = None

    def get_code(self) -> str:
        return self.employee_code or self.employeeCode or ""

    def get_first_name(self) -> str:
        return self.first_name or self.firstName or ""

    def get_last_name(self) -> str:
        return self.last_name or self.lastName or ""

    def get_dept_id(self) -> int:
        if self.department_id is not None:
            return self.department_id
        if self.departmentId is not None:
            raw = str(self.departmentId).replace("D", "")
            return int(raw) if raw.isdigit() else 1
        return 1

    def get_desig_id(self) -> int:
        if self.designation_id is not None:
            return self.designation_id
        if self.designationId is not None:
            raw = str(self.designationId).replace("DS", "")
            return int(raw) if raw.isdigit() else 1
        return 1

    def get_joining_date(self) -> date:
        if self.joining_date is not None:
            return self.joining_date
        if self.joiningDate is not None:
            if isinstance(self.joiningDate, date):
                return self.joiningDate
            return date.fromisoformat(str(self.joiningDate)[:10])
        return date.today()


class EmployeeUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    employee_code: str | None = None
    employeeCode: str | None = None
    first_name: str | None = None
    firstName: str | None = None
    last_name: str | None = None
    lastName: str | None = None
    email: str | None = None
    phone: str | None = None
    dateOfBirth: str | None = None
    gender: str | None = None
    department_id: int | None = None
    departmentId: str | int | None = None
    designation_id: int | None = None
    designationId: str | int | None = None
    manager_employee_id: int | None = None
    managerId: str | int | None = None
    employmentType: str | None = None
    employment_status: str | None = None
    employmentStatus: str | None = None
    address: str | None = None
    emergencyContact: str | None = None


class EmployeeResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    employee_id: int
    employee_code: str
    user_id: int | None = None
    first_name: str
    last_name: str
    department_id: int
    designation_id: int
    manager_employee_id: int | None = None
    joining_date: date
    employment_status: str

    id: str
    employeeCode: str
    firstName: str
    lastName: str
    email: str = ""
    phone: str = ""
    dateOfBirth: str = "1995-01-01"
    gender: str = "Male"
    departmentId: str = ""
    designationId: str = ""
    managerId: str | None = None
    employmentType: str = "Full-Time"
    joiningDate: str = ""
    employmentStatus: str = "Active"
    address: str = ""
    emergencyContact: str = ""
    createdDate: str = ""
    updatedDate: str = ""