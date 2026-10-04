from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.leave.repository import LeaveBalanceRepository as LeaveBalanceRepositoryContract
from app.infrastructure.persistence.models.leave_balance import LeaveBalanceModel


class LeaveBalanceRepository(LeaveBalanceRepositoryContract):
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, leave_balance_id: int) -> LeaveBalanceModel | None:
        return self.session.scalar(
            select(LeaveBalanceModel).where(
                LeaveBalanceModel.leave_balance_id == leave_balance_id
            )
        )

    def get_by_employee_type_year(
        self, employee_id: int, leave_type_id: int, balance_year: int
    ) -> LeaveBalanceModel | None:
        statement = select(LeaveBalanceModel).where(
            LeaveBalanceModel.employee_id == employee_id,
            LeaveBalanceModel.leave_type_id == leave_type_id,
            LeaveBalanceModel.balance_year == balance_year,
        )
        return self.session.scalar(statement)

    def add(self, leave_balance: LeaveBalanceModel) -> LeaveBalanceModel:
        self.session.add(leave_balance)
        self.session.flush()
        return leave_balance
