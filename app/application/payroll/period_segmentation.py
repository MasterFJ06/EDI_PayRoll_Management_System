from dataclasses import dataclass
from datetime import date

from app.application.common.unit_of_work import UnitOfWork
from app.application.compensation.contracts import EmployeeCompensationSnapshot
from app.application.compensation.segmentation import (
    CompensationSegment,
    CompensationSegmentationResolver,
)
from app.application.payroll.compensation_snapshot import CompensationSnapshot
from app.application.payroll.employee_eligibility_resolver import (
    EmployeeEligibilityResult,
)
from app.application.payroll.payroll_processing_issue_service import (
    PayrollProcessingIssueService,
)
from app.application.payroll.schemas import PayrollProcessingIssueCreateRequest


# Preserve the existing Payroll 2B-4 public result terminology.
PayrollPeriodSegment = CompensationSegment


@dataclass(frozen=True)
class EmployeeProcessingRange:
    employee_id: int
    range_start: date
    range_end: date


@dataclass(frozen=True)
class PeriodSegmentationResult:
    payroll_run_id: int
    period_start: date
    period_end: date
    employee_ranges: tuple[EmployeeProcessingRange, ...]
    segments: tuple[PayrollPeriodSegment, ...]
    blocked_employee_ids: tuple[int, ...]
    blocking_issue_ids: tuple[int, ...]


class PayrollPeriodSegmenter:
    """Payroll 2B-4 adapter that persists the core's blocking conditions."""

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow
        self.resolver = CompensationSegmentationResolver(uow)

    def resolve(
        self,
        payroll_run_id: int,
        attempt_number: int,
        eligibility: EmployeeEligibilityResult,
        compensation_snapshot: CompensationSnapshot,
        *,
        deferred_issues: list[PayrollProcessingIssueCreateRequest] | None = None,
    ) -> PeriodSegmentationResult:
        snapshot_employees = {
            item.employee_id: item for item in compensation_snapshot.employees
        }
        employee_ranges: list[EmployeeProcessingRange] = []
        segments: list[PayrollPeriodSegment] = []
        blocked_employee_ids: list[int] = []
        issue_ids: list[int | None] = []

        for eligible in eligibility.eligible_employees:
            employee_range = EmployeeProcessingRange(
                employee_id=eligible.employee_id,
                range_start=eligible.applicable_employment_start,
                range_end=eligible.applicable_employment_end,
            )
            employee_ranges.append(employee_range)

            # Phase 2B-3 already persists the issue when this snapshot is absent.
            current_compensation = snapshot_employees.get(eligible.employee_id)
            if current_compensation is None:
                continue

            result = self.resolver.resolve(
                employee_id=employee_range.employee_id,
                range_start=employee_range.range_start,
                range_end=employee_range.range_end,
                current_compensation=current_compensation,
            )
            if result.conditions:
                blocked_employee_ids.append(eligible.employee_id)
                condition = result.conditions[0]
                issue_ids.append(
                    self._record_issue(
                        payroll_run_id,
                        attempt_number,
                        eligible.employee_id,
                        condition.code,
                        condition.message,
                        deferred_issues,
                    )
                )
                continue
            segments.extend(result.segments)

        return PeriodSegmentationResult(
            payroll_run_id=payroll_run_id,
            period_start=eligibility.payroll_period_start,
            period_end=eligibility.payroll_period_end,
            employee_ranges=tuple(employee_ranges),
            segments=tuple(segments),
            blocked_employee_ids=tuple(blocked_employee_ids),
            blocking_issue_ids=tuple(issue_id for issue_id in issue_ids if issue_id is not None),
        )

    def _record_issue(
        self,
        payroll_run_id: int,
        attempt_number: int,
        employee_id: int,
        issue_code: str,
        issue_message: str,
        deferred_issues: list[PayrollProcessingIssueCreateRequest] | None,
    ) -> int | None:
        request = PayrollProcessingIssueCreateRequest(
            payroll_run_id=payroll_run_id,
            employee_id=employee_id,
            issue_code=issue_code,
            issue_message=issue_message,
            status="OPEN",
        )
        if deferred_issues is not None:
            deferred_issues.append(request)
            return None
        response = PayrollProcessingIssueService(self.uow).create(
            request, attempt_number
        )
        return response.payroll_issue_id
