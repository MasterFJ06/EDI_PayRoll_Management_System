from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP, localcontext
from types import MappingProxyType
from typing import Mapping, Sequence
from zoneinfo import ZoneInfo

from app.application.common.unit_of_work import UnitOfWork
from app.application.compensation.segmentation import CompensationSegment
from app.application.payroll.payroll_processing_issue_service import (
    PayrollProcessingIssueService,
)
from app.application.payroll.payroll_result_component_service import (
    PayrollResultComponentService,
)
from app.application.payroll.payroll_result_service import PayrollResultService
from app.application.payroll.schemas import (
    PayrollProcessingIssueCreateRequest,
    PayrollResultComponentCreateRequest,
    PayrollResultCreateRequest,
)
from app.application.workforce.overtime_derivation_service import (
    OvertimeDerivationService,
)
from app.domain.payroll.payroll_run_workforce_snapshot import (
    PayrollRunWorkforceSnapshot,
)


_CENT = Decimal("0.01")
_ONE = Decimal("1.00")
_ZERO = Decimal("0.00")
_NONBLOCKING_DST_ANOMALIES = {"AMBIGUOUS_LOCAL_TIME", "NONEXISTENT_LOCAL_TIME"}


class PayrollCalculationError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        issue_already_recorded: bool = False,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.issue_already_recorded = issue_already_recorded


@dataclass(frozen=True)
class _CalculatedComponent:
    salary_component_id: int
    component_name: str
    component_type: str
    compensation_amount: Decimal
    workforce_adjustment: Decimal
    overtime_adjustment: Decimal
    final_amount: Decimal
    calculation_order: int


@dataclass(frozen=True)
class EmployeePayrollCalculation:
    payroll_run_id: int
    employee_id: int
    salary_assignment_id: int
    gross_earnings: Decimal
    total_deductions: Decimal
    net_salary: Decimal
    components: tuple[_CalculatedComponent, ...]
    workforce_snapshot: dict[str, object]


class PayrollFinancialCalculationService:
    """Calculates and atomically persists employee results from frozen inputs."""

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def calculate_employee(
        self,
        payroll_run_id: int,
        employee_id: int,
        attempt_number: int,
        segments: Sequence[CompensationSegment],
        salary_assignment_id: int,
        workforce_snapshot: PayrollRunWorkforceSnapshot,
    ) -> EmployeePayrollCalculation:
        try:
            calculation = _calculate_employee(
                payroll_run_id,
                employee_id,
                attempt_number,
                segments,
                salary_assignment_id,
                workforce_snapshot,
            )
        except PayrollCalculationError:
            raise
        except (ArithmeticError, KeyError, TypeError, ValueError) as exc:
            raise PayrollCalculationError(
                "INVALID_FINANCIAL_INPUT",
                f"Frozen payroll inputs are invalid: {exc}",
            ) from exc

        result = PayrollResultService(self.uow).create(
            PayrollResultCreateRequest(
                payroll_run_id=calculation.payroll_run_id,
                employee_id=calculation.employee_id,
                salary_assignment_id=calculation.salary_assignment_id,
                gross_earnings=calculation.gross_earnings,
                total_deductions=calculation.total_deductions,
                net_salary=calculation.net_salary,
            ),
            attempt_number,
            commit=False,
            workforce_calculation_snapshot=calculation.workforce_snapshot,
        )
        for component in calculation.components:
            PayrollResultComponentService(self.uow).create(
                PayrollResultComponentCreateRequest(
                    payroll_result_id=result.payroll_result_id,
                    salary_component_id=component.salary_component_id,
                    component_type=component.component_type,
                    amount=component.final_amount,
                    calculation_order=component.calculation_order,
                ),
                attempt_number,
                commit=False,
            )
        self.uow.commit()
        return calculation

    def record_blocking_issue(
        self,
        payroll_run_id: int,
        employee_id: int,
        attempt_number: int,
        error: PayrollCalculationError,
    ) -> int | None:
        if error.issue_already_recorded:
            return None
        response = PayrollProcessingIssueService(self.uow).create(
            PayrollProcessingIssueCreateRequest(
                payroll_run_id=payroll_run_id,
                employee_id=employee_id,
                issue_code=error.code,
                issue_message=str(error),
                status="OPEN",
            ),
            attempt_number,
            commit=False,
        )
        self.uow.commit()
        return response.payroll_issue_id


