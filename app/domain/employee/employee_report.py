from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class EmployeeReportRecord:
    employee_id: int
    employee_code: str
    first_name: str
    last_name: str
    department_id: int
    department_name: str | None
    designation_id: int
    designation_name: str | None
    joining_date: date
    employment_end_date: date | None
    employment_status: str
