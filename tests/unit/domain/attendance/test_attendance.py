from datetime import date, datetime

import pytest

from app.domain.attendance.attendance import Attendance
from app.domain.shared.exceptions import BusinessRuleViolation


def test_create_valid_attendance() -> None:
    attendance = Attendance(
        attendance_id=None,
        employee_id=1,
        attendance_date=date(2026, 9, 19),
        attendance_status="PRESENT",
        check_in_time=datetime(2026, 9, 19, 9, 0),
        check_out_time=datetime(2026, 9, 19, 18, 0),
    )

    assert attendance.id is None
    assert attendance.employee_id == 1
    assert attendance.attendance_date == date(2026, 9, 19)
    assert attendance.attendance_status == "PRESENT"
    assert attendance.check_in_time == datetime(2026, 9, 19, 9, 0)
    assert attendance.check_out_time == datetime(2026, 9, 19, 18, 0)


def test_attendance_status_is_normalized_to_uppercase() -> None:
    attendance = Attendance(
        attendance_id=None,
        employee_id=1,
        attendance_date=date(2026, 9, 19),
        attendance_status="present",
    )

    assert attendance.attendance_status == "PRESENT"


def test_all_valid_attendance_statuses_are_accepted() -> None:
    valid_statuses = [
        "PRESENT",
        "ABSENT",
        "HALF_DAY",
        "ON_LEAVE",
        "HOLIDAY",
    ]

    for status in valid_statuses:
        attendance = Attendance(
            attendance_id=None,
            employee_id=1,
            attendance_date=date(2026, 9, 19),
            attendance_status=status,
        )

        assert attendance.attendance_status == status


def test_invalid_employee_id_is_rejected() -> None:
    with pytest.raises(
        BusinessRuleViolation,
        match="Employee ID must be positive.",
    ):
        Attendance(
            attendance_id=None,
            employee_id=0,
            attendance_date=date(2026, 9, 19),
            attendance_status="PRESENT",
        )


def test_invalid_attendance_status_is_rejected() -> None:
    with pytest.raises(
        BusinessRuleViolation,
        match="Attendance status must be PRESENT, ABSENT, HALF_DAY, "
        "ON_LEAVE, or HOLIDAY.",
    ):
        Attendance(
            attendance_id=None,
            employee_id=1,
            attendance_date=date(2026, 9, 19),
            attendance_status="INVALID",
        )


def test_checkout_before_checkin_is_rejected() -> None:
    with pytest.raises(
        BusinessRuleViolation,
        match="Check-out time cannot be earlier than check-in time.",
    ):
        Attendance(
            attendance_id=None,
            employee_id=1,
            attendance_date=date(2026, 9, 19),
            attendance_status="PRESENT",
            check_in_time=datetime(2026, 9, 19, 18, 0),
            check_out_time=datetime(2026, 9, 19, 9, 0),
        )


def test_checkout_equal_to_checkin_is_allowed() -> None:
    check_time = datetime(2026, 9, 19, 9, 0)

    attendance = Attendance(
        attendance_id=None,
        employee_id=1,
        attendance_date=date(2026, 9, 19),
        attendance_status="PRESENT",
        check_in_time=check_time,
        check_out_time=check_time,
    )

    assert attendance.check_in_time == attendance.check_out_time


def test_attendance_without_checkin_or_checkout_is_allowed() -> None:
    attendance = Attendance(
        attendance_id=None,
        employee_id=1,
        attendance_date=date(2026, 9, 19),
        attendance_status="ABSENT",
    )

    assert attendance.check_in_time is None
    assert attendance.check_out_time is None