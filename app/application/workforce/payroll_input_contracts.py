from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from app.application.compensation.contracts import SalaryComponentSnapshot
from app.domain.workforce.overtime import OvertimeAnomaly


@dataclass(frozen=True)
class WorkforceInputCondition:
    code: str
    message: str
    employee_id: int | None = None
    affected_date: date | None = None


@dataclass(frozen=True)
class AttendanceInput:
    employee_id: int
    attendance_date: date
    attendance_id: int | None
    status: str | None
    check_in: datetime | None
    check_out: datetime | None


@dataclass(frozen=True)
class LeaveAllocationInput:
    leave_request_id: int
    employee_id: int
    leave_type_id: int
    payroll_treatment: str | None
    status: str
    leave_date: date
    day_fraction: Decimal


@dataclass(frozen=True)
class CalendarDayInput:
    calendar_version_id: int
    calendar_version_number: int
    date: date
    classification: str
    scheduled_minutes: int
    timezone: str


@dataclass(frozen=True)
class OvertimePolicyInput:
    date: date
    policy_id: int | None
    version_number: int | None
    effective_from: date | None
    effective_to: date | None
    multiplier: Decimal | None


@dataclass(frozen=True)
class CompensationSegmentInput:
    employee_id: int
    assignment_id: int
    salary_revision_id: int
    segment_start: date
    segment_end: date
    components: tuple[SalaryComponentSnapshot, ...]
    overtime_base_components: tuple[SalaryComponentSnapshot, ...]
    conditions: tuple[WorkforceInputCondition, ...]


@dataclass(frozen=True)
class WorkforcePayrollInputResult:
    employee_id: int
    range_start: date
    range_end: date
    attendance: tuple[AttendanceInput, ...]
    leave_allocations: tuple[LeaveAllocationInput, ...]
    calendar_days: tuple[CalendarDayInput, ...]
    overtime_policies: tuple[OvertimePolicyInput, ...]
    compensation_segments: tuple[CompensationSegmentInput, ...]
    anomalies: tuple[OvertimeAnomaly, ...]
    conditions: tuple[WorkforceInputCondition, ...]
