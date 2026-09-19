from datetime import date, datetime
from unittest.mock import MagicMock

import pytest

from app.application.attendance.attendance_service import AttendanceService
from app.application.attendance.schemas import AttendanceCreateRequest
from app.domain.shared.exceptions import BusinessRuleViolation


def create_request() -> AttendanceCreateRequest:
    return AttendanceCreateRequest(
        employee_id=10,
        attendance_date=date(2026, 9, 19),
        check_in_time=datetime(2026, 9, 19, 9, 0),
        check_out_time=datetime(2026, 9, 19, 18, 0),
        attendance_status="PRESENT",
    )


def test_create_attendance_success() -> None:
    uow = MagicMock()

    employee = MagicMock()
    employee.employee_id = 10

    uow.employees.get_by_id.return_value = employee
    uow.attendance.get_by_employee_and_date.return_value = None

    attendance_record = MagicMock()
    attendance_record.attendance_id = 1

    def add_attendance(record) -> None:
        record.attendance_id = 1

    uow.attendance.add.side_effect = add_attendance

    service = AttendanceService(uow)

    result = service.create(create_request())

    assert result.attendance_id == 1
    assert result.employee_id == 10
    assert result.attendance_date == date(2026, 9, 19)
    assert result.attendance_status == "PRESENT"

    uow.employees.get_by_id.assert_called_once_with(10)
    uow.attendance.get_by_employee_and_date.assert_called_once_with(
        employee_id=10,
        attendance_date=date(2026, 9, 19),
    )
    uow.attendance.add.assert_called_once()
    uow.commit.assert_called_once()


def test_create_attendance_rejects_nonexistent_employee() -> None:
    uow = MagicMock()

    uow.employees.get_by_id.return_value = None

    service = AttendanceService(uow)

    with pytest.raises(
        BusinessRuleViolation,
        match="Employee does not exist.",
    ):
        service.create(create_request())

    uow.attendance.get_by_employee_and_date.assert_not_called()
    uow.attendance.add.assert_not_called()
    uow.commit.assert_not_called()


def test_create_attendance_rejects_duplicate_date() -> None:
    uow = MagicMock()

    employee = MagicMock()
    employee.employee_id = 10

    existing_attendance = MagicMock()

    uow.employees.get_by_id.return_value = employee
    uow.attendance.get_by_employee_and_date.return_value = (
        existing_attendance
    )

    service = AttendanceService(uow)

    with pytest.raises(
        BusinessRuleViolation,
        match="Attendance already exists for this employee and date.",
    ):
        service.create(create_request())

    uow.attendance.add.assert_not_called()
    uow.commit.assert_not_called()


def test_create_attendance_rejects_invalid_status() -> None:
    uow = MagicMock()

    employee = MagicMock()
    employee.employee_id = 10

    uow.employees.get_by_id.return_value = employee
    uow.attendance.get_by_employee_and_date.return_value = None

    request = create_request()
    request.attendance_status = "INVALID"

    service = AttendanceService(uow)

    with pytest.raises(
        BusinessRuleViolation,
        match="Attendance status must be PRESENT, ABSENT, HALF_DAY, "
        "ON_LEAVE, or HOLIDAY.",
    ):
        service.create(request)

    uow.attendance.add.assert_not_called()
    uow.commit.assert_not_called()


def test_create_attendance_rejects_checkout_before_checkin() -> None:
    uow = MagicMock()

    employee = MagicMock()
    employee.employee_id = 10

    uow.employees.get_by_id.return_value = employee
    uow.attendance.get_by_employee_and_date.return_value = None

    request = create_request()
    request.check_in_time = datetime(2026, 9, 19, 18, 0)
    request.check_out_time = datetime(2026, 9, 19, 9, 0)

    service = AttendanceService(uow)

    with pytest.raises(
        BusinessRuleViolation,
        match="Check-out time cannot be earlier than check-in time.",
    ):
        service.create(request)

    uow.attendance.add.assert_not_called()
    uow.commit.assert_not_called()