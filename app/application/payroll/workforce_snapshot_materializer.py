from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from app.application.common.unit_of_work import UnitOfWork
from app.application.payroll.payroll_processing_issue_service import (
    PayrollProcessingIssueService,
)
from app.application.payroll.employee_eligibility_resolver import (
    EmployeeEligibilityResult,
)
from app.application.payroll.schemas import PayrollProcessingIssueCreateRequest
from app.application.compensation.contracts import SalaryComponentSnapshot
from app.application.workforce.payroll_input_contracts import (
    CompensationSegmentInput,
    WorkforcePayrollInputResult,
)
from app.application.workforce.workforce_payroll_input_reader import (
    WorkforcePayrollInputReader,
)
from app.domain.payroll.payroll_run_workforce_snapshot import (
    PayrollRunWorkforceSnapshot,
)


_RUN_LEVEL_CONDITIONS = {
    "MISSING_CALENDAR_CLASSIFICATION",
    "CONFLICTING_CALENDAR_CLASSIFICATION",
    "MISSING_OVERTIME_POLICY",
    "CONFLICTING_OVERTIME_POLICY",
}


@dataclass(frozen=True)
class WorkforceSnapshotMaterialization:
    snapshots: tuple[PayrollRunWorkforceSnapshot, ...]
    pending_issues: tuple[PayrollProcessingIssueCreateRequest, ...]


class WorkforceSnapshotMaterializer:
    """Collects immutable Decision 30 input snapshots inside the caller's read boundary."""

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow
        self.reader = WorkforcePayrollInputReader(uow)

    def collect(
        self,
        *,
        payroll_run_id: int,
        attempt_number: int,
        payroll_year: int,
        payroll_month: int,
        snapshot_at: datetime,
        eligibility: EmployeeEligibilityResult,
    ) -> WorkforceSnapshotMaterialization:
        snapshots: list[PayrollRunWorkforceSnapshot] = []
        pending_issues: list[PayrollProcessingIssueCreateRequest] = []
        recorded_run_conditions: set[tuple[str, date | None]] = set()
        monthly_working_day_count = self.reader.calendar.working_day_count(
            payroll_year, payroll_month
        )

        for eligible_employee in eligibility.eligible_employees:
            employee_id = eligible_employee.employee_id
            inputs = self.reader.read(
                employee_id,
                eligible_employee.applicable_employment_start,
                eligible_employee.applicable_employment_end,
            )
            for condition in inputs.conditions:
                if condition.code in _RUN_LEVEL_CONDITIONS:
                    key = (condition.code, condition.affected_date)
                    if key in recorded_run_conditions:
                        continue
                    recorded_run_conditions.add(key)
                    issue_employee_id = None
                else:
                    issue_employee_id = employee_id
                pending_issues.append(
                    PayrollProcessingIssueCreateRequest(
                        payroll_run_id=payroll_run_id,
                        employee_id=issue_employee_id,
                        issue_code=condition.code,
                        issue_message=condition.message,
                        status="OPEN",
                    )
                )

            payload = _snapshot_payload(
                inputs,
                payroll_run_id=payroll_run_id,
                payroll_year=payroll_year,
                payroll_month=payroll_month,
                attempt_number=attempt_number,
                snapshot_at=snapshot_at,
                monthly_working_day_count=monthly_working_day_count,
            )
            snapshots.append(
                PayrollRunWorkforceSnapshot(
                    payroll_run_id=payroll_run_id,
                    employee_id=employee_id,
                    attempt_number=attempt_number,
                    snapshot_at=snapshot_at,
                    snapshot=payload,
                )
            )

        return WorkforceSnapshotMaterialization(
            snapshots=tuple(snapshots),
            pending_issues=tuple(pending_issues),
        )

    def persist(
        self,
        materialization: WorkforceSnapshotMaterialization,
        expected_attempt_number: int,
        additional_issues: tuple[PayrollProcessingIssueCreateRequest, ...] = (),
    ) -> tuple[int, ...]:
        issue_ids: list[int] = []
        recorded_issues: set[tuple[int | None, str, str]] = set()
        for request in (*additional_issues, *materialization.pending_issues):
            key = (request.employee_id, request.issue_code, request.issue_message)
            if key in recorded_issues:
                continue
            recorded_issues.add(key)
            issue = PayrollProcessingIssueService(self.uow).create(
                request, expected_attempt_number, commit=False
            )
            issue_ids.append(issue.payroll_issue_id)
        for snapshot in materialization.snapshots:
            self.uow.payroll_run_workforce_snapshots.add(
                snapshot, expected_attempt_number
            )
        return tuple(issue_ids)