def _calculate_employee(
    payroll_run_id: int,
    employee_id: int,
    attempt_number: int,
    segments: Sequence[CompensationSegment],
    salary_assignment_id: int,
    snapshot: PayrollRunWorkforceSnapshot,
) -> EmployeePayrollCalculation:
    if (
        snapshot.payroll_run_id != payroll_run_id
        or snapshot.employee_id != employee_id
        or snapshot.attempt_number != attempt_number
    ):
        raise PayrollCalculationError(
            "INVALID_WORKFORCE_SNAPSHOT", "Workforce snapshot identity is inconsistent."
        )
    if not segments:
        raise PayrollCalculationError(
            "COMPENSATION_SEGMENTS_MISSING", "No compensation segments exist for the employee."
        )
    payload = _thaw(snapshot.snapshot)
    if not isinstance(payload, dict) or payload.get("employee_id") != employee_id:
        raise PayrollCalculationError(
            "INVALID_WORKFORCE_SNAPSHOT", "Workforce snapshot employee does not match."
        )
    payload_attempt_number = payload.get("attempt_number")
    if payload_attempt_number != attempt_number:
        raise PayrollCalculationError(
            "INVALID_WORKFORCE_SNAPSHOT", "Workforce snapshot attempt number does not match."
        )

    conditions = payload.get("input_conditions", [])
    if conditions:
        condition = conditions[0]
        raise PayrollCalculationError(
            str(condition.get("code", "INVALID_WORKFORCE_INPUT")),
            str(condition.get("message", "Workforce input condition blocks calculation.")),
            issue_already_recorded=True,
        )

    monthly_working_days = _integer(payload.get("monthly_working_day_count"))
    if monthly_working_days <= 0:
        raise PayrollCalculationError(
            "INVALID_WORKFORCE_SNAPSHOT",
            "Frozen full-month working-day count must be positive.",
        )

    calendars = _index_by_date(payload.get("calendar_days", []), "date")
    processing_range = payload.get("processing_range")
    if not isinstance(processing_range, Mapping):
        raise PayrollCalculationError(
            "INVALID_WORKFORCE_SNAPSHOT", "Workforce snapshot has no processing range."
        )
    range_start = _as_date(processing_range.get("start"))
    range_end = _as_date(processing_range.get("end"))
    cursor = range_start
    while cursor <= range_end:
        calendar = calendars.get(cursor)
        if calendar is None or calendar.get("classification") not in {
            "WORKING_DAY",
            "NON_WORKING_DAY",
            "HOLIDAY",
        }:
            raise PayrollCalculationError(
                "INVALID_WORKFORCE_SNAPSHOT",
                f"Frozen Work Calendar classification is missing or invalid on {cursor.isoformat()}.",
            )
        cursor += timedelta(days=1)
    attendance = _index_by_date(payload.get("attendance", []), "date")
    policies = _index_by_date(payload.get("overtime_policies", []), "date")
    leave_by_date: dict[date, list[dict[str, object]]] = defaultdict(list)
    for allocation in _mapping_list(payload.get("leave_allocations", [])):
        day = _as_date(allocation.get("date"))
        if allocation.get("status") == "APPROVED":
            leave_by_date[day].append(allocation)

    anomalies = _mapping_list(payload.get("anomalies", []))
    attendance_anomalies: dict[date, list[dict[str, object]]] = defaultdict(list)
    for anomaly in anomalies:
        code = str(anomaly.get("code", "UNKNOWN_ATTENDANCE_ANOMALY"))
        if code == "MISSING_ATTENDANCE":
            continue
        affected_date = anomaly.get("affected_date")
        if affected_date is None:
            if code not in _NONBLOCKING_DST_ANOMALIES:
                raise _blocking_overtime_anomaly(anomaly, None)
            continue
        attendance_anomalies[_as_date(affected_date)].append(anomaly)

    grouped_segments: dict[date, list[CompensationSegment]] = defaultdict(list)
    for segment in segments:
        if segment.employee_id != employee_id:
            continue
        grouped_segments[segment.segment_start].append(segment)
    ordered_segments = sorted(
        (segment for group in grouped_segments.values() for segment in group),
        key=lambda item: (item.segment_start, item.segment_end),
    )
    if not ordered_segments:
        raise PayrollCalculationError(
            "COMPENSATION_SEGMENTS_MISSING", "No compensation segments exist for the employee."
        )

    segment_inputs: list[
        tuple[
            CompensationSegment,
            list[date],
            dict[int, tuple[Decimal, Decimal | None, int]],
            Decimal,
        ]
    ] = []
    with localcontext() as context:
        context.prec = 50
        for segment in ordered_segments:
            segment_dates = [
                day
                for day, calendar in calendars.items()
                if segment.segment_start <= day <= segment.segment_end
                and calendar.get("classification") == "WORKING_DAY"
            ]
            segment_dates.sort()
            component_amounts, _ = _calculate_segment_components(
                segment,
                len(segment_dates),
                monthly_working_days,
            )
            if not segment_dates:
                payable_fraction = _ZERO
            else:
                payable_total = sum(
                    (
                        _payable_fraction_for_date(
                            day,
                            attendance.get(day),
                            leave_by_date.get(day, []),
                        )
                        for day in segment_dates
                    ),
                    _ZERO,
                )
                payable_fraction = payable_total / Decimal(len(segment_dates))
                payable_fraction = min(_ONE, max(_ZERO, payable_fraction))
            segment_inputs.append(
                (segment, segment_dates, component_amounts, payable_fraction)
            )

    overtime_by_segment, overtime_details_by_segment = _calculate_overtime_for_segments(
        ordered_segments,
        calendars,
        attendance,
        policies,
        monthly_working_days,
        attendance_anomalies,
    )

    overtime_by_component: dict[int, Decimal] = defaultdict(lambda: _ZERO)
    for segment_adjustments in overtime_by_segment.values():
        for component_id, amount in segment_adjustments.items():
            overtime_by_component[component_id] += amount
    period_overtime_adjustments = {
        component_id: _money(amount)
        for component_id, amount in overtime_by_component.items()
    }

    aggregate: dict[int, dict[str, object]] = {}
    segment_snapshots: list[dict[str, object]] = []
    with localcontext() as context:
        context.prec = 50
        for segment, segment_dates, component_amounts, payable_fraction in segment_inputs:
            segment_key = (segment.segment_start, segment.segment_end)
            ot_adjustments = overtime_by_segment.get(segment_key, {})
            overtime_details = overtime_details_by_segment.get(segment_key, [])
            component_snapshots: list[dict[str, object]] = []
            for component in segment.compensation.revision.components:
                amount, base_amount, order = component_amounts[component.salary_component_id]
                if component.component_type == "EARNING":
                    regular_final = _money(amount * payable_fraction)
                    adjustment = regular_final - amount
                else:
                    regular_final = amount
                    adjustment = _ZERO
                segment_ot_amount = ot_adjustments.get(component.salary_component_id, _ZERO)
                segment_final_before_period_ot_rounding = regular_final + segment_ot_amount

                record = aggregate.get(component.salary_component_id)
                if record is None:
                    record = {
                        "component_name": component.component_name,
                        "component_type": component.component_type,
                        "compensation_amount": _ZERO,
                        "workforce_adjustment": _ZERO,
                        "overtime_adjustment": _ZERO,
                        "regular_final_amount": _ZERO,
                        "final_amount": _ZERO,
                        "calculation_order": order,
                    }
                    aggregate[component.salary_component_id] = record
                elif record["component_type"] != component.component_type:
                    raise PayrollCalculationError(
                        "INVALID_COMPENSATION_CONFIGURATION",
                        "A salary component changes type across compensation segments.",
                    )
                record["compensation_amount"] = (
                    Decimal(record["compensation_amount"]) + amount
                )
                record["workforce_adjustment"] = (
                    Decimal(record["workforce_adjustment"]) + adjustment
                )
                record["regular_final_amount"] = (
                    Decimal(record["regular_final_amount"]) + regular_final
                )
                component_snapshots.append(
                    {
                        "component_id": component.salary_component_id,
                        "component_name": component.component_name,
                        "component_type": component.component_type,
                        "calculation_mode": component.calculation_type,
                        "configured_fixed_amount": _decimal_string(component.fixed_amount),
                        "configured_percentage_value": _decimal_string(component.percentage_value),
                        "base_component_id": component.base_component_id,
                        "base_amount": _decimal_string(base_amount),
                        "compensation_amount": _decimal_string(amount),
                        "workforce_adjustment": _decimal_string(adjustment),
                        "overtime_adjustment": _decimal_string(segment_ot_amount),
                        "final_amount": _decimal_string(
                            segment_final_before_period_ot_rounding
                        ),
                        "calculation_order": order,
                    }
                )
            segment_snapshots.append(
                {
                    "salary_assignment_id": segment.compensation.assignment.salary_assignment_id,
                    "salary_revision_id": segment.compensation.revision.salary_revision_id,
                    "segment_start": segment.segment_start.isoformat(),
                    "segment_end": segment.segment_end.isoformat(),
                    "segment_working_day_count": len(segment_dates),
                    "segment_payable_fraction": _decimal_string(payable_fraction),
                    "components": component_snapshots,
                    "overtime": overtime_details,
                }
            )

    for component_id, record in aggregate.items():
        overtime_adjustment = period_overtime_adjustments.get(component_id, _ZERO)
        record["overtime_adjustment"] = overtime_adjustment
        record["final_amount"] = _money(
            Decimal(record["regular_final_amount"]) + overtime_adjustment
        )

    results = tuple(
        _CalculatedComponent(
            salary_component_id=component_id,
            component_name=str(record["component_name"]),
            component_type=str(record["component_type"]),
            compensation_amount=Decimal(record["compensation_amount"]),
            workforce_adjustment=Decimal(record["workforce_adjustment"]),
            overtime_adjustment=Decimal(record["overtime_adjustment"]),
            final_amount=Decimal(record["final_amount"]),
            calculation_order=int(record["calculation_order"]),
        )
        for component_id, record in aggregate.items()
    )
    gross = sum(
        (item.final_amount for item in results if item.component_type == "EARNING"),
        _ZERO,
    )
    deductions = sum(
        (item.final_amount for item in results if item.component_type == "DEDUCTION"),
        _ZERO,
    )
    net = gross - deductions
    if salary_assignment_id <= 0:
        raise PayrollCalculationError(
            "INVALID_COMPENSATION_ASSIGNMENT", "Processing-start salary assignment is invalid."
        )

    result_snapshot = {
        **payload,
        "financial_calculation": {
            "calculation_status": "CALCULATED",
            "payroll_run_id": payroll_run_id,
            "employee_id": employee_id,
            "attempt_number": snapshot.attempt_number,
            "rounding": "ROUND_HALF_UP to 0.01 at component boundaries",
            "segments": segment_snapshots,
            "components": [
                {
                    "component_id": item.salary_component_id,
                    "component_name": item.component_name,
                    "component_type": item.component_type,
                    "compensation_amount": _decimal_string(item.compensation_amount),
                    "workforce_adjustment": _decimal_string(item.workforce_adjustment),
                    "overtime_adjustment": _decimal_string(item.overtime_adjustment),
                    "final_amount": _decimal_string(item.final_amount),
                    "calculation_order": item.calculation_order,
                }
                for item in results
            ],
            "gross_earnings": _decimal_string(gross),
            "total_deductions": _decimal_string(deductions),
            "net_salary": _decimal_string(net),
        },
    }
    rule_metadata = result_snapshot.get("rule_metadata")
    if isinstance(rule_metadata, dict):
        result_snapshot["rule_metadata"] = {
            **rule_metadata,
            "financial_calculation": "performed",
        }
    return EmployeePayrollCalculation(
        payroll_run_id=payroll_run_id,
        employee_id=employee_id,
        salary_assignment_id=salary_assignment_id,
        gross_earnings=gross,
        total_deductions=deductions,
        net_salary=net,
        components=results,
        workforce_snapshot=result_snapshot,
    )


