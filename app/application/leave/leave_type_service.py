from app.application.common.unit_of_work import UnitOfWork
from app.application.leave.schemas import LeaveTypeCreateRequest, LeaveTypeResponse
from app.domain.leave.leave_type import LeaveType
from app.domain.shared.exceptions import BusinessRuleViolation
from app.infrastructure.persistence.models.leave_type import LeaveTypeModel


class LeaveTypeService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def create(self, request: LeaveTypeCreateRequest) -> LeaveTypeResponse:
        leave_type = LeaveType(
            leave_type_id=None,
            leave_type_code=request.leave_type_code,
            leave_type_name=request.leave_type_name,
            description=request.description,
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
            is_active=leave_type.is_active,
        )
        self.uow.leave_types.add(model)
        self.uow.commit()
        return LeaveTypeResponse(
            leave_type_id=model.leave_type_id,
            leave_type_code=model.leave_type_code,
            leave_type_name=model.leave_type_name,
            description=model.description,
            is_active=model.is_active,
        )
