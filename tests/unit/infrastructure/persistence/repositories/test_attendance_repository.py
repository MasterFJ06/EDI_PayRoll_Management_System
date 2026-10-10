from datetime import date
from unittest.mock import MagicMock

from sqlalchemy.dialects import mysql

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


def test_get_for_employee_period_uses_inclusive_employee_scoped_range() -> None:
    session = MagicMock()
    expected = [
        AttendanceRecord(
            attendance_id=1,
            employee_id=10,
            attendance_date=date(2026, 9, 1),
            attendance_status="PRESENT",
        ),
        AttendanceRecord(
            attendance_id=2,
            employee_id=10,
            attendance_date=date(2026, 9, 30),
            attendance_status="HALF_DAY",
        ),
    ]
    session.scalars.return_value.all.return_value = expected
    repository = AttendanceRepository(session)

    result = repository.get_for_employee_period(
        10, date(2026, 9, 1), date(2026, 9, 30)
    )

    assert result == expected
    statement = session.scalars.call_args.args[0]
    sql = str(statement.compile(dialect=mysql.dialect(), compile_kwargs={"literal_binds": True}))
    assert "attendance_records.employee_id = 10" in sql
    assert "attendance_records.attendance_date >= '2026-09-01'" in sql
    assert "attendance_records.attendance_date <= '2026-09-30'" in sql


def test_get_for_employee_period_returns_empty_when_no_rows_exist() -> None:
    session = MagicMock()
    session.scalars.return_value.all.return_value = []
    assert AttendanceRepository(session).get_for_employee_period(
        10, date(2026, 9, 1), date(2026, 9, 30)
    ) == []


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
