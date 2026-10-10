from app.application.common.unit_of_work import UnitOfWork
from app.application.payroll.schemas import PayrollRunResponse
from app.application.payroll.payroll_run_service import PayrollRunService
from app.domain.shared.exceptions import BusinessRuleViolation
from app.infrastructure.persistence.models.audit_event import AuditEventModel
from app.infrastructure.persistence.models.audit_event_change import (
    AuditEventChangeModel,
)


class PayrollRunFinalizationService:
    """Atomically finalizes a processed Payroll Run and records its audit event."""

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def finalize(
        self,
        payroll_run_id: int,
        actor_user_id: int,
        correlation_id: str | None,
    ) -> PayrollRunResponse | None:
        # The parent lock serializes finalization with issue creation and other
        # attempt-owned writes. Locking reads below see current MySQL state.
        run = self.uow.payroll_runs.lock_for_finalization(payroll_run_id)
        if run is None:
            return None
        if run.status != "PROCESSED":
            raise BusinessRuleViolation(
                f"Payroll Run cannot be finalized from {run.status} status."
            )
        if self.uow.payroll_processing_issues.has_open_for_update(payroll_run_id):
            raise BusinessRuleViolation(
                "Payroll Run cannot be finalized while blocking OPEN issues remain."
            )
        if self.uow.payslips.get_by_run_id_for_update(payroll_run_id) is not None:
            raise BusinessRuleViolation(
                "Payroll Run cannot be finalized because a payslip already exists."
            )

        if not self.uow.payroll_runs.finalize_processed_run(payroll_run_id):
            raise BusinessRuleViolation(
                "Payroll Run state changed before finalization could complete."
            )
        if run.finalized_at is None:
            raise RuntimeError("Finalized Payroll Run has no finalization timestamp.")

        self.uow.audit_events.add(
            AuditEventModel(
                actor_user_id=actor_user_id,
                action_type="PAYROLL_RUN_FINALIZED",
                resource_type="PAYROLL_RUN",
                resource_id=payroll_run_id,
                correlation_id=correlation_id,
            ),
            [
                AuditEventChangeModel(
                    field_name="status",
                    old_value="PROCESSED",
                    new_value="FINALIZED",
                ),
                AuditEventChangeModel(
                    field_name="finalized_at",
                    old_value=None,
                    new_value=run.finalized_at.isoformat(sep=" "),
                ),
            ],
        )
        self.uow.commit()
        return PayrollRunService(self.uow).get(payroll_run_id)
