from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class OvertimePolicyCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version_number: int = Field(gt=0, le=4_294_967_295)
    effective_from: date
    effective_to: date | None = None
    non_working_multiplier: Decimal = Field(ge=0, max_digits=8, decimal_places=4)

    @model_validator(mode="after")
    def validate_period(self) -> "OvertimePolicyCreateRequest":
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise ValueError("effective_to must not precede effective_from.")
        return self


class OvertimePolicyResponse(BaseModel):
    workforce_overtime_policy_version_id: int
    version_number: int
    effective_from: date
    effective_to: date | None
    non_working_multiplier: Decimal
    created_by_user_id: int

