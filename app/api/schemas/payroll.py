from pydantic import BaseModel, ConfigDict, Field


class PayrollRunCreateBody(BaseModel):
    year: int = Field(ge=1, le=65535)
    month: int = Field(ge=1, le=12)


class PayslipCreateBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payslip_number: str = Field(max_length=50)
