from pydantic import BaseModel, ConfigDict, Field


class DepartmentCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    department_code: str | None = Field(default=None, min_length=1, max_length=30)
    code: str | None = None
    department_name: str | None = Field(default=None, min_length=1, max_length=100)
    name: str | None = None
    description: str | None = None
    headEmployeeId: str | None = None

    def get_code(self) -> str:
        return self.department_code or self.code or ""

    def get_name(self) -> str:
        return self.department_name or self.name or ""


class DepartmentUpdateRequest(BaseModel):
    department_code: str | None = None
    code: str | None = None
    department_name: str | None = None
    name: str | None = None
    description: str | None = None
    status: str | None = None
    headEmployeeId: str | None = None


class DepartmentResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    department_id: int
    department_code: str
    department_name: str
    status: str
    id: str
    code: str
    name: str
    description: str = ""
    headEmployeeId: str | None = None
    headName: str | None = None
    employeeCount: int = 0
    createdDate: str = ""
    updatedDate: str = ""


class DesignationCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    designation_code: str | None = Field(default=None, min_length=1, max_length=30)
    code: str | None = None
    designation_name: str | None = Field(default=None, min_length=1, max_length=100)
    name: str | None = None
    description: str | None = None
    hierarchyLevel: int | None = 1
    departmentId: str | None = None

    def get_code(self) -> str:
        return self.designation_code or self.code or ""

    def get_name(self) -> str:
        return self.designation_name or self.name or ""


class DesignationUpdateRequest(BaseModel):
    designation_code: str | None = None
    code: str | None = None
    designation_name: str | None = None
    name: str | None = None
    description: str | None = None
    status: str | None = None
    hierarchyLevel: int | None = None
    departmentId: str | None = None


class DesignationResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    designation_id: int
    designation_code: str
    designation_name: str
    status: str
    id: str
    code: str
    name: str
    description: str = ""
    hierarchyLevel: int = 1
    departmentId: str = ""
    createdDate: str = ""
    updatedDate: str = ""