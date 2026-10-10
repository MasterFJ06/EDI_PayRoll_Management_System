from datetime import date, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from app.application.common.unit_of_work import UnitOfWork
from app.application.compensation.segmentation import CompensationSegmentationResolver
from app.application.organization.work_calendar_service import WorkCalendarService
from app.application.workforce.overtime_derivation_service import (
    OvertimeDerivationService,
)
from app.application.workforce.payroll_input_contracts import (
    AttendanceInput,
    CalendarDayInput,
    CompensationSegmentInput,
    LeaveAllocationInput,
    OvertimePolicyInput,
    WorkforceInputCondition,
    WorkforcePayrollInputResult,
)
from app.domain.shared.exceptions import BusinessRuleViolation, InvalidDomainState
from app.domain.workforce.overtime import OvertimeAnomaly


class WorkforcePayrollInputReader:
    """Reads authoritative Workforce and Compensation inputs without persisting."""

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow
        self.calendar = WorkCalendarService(uow)
        self.compensation = CompensationSegmentationResolver(uow)

    def read(
        self, employee_id: int, range_start: date, range_end: date
    ) -> WorkforcePayrollInputResult:
        if employee_id <= 0:
            raise ValueError("Employee ID must be positive.")
        if range_start > range_end:
            raise ValueError("Workforce input range must be ordered.")

        conditions: list[WorkforceInputCondition] = []
        anomalies: list[OvertimeAnomaly] = []
        days = tuple(_dates(range_start, range_end))

        attendance_rows = self.uow.attendance.get_for_employee_period(
            employee_id, range_start, range_end
        )
        attendance_by_date = {row.attendance_date: row for row in attendance_rows}
        calendar_days: list[CalendarDayInput] = []
        calendar_by_date: dict[date, CalendarDayInput] = {}
        for day in days:
            try:
                resolved = self.calendar.classify_date(day)
                item = CalendarDayInput(
                    calendar_version_id=resolved.work_calendar_version_id,
                    calendar_version_number=resolved.calendar_version_number,
                    date=resolved.calendar_date,
                    classification=resolved.classification,
                    scheduled_minutes=resolved.scheduled_minutes,
                    timezone=resolved.time_zone,
                )
                calendar_days.append(item)
                calendar_by_date[day] = item
            except InvalidDomainState as exc:
                conditions.append(
                    WorkforceInputCondition(
                        "CONFLICTING_CALENDAR_CLASSIFICATION",
                        str(exc),
                        employee_id,
                        day,
                    )
                )
            except BusinessRuleViolation as exc:
                conditions.append(
                    WorkforceInputCondition(
                        "MISSING_CALENDAR_CLASSIFICATION",
                        str(exc),
                        employee_id,
                        day,
                    )
                )

        attendance: list[AttendanceInput] = []
        for day in days:
            row = attendance_by_date.get(day)
            if row is None:
                attendance.append(
                    AttendanceInput(employee_id, day, None, None, None, None)
                )
                calendar = calendar_by_date.get(day)
                if calendar is not None and calendar.classification == "WORKING_DAY":
                    anomalies.append(
                        OvertimeAnomaly(
                            "MISSING_ATTENDANCE",
                            "No Attendance row exists for this Work Calendar working date.",
                            None,
                            day,
                        )
                    )
                continue

            item = AttendanceInput(
                employee_id=row.employee_id,
                attendance_date=row.attendance_date,
                attendance_id=row.attendance_id,
                status=row.attendance_status,
                check_in=row.check_in_time,
                check_out=row.check_out_time,
            )
            attendance.append(item)
            if item.status in {"ABSENT", "HALF_DAY"}:
                continue
            if item.check_in is None:
                anomalies.append(
                    OvertimeAnomaly(
                        "MISSING_CHECK_IN", "Attendance has no check-in time.", item.attendance_id, day
                    )
                )
            if item.check_out is None:
                anomalies.append(
                    OvertimeAnomaly(
                        "MISSING_CHECK_OUT", "Attendance has no check-out time.", item.attendance_id, day
                    )
                )
            if item.check_in is not None and item.check_out is not None:
                calendar = calendar_by_date.get(day)
                if calendar is not None:
                    zone = ZoneInfo(calendar.timezone)
                    local_start, start_issue = OvertimeDerivationService._as_local_instant(
                        item.check_in, zone
                    )
                    local_end, end_issue = OvertimeDerivationService._as_local_instant(
                        item.check_out, zone
                    )
                    for issue in (start_issue, end_issue):
                        if issue is not None:
                            anomalies.append(
                                OvertimeAnomaly(
                                    issue,
                                    "Attendance timestamp is ambiguous or nonexistent in the calendar timezone.",
                                    item.attendance_id,
                                    day,
                                )
                            )
                    if start_issue is not None or end_issue is not None:
                        continue
                    if local_start.astimezone(zone).date() != day:
                        anomalies.append(
                            OvertimeAnomaly(
                                "CHECK_IN_DATE_MISMATCH",
                                "Check-in local date does not match attendance_date.",
                                item.attendance_id,
                                day,
                            )
                        )
                    elapsed = local_end.astimezone(timezone.utc) - local_start.astimezone(
                        timezone.utc
                    )
                else:
                    try:
                        elapsed = item.check_out - item.check_in
                    except TypeError:
                        anomalies.append(
                            OvertimeAnomaly(
                                "INVALID_ATTENDANCE_INTERVAL",
                                "Attendance timestamps use incompatible timezone forms.",
                                item.attendance_id,
                                day,
                            )
                        )
                        continue
                if elapsed < timedelta(0):
                    anomalies.append(
                        OvertimeAnomaly(
                            "INVALID_ATTENDANCE_INTERVAL",
                            "Attendance check-out precedes check-in.",
                            item.attendance_id,
                            day,
                        )
                    )
                elif elapsed > timedelta(hours=24):
                    anomalies.append(
                        OvertimeAnomaly(
                            "OVER_24_HOURS",
                            "Attendance interval exceeds 24 hours.",
                            item.attendance_id,
                            day,
                        )
                    )

        leave_allocations: list[LeaveAllocationInput] = []
        leave_dates: set[date] = set()
        for request, allocation, leave_type in self.uow.leave_requests.get_approved_allocations_for_employee_period(
            employee_id, range_start, range_end
        ):
            treatment = leave_type.payroll_treatment if leave_type is not None else None
            leave_allocations.append(
                LeaveAllocationInput(
                    leave_request_id=request.leave_request_id,
                    employee_id=request.employee_id,
                    leave_type_id=request.leave_type_id,
                    payroll_treatment=treatment,
                    status=request.status,
                    leave_date=allocation.leave_date,
                    day_fraction=allocation.day_fraction,
                )
            )
            if treatment not in {"PAID", "UNPAID"}:
                conditions.append(
                    WorkforceInputCondition(
                        "INVALID_LEAVE_TREATMENT",
                        "Approved leave has no valid PAID or UNPAID payroll treatment.",
                        employee_id,
                        allocation.leave_date,
                    )
                )
            if allocation.leave_date in leave_dates:
                conditions.append(
                    WorkforceInputCondition(
                        "APPROVED_LEAVE_ALLOCATION_CONFLICT",
                        "Multiple approved leave allocations exist for the employee and date.",
                        employee_id,
                        allocation.leave_date,
                    )
                )
            leave_dates.add(allocation.leave_date)

        overtime_policies: list[OvertimePolicyInput] = []
        for day in days:
            try:
                policy = self.uow.overtime_policies.get_applicable(day)
            except InvalidDomainState as exc:
                overtime_policies.append(OvertimePolicyInput(day, None, None, None, None, None))
                conditions.append(
                    WorkforceInputCondition(
                        "CONFLICTING_OVERTIME_POLICY", str(exc), employee_id, day
                    )
                )
                continue
            if policy is None:
                overtime_policies.append(OvertimePolicyInput(day, None, None, None, None, None))
                conditions.append(
                    WorkforceInputCondition(
                        "MISSING_OVERTIME_POLICY",
                        "No overtime policy applies on this date.",
                        employee_id,
                        day,
                    )
                )
                continue
            overtime_policies.append(
                OvertimePolicyInput(
                    date=day,
                    policy_id=policy.policy_id,
                    version_number=policy.version_number,
                    effective_from=policy.effective_from,
                    effective_to=policy.effective_to,
                    multiplier=Decimal(policy.non_working_multiplier),
                )
            )

        compensation_result = self.compensation.resolve(
            employee_id, range_start, range_end
        )
        for condition in compensation_result.conditions:
            conditions.append(
                WorkforceInputCondition(
                    condition.code, condition.message, employee_id, None
                )
            )
        compensation_segments: list[CompensationSegmentInput] = []
        for segment in compensation_result.segments:
            config = segment.compensation
            components = config.revision.components
            designated = tuple(item for item in components if item.is_overtime_base)
            segment_conditions: list[WorkforceInputCondition] = []
            if not designated:
                segment_conditions.append(
                    WorkforceInputCondition(
                        "OVERTIME_BASE_MISSING",
                        "Salary revision has no designated overtime base component.",
                        employee_id,
                        segment.segment_start,
                    )
                )
            elif len(designated) > 1:
                segment_conditions.append(
                    WorkforceInputCondition(
                        "OVERTIME_BASE_AMBIGUOUS",
                        "Salary revision has multiple designated overtime base components.",
                        employee_id,
                        segment.segment_start,
                    )
                )
            else:
                base = designated[0]
                if (
                    base.component_type != "EARNING"
                    or base.calculation_type != "FIXED"
                    or base.fixed_amount is None
                ):
                    segment_conditions.append(
                        WorkforceInputCondition(
                            "INVALID_OVERTIME_BASE_CONFIGURATION",
                            "Designated overtime base must be an EARNING with FIXED amount.",
                            employee_id,
                            segment.segment_start,
                        )
                    )
            conditions.extend(segment_conditions)
            compensation_segments.append(
                CompensationSegmentInput(
                    employee_id=segment.employee_id,
                    assignment_id=config.assignment.salary_assignment_id,
                    salary_revision_id=config.revision.salary_revision_id,
                    segment_start=segment.segment_start,
                    segment_end=segment.segment_end,
                    components=components,
                    overtime_base_components=designated,
                    conditions=tuple(segment_conditions),
                )
            )

        return WorkforcePayrollInputResult(
            employee_id=employee_id,
            range_start=range_start,
            range_end=range_end,
            attendance=tuple(attendance),
            leave_allocations=tuple(leave_allocations),
            calendar_days=tuple(calendar_days),
            overtime_policies=tuple(overtime_policies),
            compensation_segments=tuple(compensation_segments),
            anomalies=tuple(anomalies),
            conditions=tuple(conditions),
        )


def _dates(start: date, end: date):
    day = start
    while day <= end:
        yield day
        day += timedelta(days=1)
