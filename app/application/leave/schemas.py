from datetime import date
from decimal import Decimal
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


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
    employeeId: str = ""
    leaveType: str = ""
    startDate: str = ""
    endDate: str = ""
    totalDays: float = 0.0
    reason: str = ""
    status: Literal["Pending", "Approved", "Rejected", "Cancelled"] = "Pending"
    approverId: str | None = None
    appliedDate: str = ""
    approvalDate: str | None = None

    # snake_case compatibility
    employee_id: str = ""
    leave_type: str = ""
    start_date: str = ""
    end_date: str = ""
    total_days: float = 0.0
    approver_id: str | None = None
    applied_date: str = ""
    approval_date: str | None = None

    @model_validator(mode="before")
    @classmethod
    def sync_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            emp = data.get("employeeId") or data.get("employee_id") or ""
            lt = data.get("leaveType") or data.get("leave_type") or "Casual"
            sd = str(data.get("startDate") or data.get("start_date") or "")
            ed = str(data.get("endDate") or data.get("end_date") or "")
            td = float(data.get("totalDays") if data.get("totalDays") is not None else (data.get("total_days") or 0.0))
            app_id = data.get("approverId") or data.get("approver_id")
            app_d = str(data.get("appliedDate") or data.get("applied_date") or "")
            apr_d = data.get("approvalDate") or data.get("approval_date")
            if apr_d is not None:
                apr_d = str(apr_d)

            data["employeeId"] = emp
            data["employee_id"] = emp
            data["leaveType"] = lt
            data["leave_type"] = lt
            data["startDate"] = sd
            data["start_date"] = sd
            data["endDate"] = ed
            data["end_date"] = ed
            data["totalDays"] = td
            data["total_days"] = td
            data["approverId"] = app_id
            data["approver_id"] = app_id
            data["appliedDate"] = app_d
            data["applied_date"] = app_d
            data["approvalDate"] = apr_d
            data["approval_date"] = apr_d
        return data


class LeaveBalanceResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    employeeId: str = ""
    leaveType: str = ""
    entitled: float = 0.0
    used: float = 0.0
    balance: float = 0.0

    # snake_case compatibility
    employee_id: str = ""
    leave_type: str = ""

    @model_validator(mode="before")
    @classmethod
    def sync_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            emp = data.get("employeeId") or data.get("employee_id") or ""
            lt = data.get("leaveType") or data.get("leave_type") or ""
            data["employeeId"] = emp
            data["employee_id"] = emp
            data["leaveType"] = lt
            data["leave_type"] = lt
        return data

