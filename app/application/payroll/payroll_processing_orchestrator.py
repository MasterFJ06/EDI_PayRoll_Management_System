import logging
from dataclasses import dataclass

from app.application.common.unit_of_work import UnitOfWork
from app.application.compensation.segmentation import CompensationSegment
from app.application.payroll.compensation_snapshot import (
    CompensationSnapshot,
    CompensationSnapshotResolver,
)
from app.application.payroll.employee_eligibility_resolver import (
    EmployeeEligibilityResult,
    EmployeeEligibilityResolver,
)
from app.application.payroll.period_segmentation import (
    PeriodSegmentationResult,
    PayrollPeriodSegmenter,
)
from app.application.payroll.workforce_snapshot_materializer import (
    WorkforceSnapshotMaterializer,
)
from app.application.payroll.payroll_run_service import PayrollRunService
from app.application.payroll.payroll_quality_assurance_service import (
    PayrollQualityAssuranceService,
)
from app.application.payroll.payroll_financial_calculator import (
    PayrollCalculationError,
    PayrollFinancialCalculationService,
)
from app.application.payroll.schemas import (
    PayrollProcessingIssueCreateRequest,
    PayrollRunResponse,
)
from app.domain.shared.exceptions import BusinessRuleViolation
from app.domain.payroll.payroll_run_workforce_snapshot import (
    PayrollRunWorkforceSnapshot,
)
from app.infrastructure.persistence.models.audit_event import AuditEventModel
from app.infrastructure.persistence.models.audit_event_change import (
    AuditEventChangeModel,
)


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PayrollProcessingOutcome:
    payroll_run: PayrollRunResponse
    eligibility: EmployeeEligibilityResult
    compensation_snapshot: CompensationSnapshot
    period_segmentation: PeriodSegmentationResult
    workforce_snapshots: tuple[PayrollRunWorkforceSnapshot, ...]
    blocking_issue_ids: tuple[int, ...]


