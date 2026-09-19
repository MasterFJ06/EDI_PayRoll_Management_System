from datetime import date, datetime

from pydantic import BaseModel, Field


class AttendanceCreateRequest(BaseModel):
    employee_id: int = Field(gt=0)
    attendance_date: date
    check_in_time: datetime | None = None
    check_out_time: datetime | None = None
    attendance_status: str = Field(min_length=1, max_length=20)


class AttendanceResponse(BaseModel):
    attendance_id: int
    employee_id: int
    attendance_date: date
    check_in_time: datetime | None
    check_out_time: datetime | None
    attendance_status: str