def _calculate_segment_components(
    segment: CompensationSegment,
    segment_working_days: int,
    monthly_working_days: int,
) -> tuple[dict[int, tuple[Decimal, Decimal | None, int]], dict[int, int]]:
    components = {
        component.salary_component_id: component
        for component in segment.compensation.revision.components
    }
    if len(components) != len(segment.compensation.revision.components):
        raise PayrollCalculationError(
            "INVALID_COMPENSATION_CONFIGURATION", "Duplicate salary component in revision."
        )
    values: dict[int, tuple[Decimal, Decimal | None, int]] = {}
    states: dict[int, int] = {}
    ordered_ids: list[int] = []

    def evaluate(component_id: int) -> Decimal:
        state = states.get(component_id, 0)
        if state == 1:
            raise PayrollCalculationError(
                "SALARY_COMPONENT_CYCLE", "Salary component dependencies contain a cycle."
            )
        if state == 2:
            return values[component_id][0]
        component = components.get(component_id)
        if component is None:
            raise PayrollCalculationError(
                "PERCENTAGE_BASE_MISSING",
                f"Percentage component base {component_id} is not in the salary revision.",
            )
        states[component_id] = 1
        if component.component_type not in {"EARNING", "DEDUCTION"}:
            raise PayrollCalculationError(
                "INVALID_COMPENSATION_CONFIGURATION", "Invalid salary component type."
            )
        base_amount: Decimal | None = None
        if component.calculation_type == "FIXED":
            if component.fixed_amount is None or component.fixed_amount < 0:
                raise PayrollCalculationError(
                    "INVALID_COMPENSATION_CONFIGURATION", "Invalid fixed component amount."
                )
            amount = (
                Decimal(component.fixed_amount)
                * Decimal(segment_working_days)
                / Decimal(monthly_working_days)
            )
        elif component.calculation_type == "PERCENTAGE":
            if component.base_component_id is None or component.percentage_value is None:
                raise PayrollCalculationError(
                    "PERCENTAGE_BASE_MISSING", "Percentage component has no valid base."
                )
            if component.percentage_value < 0:
                raise PayrollCalculationError(
                    "INVALID_COMPENSATION_CONFIGURATION", "Invalid percentage component rate."
                )
            base_amount = evaluate(component.base_component_id)
            amount = base_amount * Decimal(component.percentage_value) / Decimal(100)
        else:
            raise PayrollCalculationError(
                "INVALID_COMPENSATION_CONFIGURATION", "Invalid component calculation type."
            )
        amount = _money(amount)
        values[component_id] = (amount, base_amount, len(ordered_ids))
        ordered_ids.append(component_id)
        states[component_id] = 2
        return amount

    for component_id in sorted(components):
        evaluate(component_id)
    return values, {component_id: order for order, component_id in enumerate(ordered_ids)}