class PayrollProcessingOrchestrator:
    """Claims a Payroll Run, freezes inputs, and calculates employee results."""

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def process(
        self,
        payroll_run_id: int,
        actor_user_id: int,
        correlation_id: str | None,
    ) -> PayrollProcessingOutcome | None:
        attempt_number = self.uow.payroll_runs.claim_for_processing(payroll_run_id)
        if attempt_number is None:
            run = self.uow.payroll_runs.get_by_id(payroll_run_id)
            if run is None:
                logger.warning(
                    "Payroll processing claim rejected run_missing payroll_run_id=%s "
                    "user_id=%s correlation_id=%s",
                    payroll_run_id,
                    actor_user_id,
                    correlation_id,
                )
                return None
            logger.warning(
                "Payroll processing claim rejected invalid_state payroll_run_id=%s "
                "status=%s user_id=%s correlation_id=%s",
                payroll_run_id,
                run.status,
                actor_user_id,
                correlation_id,
            )
            raise BusinessRuleViolation(
                f"Payroll Run cannot be processed from {run.status} status."
            )

        self.uow.audit_events.add(
            AuditEventModel(
                actor_user_id=actor_user_id,
                action_type="PAYROLL_RUN_PROCESSING_STARTED",
                resource_type="PAYROLL_RUN",
                resource_id=payroll_run_id,
                correlation_id=correlation_id,
            ),
            [
                AuditEventChangeModel(
                    field_name="status",
                    old_value="CREATED",
                    new_value="PROCESSING",
                )
            ],
        )
        self.uow.commit()

        logger.info(
            "Payroll run processing claimed payroll_run_id=%s user_id=%s "
            "correlation_id=%s",
            payroll_run_id,
            actor_user_id,
            correlation_id,
        )

        try:
            snapshot_at = self.uow.begin_workforce_consistent_read()
            run = self.uow.payroll_runs.get_by_id(payroll_run_id)
            if run is None:
                raise RuntimeError("Claimed Payroll Run could not be reloaded.")
            if run.started_at is None:
                raise RuntimeError("Claimed Payroll Run has no processing start time.")
            eligibility = EmployeeEligibilityResolver(self.uow).resolve(
                run.payroll_year,
                run.payroll_month,
            )
            deferred_issues: list[PayrollProcessingIssueCreateRequest] = []
            snapshot_resolution = CompensationSnapshotResolver(self.uow).resolve(
                payroll_run_id,
                attempt_number,
                run.started_at,
                tuple(
                    employee.employee_id
                    for employee in eligibility.eligible_employees
                ),
                deferred_issues=deferred_issues,
            )
            segmentation = PayrollPeriodSegmenter(self.uow).resolve(
                payroll_run_id,
                attempt_number,
                eligibility,
                snapshot_resolution.snapshot,
                deferred_issues=deferred_issues,
            )
            workforce_materializer = WorkforceSnapshotMaterializer(self.uow)
            workforce_materialization = workforce_materializer.collect(
                payroll_run_id=payroll_run_id,
                attempt_number=attempt_number,
                payroll_year=run.payroll_year,
                payroll_month=run.payroll_month,
                snapshot_at=snapshot_at,
                eligibility=eligibility,
            )
            # End the consistent input read before opening the snapshot write transaction.
            self.uow.commit()
            workforce_materializer.persist(
                workforce_materialization,
                attempt_number,
                tuple(deferred_issues),
            )
            self.uow.commit()
            self._calculate_employee_results(
                payroll_run_id=payroll_run_id,
                attempt_number=attempt_number,
                eligibility=eligibility,
                compensation_snapshot=snapshot_resolution.snapshot,
                segmentation=segmentation,
                workforce_snapshots=workforce_materialization.snapshots,
            )
            self._processing_pipeline_extension_point(payroll_run_id)
            quality_assurance = PayrollQualityAssuranceService(self.uow).evaluate_and_transition(
                payroll_run_id=payroll_run_id,
                attempt_number=attempt_number,
                actor_user_id=actor_user_id,
                correlation_id=correlation_id,
                eligibility=eligibility,
                expected_salary_assignment_ids={
                    item.employee_id: item.assignment.salary_assignment_id
                    for item in snapshot_resolution.snapshot.employees
                },
            )
            completed_run = self.uow.payroll_runs.get_by_id(payroll_run_id)
            if completed_run is None:
                raise RuntimeError("Payroll Run disappeared after QA completion.")
            logger.info(
                "Payroll eligibility and compensation snapshot resolved payroll_run_id=%s "
                "eligible_count=%s excluded_count=%s segmented_employee_count=%s "
                "segmentation_issue_count=%s snapshot_issue_count=%s "
                "correlation_id=%s",
                payroll_run_id,
                len(eligibility.eligible_employees),
                len(eligibility.excluded_employee_ids),
                len({segment.employee_id for segment in segmentation.segments}),
                len(segmentation.blocking_issue_ids),
                len(snapshot_resolution.blocking_issue_ids),
                correlation_id,
            )
            return PayrollProcessingOutcome(
                payroll_run=PayrollRunService._to_response(completed_run),
                eligibility=eligibility,
                compensation_snapshot=snapshot_resolution.snapshot,
                period_segmentation=segmentation,
                workforce_snapshots=workforce_materialization.snapshots,
                blocking_issue_ids=quality_assurance.open_issue_ids,
            )
        except Exception:
            # Discard any partial snapshot inserts before transitioning to FAILED.
            self.uow.rollback()
            self._mark_failed_after_orchestration_error(
                payroll_run_id, attempt_number, actor_user_id, correlation_id
            )
            logger.exception(
                "Payroll processing orchestration failed payroll_run_id=%s "
                "user_id=%s correlation_id=%s",
                payroll_run_id,
                actor_user_id,
                correlation_id,
            )
            raise

    def _processing_pipeline_extension_point(self, payroll_run_id: int) -> None:
        """Reserved for later Payroll QA and completion stages."""

    def _calculate_employee_results(
        self,
        *,
        payroll_run_id: int,
        attempt_number: int,
        eligibility: EmployeeEligibilityResult,
        compensation_snapshot: CompensationSnapshot,
        segmentation: PeriodSegmentationResult,
        workforce_snapshots: tuple[PayrollRunWorkforceSnapshot, ...],
    ) -> tuple[int, ...]:
        service = PayrollFinancialCalculationService(self.uow)
        snapshots_by_employee = {
            item.employee_id: item for item in workforce_snapshots
        }
        compensation_by_employee = {
            item.employee_id: item for item in compensation_snapshot.employees
        }
        segments_by_employee: dict[int, list[CompensationSegment]] = {}
        for segment in segmentation.segments:
            segments_by_employee.setdefault(segment.employee_id, []).append(segment)

        blocked_by_segmentation = set(segmentation.blocked_employee_ids)
        issue_ids: list[int] = []
        for eligible in eligibility.eligible_employees:
            employee_id = eligible.employee_id
            if employee_id in blocked_by_segmentation:
                continue
            compensation = compensation_by_employee.get(employee_id)
            if compensation is None:
                continue  # Phase 2B-3 already recorded the blocking issue.
            employee_segments = segments_by_employee.get(employee_id, [])
            if not employee_segments:
                continue  # Phase 2B-4 already recorded the blocking issue.
            snapshot = snapshots_by_employee.get(employee_id)
            if snapshot is None:
                error = PayrollCalculationError(
                    "WORKFORCE_SNAPSHOT_MISSING",
                    "No frozen Workforce snapshot exists for the eligible employee.",
                )
                self.uow.rollback()
                issue_id = service.record_blocking_issue(
                    payroll_run_id, employee_id, attempt_number, error
                )
                if issue_id is not None:
                    issue_ids.append(issue_id)
                continue
            try:
                service.calculate_employee(
                    payroll_run_id,
                    employee_id,
                    attempt_number,
                    employee_segments,
                    compensation.assignment.salary_assignment_id,
                    snapshot,
                )
            except PayrollCalculationError as error:
                self.uow.rollback()
                issue_id = service.record_blocking_issue(
                    payroll_run_id, employee_id, attempt_number, error
                )
                if issue_id is not None:
                    issue_ids.append(issue_id)
        return tuple(issue_ids)

    def _mark_failed_after_orchestration_error(
        self,
        payroll_run_id: int,
        attempt_number: int,
        actor_user_id: int,
        correlation_id: str | None,
    ) -> None:
        try:
            if not self.uow.payroll_runs.mark_failed_if_processing(
                payroll_run_id, attempt_number
            ):
                self.uow.rollback()
                logger.error(
                    "Payroll run failure transition was not applied "
                    "payroll_run_id=%s user_id=%s correlation_id=%s",
                    payroll_run_id,
                    actor_user_id,
                    correlation_id,
                )
                return
            self.uow.audit_events.add(
                AuditEventModel(
                    actor_user_id=actor_user_id,
                    action_type="PAYROLL_RUN_PROCESSING_FAILED",
                    resource_type="PAYROLL_RUN",
                    resource_id=payroll_run_id,
                    correlation_id=correlation_id,
                ),
                [
                    AuditEventChangeModel(
                        field_name="status",
                        old_value="PROCESSING",
                        new_value="FAILED",
                    )
                ],
            )
            self.uow.commit()
        except Exception:
            self.uow.rollback()
            logger.exception(
                "Could not persist Payroll Run failure transition "
                "payroll_run_id=%s user_id=%s correlation_id=%s",
                payroll_run_id,
                actor_user_id,
                correlation_id,
            )
