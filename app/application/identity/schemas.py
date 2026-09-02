from pydantic import BaseModel, EmailStr, Field


class UserRegistrationRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserRegistrationResponse(BaseModel):
    user_id: int
    username: str
    email: EmailStr
    status: str