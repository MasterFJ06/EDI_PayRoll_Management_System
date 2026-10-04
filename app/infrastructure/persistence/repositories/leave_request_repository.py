from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.leave.repository import LeaveRequestRepository as LeaveRequestRepositoryContract
from app.infrastructure.persistence.models.leave_request import LeaveRequestModel


class LeaveRequestRepository(LeaveRequestRepositoryContract):
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, leave_request_id: int) -> LeaveRequestModel | None:
        return self.session.scalar(
            select(LeaveRequestModel).where(
                LeaveRequestModel.leave_request_id == leave_request_id
            )
        )

    def add(self, leave_request: LeaveRequestModel) -> LeaveRequestModel:
        self.session.add(leave_request)
        self.session.flush()
        return leave_request
