from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.leave.repository import LeaveTypeRepository as LeaveTypeRepositoryContract
from app.infrastructure.persistence.models.leave_type import LeaveTypeModel


class LeaveTypeRepository(LeaveTypeRepositoryContract):
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, leave_type_id: int) -> LeaveTypeModel | None:
        return self.session.scalar(
            select(LeaveTypeModel).where(LeaveTypeModel.leave_type_id == leave_type_id)
        )

    def get_by_code(self, leave_type_code: str) -> LeaveTypeModel | None:
        return self.session.scalar(
            select(LeaveTypeModel).where(LeaveTypeModel.leave_type_code == leave_type_code)
        )

    def get_by_name(self, leave_type_name: str) -> LeaveTypeModel | None:
        return self.session.scalar(
            select(LeaveTypeModel).where(LeaveTypeModel.leave_type_name == leave_type_name)
        )

    def add(self, leave_type: LeaveTypeModel) -> LeaveTypeModel:
        self.session.add(leave_type)
        self.session.flush()
        return leave_type