def _payable_fraction_for_date(
    day: date,
    attendance: dict[str, object] | None,
    allocations: list[dict[str, object]],
) -> Decimal:
    status = None if attendance is None else attendance.get("effective_status")
    missing = attendance is None or bool(attendance.get("missing_attendance"))
    if missing or status == "HOLIDAY":
        base = _ONE
    elif status == "PRESENT":
        base = _ONE
    elif status == "HALF_DAY":
        base = Decimal("0.50")
    elif status == "ABSENT":
        base = _ZERO
    elif status == "ON_LEAVE":
        approved = [item for item in allocations if item.get("status") == "APPROVED"]
        if len(approved) != 1:
            raise PayrollCalculationError(
                "ON_LEAVE_APPROVED_ALLOCATION_MISSING",
                f"ON_LEAVE Attendance on {day.isoformat()} has no unique approved Leave allocation.",
            )
        allocation = approved[0]
        fraction = _decimal(allocation.get("day_fraction"))
        treatment = allocation.get("treatment")
        if treatment == "PAID":
            return _bounded(fraction)
        if treatment == "UNPAID":
            return _bounded(_ONE - fraction)
        raise PayrollCalculationError(
            "INVALID_LEAVE_TREATMENT",
            f"ON_LEAVE Attendance on {day.isoformat()} has an invalid Leave treatment.",
        )
    else:
        raise PayrollCalculationError(
            "INVALID_WORKFORCE_SNAPSHOT",
            f"Working date {day.isoformat()} has an unsupported Attendance state.",
        )

    for allocation in allocations:
        if allocation.get("status") != "APPROVED":
            continue
        fraction = _decimal(allocation.get("day_fraction"))
        treatment = allocation.get("treatment")
        if treatment == "PAID":
            base += _ONE
        elif treatment == "UNPAID":
            base -= fraction
        else:
            raise PayrollCalculationError(
                "INVALID_LEAVE_TREATMENT",
                f"Approved Leave on {day.isoformat()} has an invalid treatment.",
            )
    return _bounded(base)


