import logging

from app.application.common.unit_of_work import UnitOfWork
from app.application.payroll.payroll_run_service import PayrollRunService
from app.application.payroll.schemas import PayrollRunResponse
from app.domain.shared.exceptions import BusinessRuleViolation
from app.infrastructure.persistence.models.audit_event import AuditEventModel
from app.infrastructure.persistence.models.audit_event_change import (
    AuditEventChangeModel,
)


logger = logging.getLogger(__name__)


class PayrollProcessingOrchestrator:
    """Claims a Payroll Run and defines the boundary for future processing steps."""

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def process(
        self,
        payroll_run_id: int,
        actor_user_id: int,
        correlation_id: str | None,
    ) -> PayrollRunResponse | None:
        if not self.uow.payroll_runs.claim_for_processing(payroll_run_id):
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
            self._processing_pipeline_extension_point(payroll_run_id)
            run = self.uow.payroll_runs.get_by_id(payroll_run_id)
            if run is None:
                raise RuntimeError("Claimed Payroll Run could not be reloaded.")
            return PayrollRunService._to_response(run)
        except Exception:
            self._mark_failed_after_orchestration_error(
                payroll_run_id, actor_user_id, correlation_id
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
        """Reserved for later pipeline stages; this phase performs no calculations."""

    def _mark_failed_after_orchestration_error(
        self,
        payroll_run_id: int,
        actor_user_id: int,
        correlation_id: str | None,
    ) -> None:
        try:
            if not self.uow.payroll_runs.mark_failed_if_processing(payroll_run_id):
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
