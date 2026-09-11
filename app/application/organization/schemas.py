from pydantic import BaseModel, Field


class DepartmentCreateRequest(BaseModel):
    department_code: str = Field(min_length=1, max_length=30)
    department_name: str = Field(min_length=1, max_length=100)


class DepartmentResponse(BaseModel):
    department_id: int
    department_code: str
    department_name: str
    status: str


class DesignationCreateRequest(BaseModel):
    designation_code: str = Field(min_length=1, max_length=30)
    designation_name: str = Field(min_length=1, max_length=100)


class DesignationResponse(BaseModel):
    designation_id: int
    designation_code: str
    designation_name: str
    status: str