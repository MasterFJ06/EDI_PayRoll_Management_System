from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP, localcontext
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from app.application.common.unit_of_work import UnitOfWork
from app.application.organization.work_calendar_service import WorkCalendarService
from app.domain.shared.exceptions import BusinessRuleViolation
from app.domain.workforce.overtime import OvertimeAnomaly, OvertimeCalculation, overtime_base_component


class OvertimeDerivationService:
    """Derives workforce OT for an existing Attendance row; it persists no OT facts."""

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow
        self.calendar = WorkCalendarService(uow)

    def derive_attendance(
        self, attendance_id: int, payroll_year: int, payroll_month: int
    ) -> tuple[tuple[OvertimeCalculation, ...], tuple[OvertimeAnomaly, ...]]:
        attendance = self.uow.attendance.get_by_id(attendance_id)
        if attendance is None:
            raise BusinessRuleViolation("Attendance record does not exist.")
        if not 1 <= payroll_month <= 12:
            raise BusinessRuleViolation("Payroll month must be between 1 and 12.")
        if attendance.attendance_status in {"ABSENT", "HALF_DAY"}:
            return (), ()
        if attendance.check_in_time is None or attendance.check_out_time is None:
            return (), (self._anomaly("MISSING_TIMESTAMP", "Attendance is missing check-in or check-out.", attendance),)

        calendar_day = self.calendar.classify_date(attendance.attendance_date)
        zone = ZoneInfo(calendar_day.time_zone)
        check_in, issue = self._as_local_instant(attendance.check_in_time, zone)
        if issue:
            return (), (self._anomaly(issue, "Check-in local time is ambiguous or nonexistent.", attendance),)
        check_out, issue = self._as_local_instant(attendance.check_out_time, zone)
        if issue:
            return (), (self._anomaly(issue, "Check-out local time is ambiguous or nonexistent.", attendance),)
        if check_in.astimezone(zone).date() != attendance.attendance_date:
            return (), (self._anomaly("CHECK_IN_DATE_MISMATCH", "Check-in local date does not equal attendance_date.", attendance),)
        checkout_local_date = check_out.astimezone(zone).date()
        checkout_calendar = self.calendar.classify_date(checkout_local_date)
        if checkout_calendar.time_zone != calendar_day.time_zone:
            return (), (self._anomaly(
                "CALENDAR_TIMEZONE_CHANGED_DURING_INTERVAL",
                "Work Calendar timezone changes during this attendance interval.", attendance,
            ),)
        elapsed = check_out.astimezone(timezone.utc) - check_in.astimezone(timezone.utc)
        if elapsed < timedelta(0):
            return (), (self._anomaly("REVERSED_TIMESTAMPS", "Check-out precedes check-in.", attendance),)
        if elapsed > timedelta(hours=24):
            return (), (self._anomaly("DURATION_EXCEEDS_24_HOURS", "Attendance duration exceeds 24 hours.", attendance),)
        working_days = self.calendar.working_day_count(payroll_year, payroll_month)
        if working_days <= 0:
            raise BusinessRuleViolation("Payroll month has no Work Calendar working days.")

        calculations: list[OvertimeCalculation] = []
        cursor = check_in.astimezone(timezone.utc)
        end_utc = check_out.astimezone(timezone.utc)
        while cursor < end_utc:
            local_cursor = cursor.astimezone(zone)
            day = local_cursor.date()
            next_midnight, issue = self._as_local_instant(datetime.combine(day + timedelta(days=1), time.min), zone)
            if issue:
                return (), (self._anomaly(issue, "Local midnight is ambiguous or nonexistent.", attendance, day),)
            boundary = next_midnight.astimezone(timezone.utc)
            if boundary <= cursor:
                return (), (self._anomaly("INVALID_LOCAL_BOUNDARY", "Unable to split attendance at local midnight.", attendance, day),)
            segment_end = min(boundary, end_utc)
            worked_minutes = _duration_minutes(segment_end - cursor)
            calendar = self.calendar.classify_date(day)
            if calendar.time_zone != calendar_day.time_zone:
                return (), (self._anomaly(
                    "CALENDAR_TIMEZONE_CHANGED_DURING_INTERVAL",
                    "Work Calendar timezone changes during this attendance interval.", attendance, day,
                ),)
            if calendar.classification == "WORKING_DAY":
                overtime_minutes = max(Decimal(0), worked_minutes - Decimal(480))
                multiplier = Decimal("1.0")
            else:
                overtime_minutes = worked_minutes
                multiplier = None
            policy = self.uow.overtime_policies.get_applicable(day) if worked_minutes > 0 else None
            if worked_minutes > 0 and policy is None:
                raise BusinessRuleViolation(f"No overtime policy applies on {day.isoformat()}.")
            if overtime_minutes > 0:
                assert policy is not None
                if calendar.classification != "WORKING_DAY":
                    multiplier = policy.non_working_multiplier
                assignment_candidates = self.uow.employee_salary_assignments.get_applicable_for_employee(
                    attendance.employee_id, day
                )
                if len(assignment_candidates) != 1:
                    raise BusinessRuleViolation(
                        f"Exactly one compensation assignment must apply on {day.isoformat()}."
                    )
                assignment = assignment_candidates[0]
                revision = self.uow.salary_revisions.get_by_id(assignment.salary_revision_id)
                if revision is None or not _applies(revision.effective_from, revision.effective_to, day):
                    raise BusinessRuleViolation(f"No applicable salary revision exists on {day.isoformat()}.")
                revision_components = self.uow.salary_revision_components.get_by_revision(revision.salary_revision_id)
                component_ids = {row.salary_component_id for row in revision_components if row.is_overtime_base}
                component_models = self.uow.salary_components.get_by_ids(component_ids)
                component_types = {item.salary_component_id: item.component_type for item in component_models}
                components = [SimpleNamespace(
                    is_overtime_base=row.is_overtime_base,
                    component_type=component_types.get(row.salary_component_id),
                    calculation_type=row.calculation_type,
                    fixed_amount=row.fixed_amount,
                    salary_component_id=row.salary_component_id,
                ) for row in revision_components]
                base = overtime_base_component(components)
                base_amount = Decimal(base.fixed_amount)
                if policy.policy_id is None:
                    raise BusinessRuleViolation("Applicable overtime policy has no persisted identifier.")
                with localcontext() as context:
                    context.prec = 50
                    hours = overtime_minutes / Decimal(60)
                    hourly_rate = base_amount / Decimal(working_days) / Decimal(8)
                    amount = (hours * hourly_rate * Decimal(multiplier)).quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    )
                segment_start = max(assignment.effective_from, revision.effective_from)
                segment_ends = [end for end in (assignment.effective_to, revision.effective_to) if end is not None]
                calculations.append(OvertimeCalculation(
                    employee_id=attendance.employee_id,
                    attendance_id=attendance.attendance_id,
                    attendance_date=attendance.attendance_date,
                    time_zone=calendar.time_zone,
                    interval_start=cursor.astimezone(zone).replace(tzinfo=None),
                    interval_end=segment_end.astimezone(zone).replace(tzinfo=None),
                    calendar_version_id=calendar.work_calendar_version_id,
                    classification=calendar.classification,
                    scheduled_minutes=calendar.scheduled_minutes,
                    actual_worked_minutes=worked_minutes,
                    overtime_minutes=overtime_minutes,
                    overtime_hours=hours,
                    policy_version_id=policy.policy_id,
                    policy_version_number=policy.version_number,
                    multiplier=Decimal(multiplier),
                    compensation_segment_start=segment_start,
                    compensation_segment_end=min(segment_ends) if segment_ends else None,
                    salary_revision_id=revision.salary_revision_id,
                    overtime_base_component_id=base.salary_component_id,
                    overtime_base_amount=base_amount,
                    working_day_denominator=working_days,
                    hourly_rate=hourly_rate,
                    amount=amount,
                ))
            cursor = segment_end
        return tuple(calculations), ()

    @staticmethod
    def _as_local_instant(value: datetime, zone: ZoneInfo) -> tuple[datetime, str | None]:
        if value.tzinfo is not None:
            return value.astimezone(zone), None
        candidates: dict[object, datetime] = {}
        for fold in (0, 1):
            candidate = value.replace(tzinfo=zone, fold=fold)
            utc_value = candidate.astimezone(timezone.utc)
            if utc_value.astimezone(zone).replace(tzinfo=None) == value:
                candidates[utc_value] = candidate
        if not candidates:
            return value.replace(tzinfo=zone), "NONEXISTENT_LOCAL_TIME"
        if len(candidates) > 1:
            return value.replace(tzinfo=zone), "AMBIGUOUS_LOCAL_TIME"
        return next(iter(candidates.values())), None

    @staticmethod
    def _anomaly(code: str, message: str, attendance: object, day: date | None = None) -> OvertimeAnomaly:
        return OvertimeAnomaly(code, message, getattr(attendance, "attendance_id", None), day or attendance.attendance_date)


def _applies(start: date, end: date | None, day: date) -> bool:
    return start <= day and (end is None or end >= day)


def _duration_minutes(duration: timedelta) -> Decimal:
    microseconds = ((duration.days * 86400 + duration.seconds) * 1_000_000) + duration.microseconds
    with localcontext() as context:
        context.prec = 50
        return Decimal(microseconds) / Decimal(60_000_000)
