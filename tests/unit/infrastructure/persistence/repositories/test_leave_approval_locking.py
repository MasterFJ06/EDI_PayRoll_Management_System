from datetime import date
from unittest.mock import MagicMock

from sqlalchemy.dialects import mysql

from app.infrastructure.persistence.repositories.employee_repository import EmployeeRepository
from app.infrastructure.persistence.repositories.leave_request_repository import LeaveRequestRepository


def test_approval_employee_lock_compiles_to_mysql_for_update() -> None:
    session = MagicMock()
    EmployeeRepository(session).get_by_id_for_update(5)
    statement = session.scalar.call_args.args[0]
    assert "FOR UPDATE" in str(statement.compile(dialect=mysql.dialect()))


def test_approved_conflict_read_is_a_mysql_current_locking_read() -> None:
    session = MagicMock()
    LeaveRequestRepository(session).find_approved_conflicts(
        employee_id=5,
        leave_dates=[date(2026, 10, 12)],
        excluding_request_id=99,
    )
    statement = session.scalars.call_args.args[0]
    compiled = statement.compile(dialect=mysql.dialect())
    sql = str(compiled)
    assert "FOR UPDATE" in sql
    assert "APPROVED" in compiled.params.values()


def test_transition_is_conditioned_on_expected_status() -> None:
    session = MagicMock()
    session.execute.return_value.rowcount = 1
    assert LeaveRequestRepository(session).transition_status(
        7, "PENDING", "APPROVED", 8
    )
    statement = session.execute.call_args.args[0]
    compiled = statement.compile(dialect=mysql.dialect())
    sql = str(compiled)
    assert "status" in sql
    assert "PENDING" in compiled.params.values()
