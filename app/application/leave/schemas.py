from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


LeaveRequestStatus = Literal["PENDING", "APPROVED", "REJECTED", "CANCELLED"]


class LeaveTypeCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    leave_type_code: str = Field(min_length=1, max_length=30)
    leave_type_name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    payroll_treatment: Literal["PAID", "UNPAID"]
    is_active: bool = True


class LeaveTypeResponse(BaseModel):
    leave_type_id: int
    leave_type_code: str
    leave_type_name: str
    description: str | None
    payroll_treatment: Literal["PAID", "UNPAID"]
    is_active: bool


class LeaveBalanceCreateRequest(BaseModel):
    employee_id: int = Field(gt=0)
    leave_type_id: int = Field(gt=0)
    balance_year: int = Field(ge=0, le=65535)
    allocated_days: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=6, decimal_places=2)
    used_days: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=6, decimal_places=2)


class LeaveBalanceResponse(BaseModel):
    leave_balance_id: int
    employee_id: int
    leave_type_id: int
    balance_year: int
    allocated_days: Decimal
    used_days: Decimal


class LeaveRequestCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    employee_id: int = Field(gt=0)
    leave_type_id: int = Field(gt=0)
    start_date: date
    end_date: date
    requested_days: Decimal = Field(gt=0, max_digits=6, decimal_places=2)
    reason: str | None = Field(default=None, max_length=1000)
    allocations: list["LeaveRequestDayInput"] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_allocations(self) -> "LeaveRequestCreateRequest":
        dates = [allocation.leave_date for allocation in self.allocations]
        if len(set(dates)) != len(dates):
            raise ValueError("A leave request may contain only one allocation per date.")
        return self


class LeaveRequestDayInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    leave_date: date
    day_fraction: Decimal = Field(ge=Decimal("0.01"), le=Decimal("1.00"), max_digits=4, decimal_places=2)


class LeaveRequestReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_comment: str | None = Field(default=None, max_length=1000)


class LeaveRequestDayResponse(BaseModel):
    leave_date: date
    day_fraction: Decimal


class LeaveRequestResponse(BaseModel):
    leave_request_id: int
    employee_id: int
    leave_type_id: int
    start_date: date
    end_date: date
    requested_days: Decimal
    reason: str | None
    status: LeaveRequestStatus
    reviewed_by_employee_id: int | None
    reviewed_at: datetime | None
    review_comment: str | None
    allocations: list[LeaveRequestDayResponse] = Field(default_factory=list)
