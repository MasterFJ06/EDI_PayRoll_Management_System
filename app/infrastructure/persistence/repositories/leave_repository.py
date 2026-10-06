from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.persistence.models.leave import (
    LeaveBalance,
    LeaveRequest,
    LeaveType,
)


class LeaveRepository:
    """Repository for leave types, balances, and requests."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_requests(self, employee_id: int | None = None) -> list[LeaveRequest]:
        statement = select(LeaveRequest)
        if employee_id is not None:
            statement = statement.where(LeaveRequest.employee_id == employee_id)
        statement = statement.order_by(LeaveRequest.leave_request_id.desc())
        return list(self.session.scalars(statement).all())

    def get_request_by_id(self, leave_request_id: int) -> LeaveRequest | None:
        statement = select(LeaveRequest).where(
            LeaveRequest.leave_request_id == leave_request_id
        )
        return self.session.scalar(statement)

    def add_request(self, request: LeaveRequest) -> LeaveRequest:
        self.session.add(request)
        self.session.flush()
        return request

    def update_request(self, request: LeaveRequest) -> LeaveRequest:
        self.session.merge(request)
        self.session.flush()
        return request

    def get_balances(self, employee_id: int | None = None) -> list[LeaveBalance]:
        statement = select(LeaveBalance)
        if employee_id is not None:
            statement = statement.where(LeaveBalance.employee_id == employee_id)
        statement = statement.order_by(LeaveBalance.leave_balance_id.asc())
        return list(self.session.scalars(statement).all())

    def get_balance(
        self,
        employee_id: int,
        leave_type_id: int,
        year: int,
    ) -> LeaveBalance | None:
        statement = select(LeaveBalance).where(
            LeaveBalance.employee_id == employee_id,
            LeaveBalance.leave_type_id == leave_type_id,
            LeaveBalance.balance_year == year,
        )
        return self.session.scalar(statement)

    def add_balance(self, balance: LeaveBalance) -> LeaveBalance:
        self.session.add(balance)
        self.session.flush()
        return balance

    def update_balance(self, balance: LeaveBalance) -> LeaveBalance:
        self.session.merge(balance)
        self.session.flush()
        return balance

    def get_types(self) -> list[LeaveType]:
        statement = select(LeaveType).order_by(LeaveType.leave_type_id.asc())
        return list(self.session.scalars(statement).all())

    def get_type_by_id(self, leave_type_id: int) -> LeaveType | None:
        statement = select(LeaveType).where(
            LeaveType.leave_type_id == leave_type_id
        )
        return self.session.scalar(statement)

    def get_type_by_code(self, code: str) -> LeaveType | None:
        statement = select(LeaveType).where(
            LeaveType.leave_type_code == code
        )
        return self.session.scalar(statement)

    def add_type(self, leave_type: LeaveType) -> LeaveType:
        self.session.add(leave_type)
        self.session.flush()
        return leave_type