def _calculate_overtime_for_segments(
    segments: Sequence[CompensationSegment],
    calendars: dict[date, dict[str, object]],
    attendance: dict[date, dict[str, object]],
    policies: dict[date, dict[str, object]],
    monthly_working_days: int,
    anomalies: dict[date, list[dict[str, object]]],
) -> tuple[
    dict[tuple[date, date], dict[int, Decimal]],
    dict[tuple[date, date], list[dict[str, object]]],
]:
    def segment_for(day: date) -> CompensationSegment | None:
        return next(
            (item for item in segments if item.segment_start <= day <= item.segment_end),
            None,
        )

    for segment in segments:
        bases = [
            component
            for component in segment.compensation.revision.components
            if component.is_overtime_base
        ]
        if len(bases) != 1:
            code = "OVERTIME_BASE_MISSING" if not bases else "OVERTIME_BASE_AMBIGUOUS"
            raise PayrollCalculationError(code, "Salary revision must have exactly one OT base.")
        base = bases[0]
        if base.component_type != "EARNING" or base.calculation_type != "FIXED" or base.fixed_amount is None:
            raise PayrollCalculationError(
                "INVALID_OVERTIME_BASE_CONFIGURATION", "OT base must be a FIXED EARNING component."
            )

    adjustments: dict[tuple[date, date], dict[int, Decimal]] = defaultdict(
        lambda: defaultdict(lambda: _ZERO)
    )
    details: dict[tuple[date, date], list[dict[str, object]]] = defaultdict(list)
    for day, row in sorted(attendance.items()):
        if segment_for(day) is None:
            continue
        row_anomalies = anomalies.get(day, [])
        blocking_anomalies = [
            item
            for item in row_anomalies
            if str(item.get("code", "UNKNOWN_ATTENDANCE_ANOMALY"))
            not in _NONBLOCKING_DST_ANOMALIES
        ]
        if blocking_anomalies:
            raise _blocking_overtime_anomaly(blocking_anomalies[0], day)
        if row_anomalies:
            # The only nonblocking timestamp anomalies are the approved DST cases.
            continue
        if row.get("missing_attendance"):
            # Missing Attendance is not a malformed timestamp interval. The
            # approved regular-pay rule applies; no OT is inferred without a row.
            continue
        if row.get("effective_status") in {"ABSENT", "HALF_DAY"}:
            continue
        check_in_value = row.get("check_in")
        check_out_value = row.get("check_out")
        if check_in_value is None or check_out_value is None:
            missing_field = "check-in" if check_in_value is None else "check-out"
            code = "MISSING_CHECK_IN" if check_in_value is None else "MISSING_CHECK_OUT"
            attendance_id = row.get("attendance_id")
            raise PayrollCalculationError(
                code,
                f"Attendance {attendance_id} on {day.isoformat()} has no {missing_field} time; OT cannot be determined reliably.",
            )
        first_calendar = calendars.get(day)
        if first_calendar is None:
            raise PayrollCalculationError(
                "INVALID_WORKFORCE_SNAPSHOT", f"Calendar classification missing on {day.isoformat()}."
            )
        zone = ZoneInfo(str(first_calendar["timezone"]))
        check_in = _parse_datetime(check_in_value)
        check_out = _parse_datetime(check_out_value)
        start, start_error = OvertimeDerivationService._as_local_instant(check_in, zone)
        end, end_error = OvertimeDerivationService._as_local_instant(check_out, zone)
        if start_error or end_error:
            # Reader snapshots record these same DST anomalies. Keep this defensive
            # path nonblocking when a directly constructed snapshot omits the row.
            continue
        if start.astimezone(zone).date() != day:
            raise PayrollCalculationError(
                "CHECK_IN_DATE_MISMATCH",
                f"Attendance {row.get('attendance_id')} check-in on {day.isoformat()} does not match the Work Calendar date.",
            )
        cursor = start.astimezone(timezone.utc)
        end_utc = end.astimezone(timezone.utc)
        if end_utc < cursor:
            raise PayrollCalculationError(
                "INVALID_ATTENDANCE_INTERVAL",
                f"Attendance {row.get('attendance_id')} on {day.isoformat()} has a reversed interval; OT cannot be determined reliably.",
            )
        if end_utc - cursor > timedelta(hours=24):
            raise PayrollCalculationError(
                "OVER_24_HOURS",
                f"Attendance {row.get('attendance_id')} on {day.isoformat()} exceeds 24 hours; OT cannot be determined reliably.",
            )
        if end_utc == cursor:
            continue
        first_timezone = str(first_calendar["timezone"])
        while cursor < end_utc:
            local_cursor = cursor.astimezone(zone)
            work_date = local_cursor.date()
            calendar = calendars.get(work_date)
            if calendar is None:
                raise PayrollCalculationError(
                    "OVERTIME_CALENDAR_INPUT_MISSING",
                    f"Frozen Work Calendar input missing on overtime date {work_date.isoformat()}.",
                )
            current_timezone = str(calendar.get("timezone", ""))
            if current_timezone != first_timezone:
                raise PayrollCalculationError(
                    "CALENDAR_TIMEZONE_CHANGED_DURING_INTERVAL",
                    f"Attendance {row.get('attendance_id')} from {day.isoformat()} crosses from calendar timezone {first_timezone} to {current_timezone}; OT cannot be calculated consistently.",
                )
            try:
                next_midnight = datetime.combine(work_date + timedelta(days=1), time.min)
                boundary_local, boundary_error = OvertimeDerivationService._as_local_instant(
                    next_midnight, ZoneInfo(str(calendar["timezone"]))
                )
            except (KeyError, ValueError) as exc:
                raise PayrollCalculationError(
                    "INVALID_WORKFORCE_SNAPSHOT", "Invalid frozen calendar timezone."
                ) from exc
            if boundary_error:
                raise PayrollCalculationError(
                    "INVALID_ATTENDANCE_INTERVAL",
                    f"Unable to resolve local midnight on {work_date.isoformat()}.",
                )
            boundary = boundary_local.astimezone(timezone.utc)
            interval_end = min(boundary, end_utc)
            if interval_end <= cursor:
                raise PayrollCalculationError(
                    "INVALID_ATTENDANCE_INTERVAL", "Unable to split overtime at local midnight."
                )
            worked_minutes = _duration_minutes(interval_end - cursor)
            working = calendar.get("classification") == "WORKING_DAY"
            overtime_minutes = max(
                _ZERO,
                worked_minutes - Decimal(480) if working else worked_minutes,
            )
            policy = policies.get(work_date)
            if overtime_minutes > 0:
                day_segment = segment_for(work_date)
                if day_segment is None:
                    raise PayrollCalculationError(
                        "OVERTIME_COMPENSATION_SEGMENT_MISSING",
                        f"No frozen compensation segment covers overtime date {work_date.isoformat()}.",
                    )
                base_candidates = [
                    component
                    for component in day_segment.compensation.revision.components
                    if component.is_overtime_base
                ]
                if len(base_candidates) != 1:
                    code = "OVERTIME_BASE_MISSING" if not base_candidates else "OVERTIME_BASE_AMBIGUOUS"
                    raise PayrollCalculationError(code, "Salary revision must have exactly one OT base.")
                base = base_candidates[0]
                if not working and (policy is None or policy.get("multiplier") is None):
                    raise PayrollCalculationError(
                        "OVERTIME_POLICY_MISSING",
                        f"Frozen overtime policy missing on {work_date.isoformat()}.",
                    )
                multiplier = Decimal(1) if working else _decimal(policy.get("multiplier"))
                with localcontext() as context:
                    context.prec = 50
                    hourly_rate = (
                        Decimal(base.fixed_amount)
                        / Decimal(monthly_working_days)
                        / Decimal(8)
                    )
                    hours = overtime_minutes / Decimal(60)
                    amount = hours * hourly_rate * multiplier
                segment_key = (day_segment.segment_start, day_segment.segment_end)
                adjustments[segment_key][base.salary_component_id] += amount
                details[segment_key].append(
                    {
                        "attendance_date": day.isoformat(),
                        "overtime_date": work_date.isoformat(),
                        "overtime_minutes": _decimal_string(overtime_minutes),
                        "overtime_hours": _decimal_string(hours),
                        "monthly_ot_base": _decimal_string(Decimal(base.fixed_amount)),
                        "monthly_working_day_count": monthly_working_days,
                        "hourly_rate": _decimal_string(hourly_rate),
                        "multiplier": _decimal_string(multiplier),
                        "policy_version_id": None if policy is None else policy.get("policy_version_id"),
                        "policy_version_number": None if policy is None else policy.get("policy_version_number"),
                        "overtime_base_component_id": base.salary_component_id,
                        "interval_amount_unrounded": _decimal_string(amount),
                        "calendar_classification": calendar.get("classification"),
                    }
                )
            cursor = interval_end
    return (
        {key: dict(values) for key, values in adjustments.items()},
        dict(details),
    )


