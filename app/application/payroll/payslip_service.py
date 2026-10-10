from sqlalchemy.exc import IntegrityError

from app.application.common.unit_of_work import UnitOfWork
from app.application.payroll.schemas import PayslipCreateRequest, PayslipResponse
from app.domain.payroll.payslip import Payslip
from app.domain.shared.exceptions import BusinessRuleViolation
from app.infrastructure.persistence.models.audit_event import AuditEventModel
from app.infrastructure.persistence.models.audit_event_change import (
    AuditEventChangeModel,
)
from app.infrastructure.persistence.models.payslip import PayslipModel


class PayslipService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def generate(
        self,
        request: PayslipCreateRequest,
        actor_user_id: int,
        correlation_id: str | None,
    ) -> PayslipResponse | None:
        run = self.uow.payroll_runs.lock_for_finalization(request.payroll_run_id)
        if run is None:
            return None
        if run.status != "FINALIZED":
            raise BusinessRuleViolation(
                "Payslips can only be generated for a FINALIZED Payroll Run."
            )

        result = self.uow.payroll_results.get_by_id(request.payroll_result_id)
        if result is None or result.payroll_run_id != request.payroll_run_id:
            return None
        if self.uow.payslips.get_by_result_id(request.payroll_result_id) is not None:
            raise BusinessRuleViolation("A payslip already exists for this payroll result.")
        if self.uow.payslips.get_by_number(request.payslip_number) is not None:
            raise BusinessRuleViolation("Payslip number already exists.")
        payslip = Payslip(
            payslip_id=None,
            payroll_result_id=request.payroll_result_id,
            payslip_number=request.payslip_number,
            generated_by_user_id=actor_user_id,
            document_path=None,
        )
        model = PayslipModel(
            payroll_result_id=payslip.payroll_result_id,
            payslip_number=payslip.payslip_number,
            generated_by_user_id=actor_user_id,
            document_path=payslip.document_path,
        )
        try:
            self.uow.payslips.add(model)
        except IntegrityError as exc:
            if _is_payslip_unique_conflict(exc):
                self.uow.rollback()
                raise BusinessRuleViolation(
                    "A payslip already exists for this result or payslip number."
                ) from exc
            raise

        try:
            self.uow.audit_events.add(
                AuditEventModel(
                    actor_user_id=actor_user_id,
                    action_type="PAYSLIP_GENERATED",
                    resource_type="PAYSLIP",
                    resource_id=model.payslip_id,
                    correlation_id=correlation_id,
                ),
                [
                    AuditEventChangeModel(
                        field_name="payroll_run_id",
                        old_value=None,
                        new_value=str(request.payroll_run_id),
                    ),
                    AuditEventChangeModel(
                        field_name="payroll_result_id",
                        old_value=None,
                        new_value=str(request.payroll_result_id),
                    ),
                ],
            )
            self.uow.commit()
        except Exception:
            self.uow.rollback()
            raise
        return PayslipResponse(
            payslip_id=model.payslip_id,
            payroll_result_id=model.payroll_result_id,
            payslip_number=model.payslip_number,
            generated_by_user_id=model.generated_by_user_id,
            generated_at=model.generated_at,
            document_path=model.document_path,
        )


def _is_payslip_unique_conflict(exc: IntegrityError) -> bool:
    message = str(exc.orig).lower()
    if "uq_payslip_result" in message or "uq_payslip_number" in message:
        return True
    return "unique constraint failed" in message and "payslips." in message and (
        "payroll_result_id" in message or "payslip_number" in message
    )
