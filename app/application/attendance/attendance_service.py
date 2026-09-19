from app.application.attendance.schemas import (
    AttendanceCreateRequest,
    AttendanceResponse,
)
from app.application.common.unit_of_work import UnitOfWork
from app.domain.attendance.attendance import Attendance
from app.domain.shared.exceptions import BusinessRuleViolation
from app.infrastructure.persistence.models.attendance import AttendanceRecord


class AttendanceService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def create(
        self,
        request: AttendanceCreateRequest,
    ) -> AttendanceResponse:
        employee = self.uow.employees.get_by_id(request.employee_id)

        if employee is None:
            raise BusinessRuleViolation(
                "Employee does not exist."
            )

        existing_attendance = (
            self.uow.attendance.get_by_employee_and_date(
                employee_id=request.employee_id,
                attendance_date=request.attendance_date,
            )
        )

        if existing_attendance is not None:
            raise BusinessRuleViolation(
                "Attendance already exists for this employee and date."
            )

        attendance = Attendance(
            attendance_id=None,
            employee_id=request.employee_id,
            attendance_date=request.attendance_date,
            attendance_status=request.attendance_status,
            check_in_time=request.check_in_time,
            check_out_time=request.check_out_time,
        )

        attendance_record = AttendanceRecord(
            employee_id=attendance.employee_id,
            attendance_date=attendance.attendance_date,
            check_in_time=attendance.check_in_time,
            check_out_time=attendance.check_out_time,
            attendance_status=attendance.attendance_status,
        )

        self.uow.attendance.add(attendance_record)
        self.uow.commit()

        return AttendanceResponse(
            attendance_id=attendance_record.attendance_id,
            employee_id=attendance_record.employee_id,
            attendance_date=attendance_record.attendance_date,
            check_in_time=attendance_record.check_in_time,
            check_out_time=attendance_record.check_out_time,
            attendance_status=attendance_record.attendance_status,
        )