def _blocking_overtime_anomaly(
    anomaly: dict[str, object], fallback_date: date | None
) -> PayrollCalculationError:
    code = str(anomaly.get("code", "INVALID_ATTENDANCE_INTERVAL"))
    affected_date = anomaly.get("affected_date")
    if affected_date is None:
        affected_date = fallback_date
    attendance_id = anomaly.get("attendance_id")
    details = str(anomaly.get("message", "OT timestamp input is unusable."))
    return PayrollCalculationError(
        code,
        f"Attendance {attendance_id} on {affected_date} has blocking OT anomaly {code}: {details}",
    )


def _duration_minutes(duration: timedelta) -> Decimal:
    microseconds = ((duration.days * 86400 + duration.seconds) * 1_000_000) + duration.microseconds
    with localcontext() as context:
        context.prec = 50
        return Decimal(microseconds) / Decimal(60_000_000)


def _index_by_date(value: object, field: str) -> dict[date, dict[str, object]]:
    result: dict[date, dict[str, object]] = {}
    for item in _mapping_list(value):
        day = _as_date(item.get(field))
        if day in result:
            raise PayrollCalculationError(
                "INVALID_WORKFORCE_SNAPSHOT", f"Duplicate frozen input for {day.isoformat()}."
            )
        result[day] = item
    return result


