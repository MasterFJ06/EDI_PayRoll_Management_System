from dataclasses import dataclass
from datetime import date, datetime

from app.application.common.unit_of_work import UnitOfWork
from app.application.compensation.contracts import (
    EmployeeCompensationSnapshot,
    EmployeeSalaryAssignmentSnapshot,
    SalaryComponentSnapshot,
    SalaryRevisionSnapshot,
)
from app.application.payroll.payroll_processing_issue_service import (
    PayrollProcessingIssueService,
)
from app.application.payroll.schemas import PayrollProcessingIssueCreateRequest
from app.domain.compensation.salary_component import SalaryComponent
from app.domain.compensation.salary_revision_component import (
    SalaryRevisionComponent,
)
from app.domain.shared.exceptions import BusinessRuleViolation


@dataclass(frozen=True)
class CompensationSnapshot:
    payroll_run_id: int
    processing_started_at: datetime
    snapshot_date: date
    employees: tuple[EmployeeCompensationSnapshot, ...]


@dataclass(frozen=True)
class CompensationSnapshotResolution:
    snapshot: CompensationSnapshot
    blocking_issue_ids: tuple[int, ...]


class CompensationSnapshotResolver:
    """Resolves immutable compensation inputs for eligible employees at run claim."""

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def resolve(
        self,
        payroll_run_id: int,
        attempt_number: int,
        processing_started_at: datetime,
        eligible_employee_ids: tuple[int, ...],
        *,
        deferred_issues: list[PayrollProcessingIssueCreateRequest] | None = None,
    ) -> CompensationSnapshotResolution:
        snapshot_date = processing_started_at.date()
        employee_snapshots: list[EmployeeCompensationSnapshot] = []
        issue_ids: list[int | None] = []

        for employee_id in eligible_employee_ids:
            assignments = self.uow.employee_salary_assignments.get_applicable_for_employee(
                employee_id,
                snapshot_date,
            )
            if not assignments:
                issue_ids.append(
                    self._record_issue(
                        payroll_run_id,
                        attempt_number,
                        employee_id,
                        "SALARY_ASSIGNMENT_MISSING",
                        "No salary assignment is applicable at the processing start.",
                        deferred_issues,
                    )
                )
                continue
            if len(assignments) > 1:
                issue_ids.append(
                    self._record_issue(
                        payroll_run_id,
                        attempt_number,
                        employee_id,
                        "SALARY_ASSIGNMENT_AMBIGUOUS",
                        "Multiple salary assignments are applicable at the processing start.",
                        deferred_issues,
                    )
                )
                continue

            assignment = assignments[0]
            revision = self.uow.salary_revisions.get_by_id(
                assignment.salary_revision_id
            )
            if revision is None:
                issue_ids.append(
                    self._record_issue(
                        payroll_run_id,
                        attempt_number,
                        employee_id,
                        "SALARY_REVISION_MISSING",
                        "The salary assignment references a missing salary revision.",
                        deferred_issues,
                    )
                )
                continue
            if not _is_effective(revision.effective_from, revision.effective_to, snapshot_date):
                issue_ids.append(
                    self._record_issue(
                        payroll_run_id,
                        attempt_number,
                        employee_id,
                        "SALARY_REVISION_NOT_EFFECTIVE",
                        "The referenced salary revision is not effective at processing start.",
                        deferred_issues,
                    )
                )
                continue

            component_snapshots, issue_id = self._snapshot_components(
                payroll_run_id,
                attempt_number,
                employee_id,
                revision.salary_revision_id,
                deferred_issues,
            )
            if component_snapshots is None:
                assert issue_id is not None
                issue_ids.append(issue_id)
                continue

            employee_snapshots.append(
                EmployeeCompensationSnapshot(
                    employee_id=employee_id,
                    assignment=EmployeeSalaryAssignmentSnapshot(
                        salary_assignment_id=assignment.salary_assignment_id,
                        salary_revision_id=assignment.salary_revision_id,
                        effective_from=assignment.effective_from,
                        effective_to=assignment.effective_to,
                    ),
                    revision=SalaryRevisionSnapshot(
                        salary_revision_id=revision.salary_revision_id,
                        salary_structure_id=revision.salary_structure_id,
                        revision_number=revision.revision_number,
                        effective_from=revision.effective_from,
                        effective_to=revision.effective_to,
                        components=component_snapshots,
                    ),
                )
            )

        return CompensationSnapshotResolution(
            snapshot=CompensationSnapshot(
                payroll_run_id=payroll_run_id,
                processing_started_at=processing_started_at,
                snapshot_date=snapshot_date,
                employees=tuple(employee_snapshots),
            ),
            blocking_issue_ids=tuple(issue_id for issue_id in issue_ids if issue_id is not None),
        )

    def _snapshot_components(
        self,
        payroll_run_id: int,
        attempt_number: int,
        employee_id: int,
        salary_revision_id: int,
        deferred_issues: list[PayrollProcessingIssueCreateRequest] | None,
    ) -> tuple[tuple[SalaryComponentSnapshot, ...] | None, int | None]:
        revision_components = self.uow.salary_revision_components.get_by_revision(
            salary_revision_id
        )
        component_ids = {item.salary_component_id for item in revision_components}
        component_ids.update(
            item.base_component_id
            for item in revision_components
            if item.base_component_id is not None
        )
        components = {
            item.salary_component_id: item
            for item in self.uow.salary_components.get_by_ids(component_ids)
        }

        snapshots: list[SalaryComponentSnapshot] = []
        for revision_component in revision_components:
            component = components.get(revision_component.salary_component_id)
            if component is None:
                return None, self._record_issue(
                    payroll_run_id,
                    attempt_number,
                    employee_id,
                    "INVALID_COMPENSATION_CONFIGURATION",
                    "A revision component references a missing salary component.",
                    deferred_issues,
                )

            try:
                SalaryComponent(
                    salary_component_id=component.salary_component_id,
                    component_code=component.component_code,
                    component_name=component.component_name,
                    component_type=component.component_type,
                    status=component.status,
                )
                SalaryRevisionComponent(
                    salary_revision_id=revision_component.salary_revision_id,
                    salary_component_id=revision_component.salary_component_id,
                    calculation_type=revision_component.calculation_type,
                    fixed_amount=revision_component.fixed_amount,
                    percentage_value=revision_component.percentage_value,
                    base_component_id=revision_component.base_component_id,
                )
            except BusinessRuleViolation as exc:
                return None, self._record_issue(
                    payroll_run_id,
                    attempt_number,
                    employee_id,
                    "INVALID_COMPENSATION_CONFIGURATION",
                    str(exc),
                    deferred_issues,
                )

            if (
                revision_component.base_component_id is not None
                and revision_component.base_component_id not in components
            ):
                return None, self._record_issue(
                    payroll_run_id,
                    attempt_number,
                    employee_id,
                    "INVALID_COMPENSATION_CONFIGURATION",
                    "A percentage component references a missing base component.",
                    deferred_issues,
                )

            snapshots.append(
                SalaryComponentSnapshot(
                    salary_component_id=component.salary_component_id,
                    component_name=component.component_name,
                    component_type=component.component_type,
                    calculation_type=revision_component.calculation_type,
                    is_overtime_base=revision_component.is_overtime_base,
                    fixed_amount=revision_component.fixed_amount,
                    percentage_value=revision_component.percentage_value,
                    base_component_id=revision_component.base_component_id,
                )
            )

        return tuple(snapshots), None

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


def _is_effective(
    effective_from: date,
    effective_to: date | None,
    snapshot_date: date,
) -> bool:
    return effective_from <= snapshot_date and (
        effective_to is None or effective_to >= snapshot_date
    )
