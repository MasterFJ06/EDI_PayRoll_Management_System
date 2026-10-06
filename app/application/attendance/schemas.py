from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field


class AttendanceCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    employee_id: int | None = Field(default=None, gt=0)
    employeeId: str | int | None = None
    attendance_date: date | None = None
    attendanceDate: str | date | None = None
    check_in_time: datetime | None = None
    checkIn: str | None = None
    check_out_time: datetime | None = None
    checkOut: str | None = None
    attendance_status: str
    status: str | None = None
    remarks: str | None = ""

    def get_emp_id(self) -> int:
        if self.employee_id is not None:
            return self.employee_id
        if self.employeeId is not None:
            raw = str(self.employeeId).replace("EMP", "")
            return int(raw) if raw.isdigit() else 1
        return 1

    def get_date(self) -> date:
        if self.attendance_date is not None:
            return self.attendance_date
        if self.attendanceDate is not None:
            if isinstance(self.attendanceDate, date):
                return self.attendanceDate
            return date.fromisoformat(str(self.attendanceDate)[:10])
        return date.today()

    def get_status(self) -> str:
        st = self.attendance_status or self.status or "PRESENT"
        return st.upper()


class AttendanceUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    attendance_status: str | None = None
    status: str | None = None
    check_in_time: datetime | None = None
    checkIn: str | None = None
    check_out_time: datetime | None = None
    checkOut: str | None = None
    remarks: str | None = None
    workingHours: float | None = None
    overtimeHours: float | None = None


class AttendanceResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    attendance_id: int
    employee_id: int
    attendance_date: date
    check_in_time: datetime | None = None
    check_out_time: datetime | None = None
    attendance_status: str

    id: str
    employeeId: str
    attendanceDate: str
    checkIn: str | None = None
    checkOut: str | None = None
    workingHours: float = 8.0
    overtimeHours: float = 0.0
    status: str = "Present"
    remarks: str = ""
    createdAt: str = ""
    updatedAt: str = ""