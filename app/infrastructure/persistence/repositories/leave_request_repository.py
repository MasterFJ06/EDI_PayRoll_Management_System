from datetime import date, datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.domain.leave.repository import LeaveRequestRepository as LeaveRequestRepositoryContract
from app.domain.leave.leave_request_day import LeaveRequestDay
from app.infrastructure.persistence.models.leave_request_day import LeaveRequestDayModel
from app.infrastructure.persistence.models.leave_request import LeaveRequestModel
from app.infrastructure.persistence.models.leave_type import LeaveTypeModel


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

    def get_days(self, leave_request_id: int) -> list[LeaveRequestDayModel]:
        statement = (
            select(LeaveRequestDayModel)
            .where(LeaveRequestDayModel.leave_request_id == leave_request_id)
            .order_by(LeaveRequestDayModel.leave_date)
        )
        return list(self.session.scalars(statement))

    def get_approved_allocations_for_employee_period(
        self, employee_id: int, start_date: date, end_date: date
    ) -> list[tuple[LeaveRequestModel, LeaveRequestDayModel, LeaveTypeModel | None]]:
        statement = (
            select(LeaveRequestModel, LeaveRequestDayModel, LeaveTypeModel)
            .join(
                LeaveRequestDayModel,
                LeaveRequestDayModel.leave_request_id
                == LeaveRequestModel.leave_request_id,
            )
            .outerjoin(
                LeaveTypeModel,
                LeaveTypeModel.leave_type_id == LeaveRequestModel.leave_type_id,
            )
            .where(
                LeaveRequestModel.employee_id == employee_id,
                LeaveRequestModel.status == "APPROVED",
                LeaveRequestDayModel.leave_date >= start_date,
                LeaveRequestDayModel.leave_date <= end_date,
            )
            .order_by(
                LeaveRequestDayModel.leave_date,
                LeaveRequestModel.leave_request_id,
            )
        )
        return list(self.session.execute(statement).all())

    def add_days(self, leave_request_id: int, days: list[LeaveRequestDay]) -> None:
        self.session.add_all(
            [
                LeaveRequestDayModel(
                    leave_request_id=leave_request_id,
                    leave_date=day.leave_date,
                    day_fraction=day.day_fraction,
                )
                for day in days
            ]
        )
        self.session.flush()

    def find_approved_conflicts(
        self, employee_id: int, leave_dates: list[date], excluding_request_id: int
    ) -> list[date]:
        if not leave_dates:
            return []
        statement = (
            select(LeaveRequestDayModel.leave_date)
            .join(
                LeaveRequestModel,
                LeaveRequestModel.leave_request_id
                == LeaveRequestDayModel.leave_request_id,
            )
            .where(
                LeaveRequestModel.employee_id == employee_id,
                LeaveRequestModel.status == "APPROVED",
                LeaveRequestModel.leave_request_id != excluding_request_id,
                LeaveRequestDayModel.leave_date.in_(leave_dates),
            )
            .with_for_update()
        )
        return list(self.session.scalars(statement))

    def transition_status(
        self,
        leave_request_id: int,
        expected_status: str,
        target_status: str,
        reviewed_by_employee_id: int | None = None,
        reviewed_at: datetime | None = None,
        review_comment: str | None = None,
    ) -> bool:
        values: dict[str, object] = {"status": target_status}
        if target_status in {"APPROVED", "REJECTED"}:
            values.update(
                reviewed_by_employee_id=reviewed_by_employee_id,
                reviewed_at=reviewed_at,
                review_comment=review_comment,
            )
        result = self.session.execute(
            update(LeaveRequestModel)
            .where(
                LeaveRequestModel.leave_request_id == leave_request_id,
                LeaveRequestModel.status == expected_status,
            )
            .values(**values)
            .execution_options(synchronize_session=False)
        )
        return result.rowcount == 1
