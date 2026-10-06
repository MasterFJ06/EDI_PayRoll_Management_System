from pydantic import BaseModel, Field


class PayrollRunCreateBody(BaseModel):
    year: int = Field(ge=1, le=65535)
    month: int = Field(ge=1, le=12)
