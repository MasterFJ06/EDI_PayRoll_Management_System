from app.application.common.unit_of_work import UnitOfWork
from app.application.leave.schemas import LeaveBalanceCreateRequest, LeaveBalanceResponse
from app.domain.leave.leave_balance import LeaveBalance
from app.domain.shared.exceptions import BusinessRuleViolation
from app.infrastructure.persistence.models.leave_balance import LeaveBalanceModel


class LeaveBalanceService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def create(self, request: LeaveBalanceCreateRequest) -> LeaveBalanceResponse:
        if self.uow.employees.get_by_id(request.employee_id) is None:
            raise BusinessRuleViolation("Employee does not exist.")
        if self.uow.leave_types.get_by_id(request.leave_type_id) is None:
            raise BusinessRuleViolation("Leave type does not exist.")
        if self.uow.leave_balances.get_by_employee_type_year(
            request.employee_id, request.leave_type_id, request.balance_year
        ) is not None:
            raise BusinessRuleViolation("Leave balance already exists for this employee, type, and year.")

        balance = LeaveBalance(
            leave_balance_id=None,
            employee_id=request.employee_id,
            leave_type_id=request.leave_type_id,
            balance_year=request.balance_year,
            allocated_days=request.allocated_days,
            used_days=request.used_days,
        )
        model = LeaveBalanceModel(
            employee_id=balance.employee_id,
            leave_type_id=balance.leave_type_id,
            balance_year=balance.balance_year,
            allocated_days=balance.allocated_days,
            used_days=balance.used_days,
        )
        self.uow.leave_balances.add(model)
        self.uow.commit()
        return LeaveBalanceResponse(
            leave_balance_id=model.leave_balance_id,
            employee_id=model.employee_id,
            leave_type_id=model.leave_type_id,
            balance_year=model.balance_year,
            allocated_days=model.allocated_days,
            used_days=model.used_days,
        )
