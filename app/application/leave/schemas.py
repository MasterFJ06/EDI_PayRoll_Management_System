from datetime import date
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class LeaveApplyRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    employee_id: int | str | None = None
    employeeId: str | None = None
    leave_type: str | None = None
    leaveType: str | None = None
    start_date: date | str | None = None
    startDate: str | None = None
    end_date: date | str | None = None
    endDate: str | None = None
    total_days: float | int | None = None
    totalDays: float | int | None = None
    reason: str | None = None


class LeaveReviewRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    approver_id: int | str | None = None
    approverId: str | None = None
    comment: str | None = None
    status: str | None = None


class LeaveRequestResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: str
    employeeId: str = Field(alias="employee_id")
    leaveType: str = Field(alias="leave_type")
    startDate: str = Field(alias="start_date")
    endDate: str = Field(alias="end_date")
    totalDays: float = Field(alias="total_days")
    reason: str = ""
    status: Literal["Pending", "Approved", "Rejected", "Cancelled"] = "Pending"
    approverId: str | None = Field(default=None, alias="approver_id")
    appliedDate: str = Field(alias="applied_date")
    approvalDate: str | None = Field(default=None, alias="approval_date")


class LeaveBalanceResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    employeeId: str = Field(alias="employee_id")
    leaveType: str = Field(alias="leave_type")
    entitled: float
    used: float
    balance: float
