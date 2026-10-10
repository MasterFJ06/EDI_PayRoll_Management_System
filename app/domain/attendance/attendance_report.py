from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class AttendanceReportRecord:
    attendance_id: int
    employee_id: int
    employee_code: str
    first_name: str
    last_name: str
    department_id: int
    department_name: str | None
    designation_id: int
    designation_name: str | None
    attendance_date: date
    attendance_status: str
    check_in_time: datetime | None
    check_out_time: datetime | None
