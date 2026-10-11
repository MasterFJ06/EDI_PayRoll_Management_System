from app.application.common.unit_of_work import UnitOfWork
from app.application.payroll.payroll_run_service import PayrollRunService
from app.application.payroll.schemas import PayrollRunResponse
from app.domain.shared.exceptions import BusinessRuleViolation
from app.infrastructure.persistence.models.audit_event import AuditEventModel
from app.infrastructure.persistence.models.audit_event_change import (
    AuditEventChangeModel,
)


class PayrollRunRecoveryService:
    """Recovers an expired processing attempt without starting its successor."""

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def recover_expired_attempt(
        self,
        payroll_run_id: int,
        actor_user_id: int,
        correlation_id: str | None,
    ) -> PayrollRunResponse | None:
        run = self.uow.payroll_runs.lock_expired_processing_attempt(payroll_run_id)
        if run is None:
            if self.uow.payroll_runs.get_by_id(payroll_run_id) is None:
                return None
            raise BusinessRuleViolation(
                "Only a Payroll Run with an expired PROCESSING attempt can be recovered."
            )

        attempt_number = run.attempt_number
        expired_at = run.attempt_lease_expires_at
        if not self.uow.payroll_runs.recover_expired_attempt(
            payroll_run_id, attempt_number
        ):
            raise BusinessRuleViolation(
                "Payroll processing attempt changed before recovery could be applied."
            )

        self.uow.audit_events.add(
            AuditEventModel(
                actor_user_id=actor_user_id,
                action_type="PAYROLL_RUN_ATTEMPT_RECOVERED",
                resource_type="PAYROLL_RUN",
                resource_id=payroll_run_id,
                correlation_id=correlation_id,
            ),
            [
                AuditEventChangeModel(
                    field_name="payroll_run_id",
                    old_value=None,
                    new_value=str(payroll_run_id),
                ),
                AuditEventChangeModel(
                    field_name="attempt_number",
                    old_value=None,
                    new_value=str(attempt_number),
                ),
                AuditEventChangeModel(
                    field_name="status",
                    old_value="PROCESSING",
                    new_value="FAILED",
                ),
                AuditEventChangeModel(
                    field_name="attempt_lease_expires_at",
                    old_value=expired_at.isoformat() if expired_at is not None else None,
                    new_value=None,
                ),
            ],
        )
        # AuditEventModel.occurred_at is populated by the authoritative database
        # CURRENT_TIMESTAMP default in the same transaction as the transition.
        self.uow.commit()
        return PayrollRunService(self.uow).get(payroll_run_id)
