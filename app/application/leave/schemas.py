from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


LeaveRequestStatus = Literal["PENDING", "APPROVED", "REJECTED", "CANCELLED"]


class LeaveTypeCreateRequest(BaseModel):
    leave_type_code: str = Field(min_length=1, max_length=30)
    leave_type_name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    is_active: bool = True


class LeaveTypeResponse(BaseModel):
    leave_type_id: int
    leave_type_code: str
    leave_type_name: str
    description: str | None
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
    employee_id: int = Field(gt=0)
    leave_type_id: int = Field(gt=0)
    start_date: date
    end_date: date
    requested_days: Decimal = Field(gt=0, max_digits=6, decimal_places=2)
    reason: str | None = Field(default=None, max_length=1000)
    status: LeaveRequestStatus = "PENDING"
    reviewed_by_employee_id: int | None = Field(default=None, gt=0)
    reviewed_at: datetime | None = None
    review_comment: str | None = Field(default=None, max_length=1000)


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
