from datetime import date
from unittest.mock import MagicMock

from app.infrastructure.persistence.models.attendance import AttendanceRecord
from app.infrastructure.persistence.repositories.attendance_repository import (
    AttendanceRepository,
)


def test_get_by_id() -> None:
    session = MagicMock()
    expected = AttendanceRecord(
        attendance_id=1,
        employee_id=10,
        attendance_date=date(2026, 9, 19),
        attendance_status="PRESENT",
    )

    session.scalar.return_value = expected

    repository = AttendanceRepository(session)

    result = repository.get_by_id(1)

    assert result is expected
    session.scalar.assert_called_once()


def test_get_by_employee_and_date() -> None:
    session = MagicMock()
    expected = AttendanceRecord(
        attendance_id=1,
        employee_id=10,
        attendance_date=date(2026, 9, 19),
        attendance_status="PRESENT",
    )

    session.scalar.return_value = expected

    repository = AttendanceRepository(session)

    result = repository.get_by_employee_and_date(
        employee_id=10,
        attendance_date=date(2026, 9, 19),
    )

    assert result is expected
    session.scalar.assert_called_once()


def test_add() -> None:
    session = MagicMock()

    attendance = AttendanceRecord(
        employee_id=10,
        attendance_date=date(2026, 9, 19),
        attendance_status="PRESENT",
    )

    repository = AttendanceRepository(session)

    result = repository.add(attendance)

    assert result is attendance
    session.add.assert_called_once_with(attendance)
    session.flush.assert_called_once()