def _mapping_list(value: object) -> list[dict[str, object]]:
    if not isinstance(value, (list, tuple)):
        raise PayrollCalculationError(
            "INVALID_WORKFORCE_SNAPSHOT", "Expected a list in frozen Workforce snapshot."
        )
    result: list[dict[str, object]] = []
    for item in value:
        if not isinstance(item, Mapping):
            raise PayrollCalculationError(
                "INVALID_WORKFORCE_SNAPSHOT", "Frozen Workforce item is not an object."
            )
        result.append(dict(item))
    return result


def _thaw(value: object) -> object:
    if isinstance(value, MappingProxyType) or isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_thaw(item) for item in value]
    return value


def _as_date(value: object) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    return date.fromisoformat(str(value))


def _parse_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


def _decimal(value: object) -> Decimal:
    result = value if isinstance(value, Decimal) else Decimal(str(value))
    if not result.is_finite():
        raise PayrollCalculationError(
            "INVALID_FINANCIAL_INPUT", "Monetary and Workforce values must be finite."
        )
    return result


def _decimal_string(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


def _integer(value: object) -> int:
    if isinstance(value, bool):
        raise ValueError("Boolean is not a valid integer input.")
    return int(value)


def _bounded(value: Decimal) -> Decimal:
    return min(_ONE, max(_ZERO, value))


def _money(value: Decimal) -> Decimal:
    return _decimal(value).quantize(_CENT, rounding=ROUND_HALF_UP)
