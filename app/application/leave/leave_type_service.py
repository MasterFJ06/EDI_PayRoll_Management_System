from app.application.common.unit_of_work import UnitOfWork
from app.application.leave.schemas import LeaveTypeCreateRequest, LeaveTypeResponse
from app.domain.leave.leave_type import LeaveType
from app.domain.shared.exceptions import BusinessRuleViolation
from app.infrastructure.persistence.models.audit_event import AuditEventModel
from app.infrastructure.persistence.models.audit_event_change import AuditEventChangeModel
from app.infrastructure.persistence.models.leave_type import LeaveTypeModel
from sqlalchemy.exc import IntegrityError


class LeaveTypeService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def create(
        self,
        request: LeaveTypeCreateRequest,
        actor_user_id: int,
        correlation_id: str | None,
    ) -> LeaveTypeResponse:
        leave_type = LeaveType(
            leave_type_id=None,
            leave_type_code=request.leave_type_code,
            leave_type_name=request.leave_type_name,
            description=request.description,
            payroll_treatment=request.payroll_treatment,
            is_active=request.is_active,
        )
        if self.uow.leave_types.get_by_code(leave_type.leave_type_code) is not None:
            raise BusinessRuleViolation("Leave type code is already registered.")
        if self.uow.leave_types.get_by_name(leave_type.leave_type_name) is not None:
            raise BusinessRuleViolation("Leave type name is already registered.")

        model = LeaveTypeModel(
            leave_type_code=leave_type.leave_type_code,
            leave_type_name=leave_type.leave_type_name,
            description=leave_type.description,
            payroll_treatment=leave_type.payroll_treatment,
            is_active=leave_type.is_active,
        )
        try:
            self.uow.leave_types.add(model)
            self.uow.audit_events.add(
                AuditEventModel(
                    actor_user_id=actor_user_id,
                    action_type="LEAVE_TYPE_CREATED",
                    resource_type="LEAVE_TYPE",
                    resource_id=model.leave_type_id,
                    correlation_id=correlation_id,
                ),
                [
                    AuditEventChangeModel(
                        field_name="payroll_treatment",
                        old_value=None,
                        new_value=model.payroll_treatment,
                    )
                ],
            )
            self.uow.commit()
        except IntegrityError as exc:
            self.uow.rollback()
            raise BusinessRuleViolation("Leave type code or name is already registered.") from exc
        return LeaveTypeResponse(
            leave_type_id=model.leave_type_id,
            leave_type_code=model.leave_type_code,
            leave_type_name=model.leave_type_name,
            description=model.description,
            payroll_treatment=model.payroll_treatment,
            is_active=model.is_active,
        )
