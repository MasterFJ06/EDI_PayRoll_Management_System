from datetime import date

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.domain.attendance.attendance_report import AttendanceReportRecord
from app.infrastructure.persistence.models.department import Department
from app.infrastructure.persistence.models.designation import Designation
from app.infrastructure.persistence.models.attendance import AttendanceRecord
from app.infrastructure.persistence.models.employee import Employee


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

    def get_for_employee_period(self, employee_id: int, start_date: date, end_date: date) -> list[AttendanceRecord]:
        statement = (
            select(AttendanceRecord)
            .where(
                AttendanceRecord.employee_id == employee_id,
                AttendanceRecord.attendance_date >= start_date,
                AttendanceRecord.attendance_date <= end_date,
            )
            .order_by(AttendanceRecord.attendance_date, AttendanceRecord.attendance_id)
        )
        return list(self.session.scalars(statement).all())

    def list_report_page(
        self,
        date_from: date | None,
        date_to: date | None,
        employee_id: int | None,
        department_id: int | None,
        attendance_status: str | None,
        after_attendance_date: date | None,
        after_attendance_id: int | None,
        limit: int,
    ) -> list[AttendanceReportRecord]:
        statement = (
            select(
                AttendanceRecord.attendance_id,
                AttendanceRecord.employee_id,
                Employee.employee_code,
                Employee.first_name,
                Employee.last_name,
                Employee.department_id,
                Department.department_name,
                Employee.designation_id,
                Designation.designation_name,
                AttendanceRecord.attendance_date,
                AttendanceRecord.attendance_status,
                AttendanceRecord.check_in_time,
                AttendanceRecord.check_out_time,
            )
            .select_from(AttendanceRecord)
            .join(Employee, Employee.employee_id == AttendanceRecord.employee_id)
            .outerjoin(Department, Department.department_id == Employee.department_id)
            .outerjoin(Designation, Designation.designation_id == Employee.designation_id)
        )
        if date_from is not None:
            statement = statement.where(AttendanceRecord.attendance_date >= date_from)
        if date_to is not None:
            statement = statement.where(AttendanceRecord.attendance_date <= date_to)
        if employee_id is not None:
            statement = statement.where(AttendanceRecord.employee_id == employee_id)
        if department_id is not None:
            statement = statement.where(Employee.department_id == department_id)
        if attendance_status is not None:
            statement = statement.where(
                AttendanceRecord.attendance_status == attendance_status
            )
        if after_attendance_date is not None and after_attendance_id is not None:
            statement = statement.where(
                or_(
                    AttendanceRecord.attendance_date > after_attendance_date,
                    and_(
                        AttendanceRecord.attendance_date == after_attendance_date,
                        AttendanceRecord.attendance_id > after_attendance_id,
                    ),
                )
            )
        statement = statement.order_by(
            AttendanceRecord.attendance_date.asc(),
            AttendanceRecord.attendance_id.asc(),
        ).limit(limit)

        return [
            AttendanceReportRecord(
                attendance_id=row.attendance_id,
                employee_id=row.employee_id,
                employee_code=row.employee_code,
                first_name=row.first_name,
                last_name=row.last_name,
                department_id=row.department_id,
                department_name=row.department_name,
                designation_id=row.designation_id,
                designation_name=row.designation_name,
                attendance_date=row.attendance_date,
                attendance_status=row.attendance_status,
                check_in_time=row.check_in_time,
                check_out_time=row.check_out_time,
            )
            for row in self.session.execute(statement)
        ]

    def add(self, attendance: AttendanceRecord) -> AttendanceRecord:
        self.session.add(attendance)
        self.session.flush()
        return attendance
