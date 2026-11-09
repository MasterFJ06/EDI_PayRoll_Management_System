from typing import Literal
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRegistrationRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=4, max_length=128)


class UserRegistrationResponse(BaseModel):
    user_id: int
    username: str
    email: EmailStr
    status: str


class UserMeResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: str
    username: str
    firstName: str = Field(default="User", alias="first_name")
    lastName: str = Field(default="", alias="last_name")
    email: str
    phone: str = ""
    employeeId: str | None = Field(default=None, alias="employee_id")
    role: str = "Employee"
    permissions: list[str] = Field(default_factory=list)
    status: Literal["Active", "Inactive"] = "Active"
    avatarColor: str = Field(default="bg-blue-500", alias="avatar_color")


class UserLoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=4, max_length=128)


class UserLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserMeResponse | None = None


class UserCreateRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=4, max_length=128)
    role: str = "Employee"
    firstName: str | None = Field(default=None, alias="first_name")
    lastName: str | None = Field(default=None, alias="last_name")
    phone: str | None = None
    employeeId: str | None = Field(default=None, alias="employee_id")


class UserUpdateRequest(BaseModel):
    email: EmailStr | None = None
    role: str | None = None
    firstName: str | None = Field(default=None, alias="first_name")
    lastName: str | None = Field(default=None, alias="last_name")
    phone: str | None = None
    status: Literal["Active", "Inactive"] | None = None
    password: str | None = None


class UserResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: str
    username: str
    firstName: str = Field(alias="first_name")
    lastName: str = Field(alias="last_name")
    email: str
    phone: str = ""
    employeeId: str | None = Field(default=None, alias="employee_id")
    role: str = "Employee"
    permissions: list[str] = Field(default_factory=list)
    status: Literal["Active", "Inactive"] = "Active"
    avatarColor: str = Field(default="bg-blue-500", alias="avatar_color")



class RoleResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: str
    name: str
    description: str | None = None
    isActive: bool = Field(default=True, alias="is_active")
    permissions: list[str] = Field(default_factory=list)


class RoleCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: str | None = None
    permissions: list[str] = Field(default_factory=list)


class RoleUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    isActive: bool | None = Field(default=None, alias="is_active")
    permissions: list[str] | None = None