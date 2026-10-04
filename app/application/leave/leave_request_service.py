from app.application.common.unit_of_work import UnitOfWork
from app.application.leave.schemas import LeaveRequestCreateRequest, LeaveRequestResponse
from app.domain.leave.leave_request import LeaveRequest
from app.domain.shared.exceptions import BusinessRuleViolation
from app.infrastructure.persistence.models.leave_request import LeaveRequestModel


class LeaveRequestService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def create(self, request: LeaveRequestCreateRequest) -> LeaveRequestResponse:
        if self.uow.employees.get_by_id(request.employee_id) is None:
            raise BusinessRuleViolation("Employee does not exist.")
        if self.uow.leave_types.get_by_id(request.leave_type_id) is None:
            raise BusinessRuleViolation("Leave type does not exist.")
        if request.reviewed_by_employee_id is not None and self.uow.employees.get_by_id(
            request.reviewed_by_employee_id
        ) is None:
            raise BusinessRuleViolation("Reviewer employee does not exist.")

        leave_request = LeaveRequest(
            leave_request_id=None,
            employee_id=request.employee_id,
            leave_type_id=request.leave_type_id,
            start_date=request.start_date,
            end_date=request.end_date,
            requested_days=request.requested_days,
            reason=request.reason,
            status=request.status,
            reviewed_by_employee_id=request.reviewed_by_employee_id,
            reviewed_at=request.reviewed_at,
            review_comment=request.review_comment,
        )
        model = LeaveRequestModel(
            employee_id=leave_request.employee_id,
            leave_type_id=leave_request.leave_type_id,
            start_date=leave_request.start_date,
            end_date=leave_request.end_date,
            requested_days=leave_request.requested_days,
            reason=leave_request.reason,
            status=leave_request.status,
            reviewed_by_employee_id=leave_request.reviewed_by_employee_id,
            reviewed_at=leave_request.reviewed_at,
            review_comment=leave_request.review_comment,
        )
        self.uow.leave_requests.add(model)
        self.uow.commit()
        return LeaveRequestResponse(
            leave_request_id=model.leave_request_id,
            employee_id=model.employee_id,
            leave_type_id=model.leave_type_id,
            start_date=model.start_date,
            end_date=model.end_date,
            requested_days=model.requested_days,
            reason=model.reason,
            status=model.status,
            reviewed_by_employee_id=model.reviewed_by_employee_id,
            reviewed_at=model.reviewed_at,
            review_comment=model.review_comment,
        )
