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

    def add(self, attendance: AttendanceRecord) -> AttendanceRecord:
        self.session.add(attendance)
        self.session.flush()
        return attendance