def _snapshot_payload(
    inputs: WorkforcePayrollInputResult,
    *,
    payroll_run_id: int,
    payroll_year: int,
    payroll_month: int,
    attempt_number: int,
    snapshot_at: datetime,
    monthly_working_day_count: int,
) -> dict[str, object]:
    working_dates = {
        item.date
        for item in inputs.calendar_days
        if item.classification == "WORKING_DAY"
    }
    attendance = []
    for item in inputs.attendance:
        missing = item.attendance_id is None
        default_present = missing and item.attendance_date in working_dates
        effective_status = "PRESENT" if default_present else item.status
        attendance.append(
            {
                "attendance_id": item.attendance_id,
                "employee_id": item.employee_id,
                "date": item.attendance_date,
                "status": item.status,
                "effective_status": effective_status,
                "check_in": item.check_in,
                "check_out": item.check_out,
                "missing_attendance": missing,
                "payable_effect": effective_status,
            }
        )

    return _json_value(
        {
            "snapshot_format_version": 1,
            "payroll_run_id": payroll_run_id,
            "employee_id": inputs.employee_id,
            "payroll_period": {
                "year": payroll_year,
                "month": payroll_month,
            },
            "processing_range": {
                "start": inputs.range_start,
                "end": inputs.range_end,
            },
            "attempt_number": attempt_number,
            "snapshot_at": snapshot_at,
            "monthly_working_day_count": monthly_working_day_count,
            "rule_metadata": {
                "architecture_decisions": [
                    "Decision 24",
                    "Decision 27",
                    "Decision 28",
                    "Decision 29",
                    "Decision 30",
                    "Decision 31",
                ],
                "financial_calculation": "not_performed",
            },
            "attendance": attendance,
            "leave_allocations": [
                {
                    "leave_request_id": item.leave_request_id,
                    "leave_type_id": item.leave_type_id,
                    "date": item.leave_date,
                    "status": item.status,
                    "treatment": item.payroll_treatment,
                    "day_fraction": item.day_fraction,
                    "payable_effect": {
                        "applies": item.status == "APPROVED"
                        and item.payroll_treatment in {"PAID", "UNPAID"},
                        "treatment": item.payroll_treatment,
                        "day_fraction": item.day_fraction,
                    },
                }
                for item in inputs.leave_allocations
            ],
            "calendar_days": [
                {
                    "calendar_version_id": item.calendar_version_id,
                    "calendar_version_number": item.calendar_version_number,
                    "timezone": item.timezone,
                    "date": item.date,
                    "classification": item.classification,
                    "scheduled_minutes": item.scheduled_minutes,
                }
                for item in inputs.calendar_days
            ],
            "overtime_policies": [
                {
                    "policy_version_id": item.policy_id,
                    "policy_version_number": item.version_number,
                    "date": item.date,
                    "effective_from": item.effective_from,
                    "effective_to": item.effective_to,
                    "multiplier": item.multiplier,
                }
                for item in inputs.overtime_policies
            ],
            "compensation_segments": [
                _compensation_segment(item) for item in inputs.compensation_segments
            ],
            "anomalies": [
                {
                    "code": item.code,
                    "message": item.message,
                    "attendance_id": item.attendance_id,
                    "affected_date": item.affected_date,
                }
                for item in inputs.anomalies
            ],
            "input_conditions": [
                {
                    "code": item.code,
                    "message": item.message,
                    "employee_id": item.employee_id,
                    "affected_date": item.affected_date,
                }
                for item in inputs.conditions
            ],
        }
    )


def _compensation_segment(segment: CompensationSegmentInput) -> dict[str, object]:
    return {
        "employee_id": segment.employee_id,
        "salary_assignment_id": segment.assignment_id,
        "salary_revision_id": segment.salary_revision_id,
        "segment_start": segment.segment_start,
        "segment_end": segment.segment_end,
        "components": [_component(component) for component in segment.components],
        "overtime_base_components": [
            {
                **_component(component),
                "overtime_base_amount": component.fixed_amount,
            }
            for component in segment.overtime_base_components
        ],
        "conditions": [
            {
                "code": condition.code,
                "message": condition.message,
                "employee_id": condition.employee_id,
                "affected_date": condition.affected_date,
            }
            for condition in segment.conditions
        ],
    }


def _component(component: SalaryComponentSnapshot) -> dict[str, object]:
    return {
        "salary_component_id": component.salary_component_id,
        "component_name": component.component_name,
        "component_type": component.component_type,
        "calculation_type": component.calculation_type,
        "fixed_amount": component.fixed_amount,
        "percentage_value": component.percentage_value,
        "base_component_id": component.base_component_id,
        "is_overtime_base": component.is_overtime_base,
    }


def _json_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value
