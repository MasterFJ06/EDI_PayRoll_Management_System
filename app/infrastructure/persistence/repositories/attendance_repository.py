from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.persistence.models.attendance import AttendanceRecord


class AttendanceRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, attendance_id: int) -> AttendanceRecord | None:
        statement = select(AttendanceRecord).where(
            AttendanceRecord.attendance_id == attendance_id
        )
        return self.session.scalar(statement)

    def get_by_employee_and_date(
        self,
        employee_id: int,
        attendance_date: date,
    ) -> AttendanceRecord | None:
        statement = select(AttendanceRecord).where(
            AttendanceRecord.employee_id == employee_id,
            AttendanceRecord.attendance_date == attendance_date,
        )
        return self.session.scalar(statement)

    def get_all(self) -> list[AttendanceRecord]:
        statement = select(AttendanceRecord).order_by(
            AttendanceRecord.attendance_date.desc(),
            AttendanceRecord.attendance_id.desc(),
        )
        return list(self.session.scalars(statement).all())

    def get_all_by_employee(self, employee_id: int) -> list[AttendanceRecord]:
        statement = (
            select(AttendanceRecord)
            .where(AttendanceRecord.employee_id == employee_id)
            .order_by(AttendanceRecord.attendance_date.desc())
        )
        return list(self.session.scalars(statement).all())

    def add(self, attendance: AttendanceRecord) -> AttendanceRecord:
        self.session.add(attendance)
        self.session.flush()
        return attendance

    def update(self, attendance: AttendanceRecord) -> AttendanceRecord:
        self.session.merge(attendance)
        self.session.flush()
        return attendance