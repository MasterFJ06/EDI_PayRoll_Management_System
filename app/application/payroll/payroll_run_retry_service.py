from dataclasses import dataclass

from app.application.common.unit_of_work import UnitOfWork
from app.domain.shared.exceptions import BusinessRuleViolation
from app.infrastructure.persistence.models.audit_event import AuditEventModel
from app.infrastructure.persistence.models.audit_event_change import (
    AuditEventChangeModel,
)


@dataclass(frozen=True)
class PayrollRunRetryOutcome:
    payroll_run_id: int
    old_attempt_number: int
    new_attempt_number: int
    deleted_result_count: int
    deleted_component_count: int
    deleted_workforce_snapshot_count: int


class PayrollRunRetryService:
    """Atomically reconciles a failed attempt and claims its successor."""

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def retry_failed_payroll_run(
        self,
        payroll_run_id: int,
        expected_attempt_number: int,
        actor_user_id: int,
        correlation_id: str | None,
    ) -> PayrollRunRetryOutcome:
        # Parent-first lock is the serialization point for retry and fenced writes.
        run = self.uow.payroll_runs.lock_failed_attempt(payroll_run_id)
        if run is None:
            raise BusinessRuleViolation("Payroll Run does not exist.")
        if run.status != "FAILED":
            raise BusinessRuleViolation(
                f"Payroll Run cannot be retried from {run.status} status."
            )
        if run.attempt_number != expected_attempt_number:
            raise BusinessRuleViolation(
                "Expected Payroll Run attempt does not match the current attempt."
            )

        # Check the invariant before deleting any financial artifacts.
        if self.uow.payslips.get_by_run_id(payroll_run_id) is not None:
            raise BusinessRuleViolation(
                "Payroll Run cannot be retried because a payslip exists."
            )

        old_attempt_number = run.attempt_number
        component_count = self.uow.payroll_result_components.delete_by_run(
            payroll_run_id
        )
        result_count = self.uow.payroll_results.delete_by_run(payroll_run_id)
        snapshot_count = self.uow.payroll_run_workforce_snapshots.delete_by_run_and_attempt(
            payroll_run_id, old_attempt_number
        )

        new_attempt_number = self.uow.payroll_runs.retry_failed_attempt(
            payroll_run_id, expected_attempt_number
        )
        if new_attempt_number is None:
            raise BusinessRuleViolation(
                "Payroll Run attempt changed before retry could be claimed."
            )

        self.uow.audit_events.add(
            AuditEventModel(
                actor_user_id=actor_user_id,
                action_type="PAYROLL_RUN_RETRY_CLAIMED",
                resource_type="PAYROLL_RUN",
                resource_id=payroll_run_id,
                correlation_id=correlation_id,
            ),
            [
                AuditEventChangeModel(
                    field_name="attempt_number",
                    old_value=str(old_attempt_number),
                    new_value=str(new_attempt_number),
                ),
                AuditEventChangeModel(
                    field_name="deleted_result_count",
                    old_value=None,
                    new_value=str(result_count),
                ),
                AuditEventChangeModel(
                    field_name="deleted_component_count",
                    old_value=None,
                    new_value=str(component_count),
                ),
                AuditEventChangeModel(
                    field_name="deleted_workforce_snapshot_count",
                    old_value=None,
                    new_value=str(snapshot_count),
                ),
                AuditEventChangeModel(
                    field_name="status",
                    old_value="FAILED",
                    new_value="PROCESSING",
                ),
            ],
        )
        self.uow.commit()

        return PayrollRunRetryOutcome(
            payroll_run_id=payroll_run_id,
            old_attempt_number=old_attempt_number,
            new_attempt_number=new_attempt_number,
            deleted_result_count=result_count,
            deleted_component_count=component_count,
            deleted_workforce_snapshot_count=snapshot_count,
        )
