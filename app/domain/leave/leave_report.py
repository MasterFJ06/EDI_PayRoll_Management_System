from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class LeaveAllocationReportRecord:
    leave_request_id: int
    leave_request_day_id: int
    employee_id: int
    employee_code: str
    first_name: str
    last_name: str
    department_id: int
    department_name: str
    designation_id: int
    designation_name: str
    leave_type_id: int
    leave_type_name: str
    start_date: date
    end_date: date
    requested_days: Decimal
    status: str
    leave_date: date
    day_fraction: Decimal


@dataclass(frozen=True)
class LeaveBalanceReportRecord:
    employee_id: int
    employee_code: str
    first_name: str
    last_name: str
    department_id: int
    department_name: str
    designation_id: int
    designation_name: str
    leave_type_id: int
    leave_type_name: str
    balance_year: int
    allocated_days: Decimal
    used_days: Decimal
