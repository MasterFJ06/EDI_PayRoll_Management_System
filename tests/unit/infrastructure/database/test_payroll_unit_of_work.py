from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import text
from sqlalchemy.dialects import mysql

from app.infrastructure.database.unit_of_work import SQLAlchemyUnitOfWork


def test_payroll_repositories_share_uow_session_and_are_released() -> None:
    session = MagicMock()
    uow = SQLAlchemyUnitOfWork()
    with patch("app.infrastructure.database.unit_of_work.SessionLocal", return_value=session):
        with uow:
            assert (
                uow.payroll_run_workforce_snapshots.payroll_runs
                is uow.payroll_runs
            )
            repositories = (
                uow.audit_events,
                uow.payroll_runs,
                uow.payroll_run_workforce_snapshots,
                uow.payroll_results,
                uow.payroll_result_components,
                uow.payroll_processing_issues,
                uow.payslips,
            )
            assert all(repository.session is session for repository in repositories)
    session.close.assert_called_once()
    assert all(
        repository is None
        for repository in (
            uow.payroll_runs,
            uow.payroll_run_workforce_snapshots,
            uow.payroll_results,
            uow.payroll_result_components,
            uow.payroll_processing_issues,
            uow.payslips,
        )
    )
    assert uow.audit_events is None


def test_payroll_operation_failure_rolls_back_without_committing() -> None:
    session = MagicMock()
    with patch("app.infrastructure.database.unit_of_work.SessionLocal", return_value=session):
        with pytest.raises(RuntimeError):
            with SQLAlchemyUnitOfWork():
                raise RuntimeError("payroll persistence failure")
    session.rollback.assert_called_once()
    session.commit.assert_not_called()
    session.close.assert_called_once()


def test_workforce_consistent_read_sets_isolation_snapshot_and_db_timestamp() -> None:
    session = MagicMock()
    session.in_transaction.return_value = False
    connection = session.connection.return_value
    connection.dialect.name = "mysql"
    timestamp = datetime(2026, 10, 8, 12, 30, 0, 123456)
    connection.scalar.return_value = timestamp
    with patch("app.infrastructure.database.unit_of_work.SessionLocal", return_value=session):
        with SQLAlchemyUnitOfWork() as uow:
            actual = uow.begin_workforce_consistent_read()

    assert actual == timestamp
    session.expire_all.assert_called_once_with()
    session.connection.assert_called_once_with(
        execution_options={"isolation_level": "REPEATABLE READ"}
    )
    connection.exec_driver_sql.assert_called_once_with(
        "START TRANSACTION WITH CONSISTENT SNAPSHOT"
    )
    assert str(connection.scalar.call_args.args[0]) == "SELECT CURRENT_TIMESTAMP(6)"
    assert str(
        text("SELECT CURRENT_TIMESTAMP(6)").compile(dialect=mysql.dialect())
    ) == "SELECT CURRENT_TIMESTAMP(6)"


def test_workforce_consistent_read_rejects_non_mysql_and_active_transaction() -> None:
    session = MagicMock()
    session.in_transaction.return_value = False
    session.connection.return_value.dialect.name = "sqlite"
    with patch("app.infrastructure.database.unit_of_work.SessionLocal", return_value=session):
        with SQLAlchemyUnitOfWork() as uow:
            with pytest.raises(RuntimeError, match="require MySQL/InnoDB"):
                uow.begin_workforce_consistent_read()

    session.connection.return_value.exec_driver_sql.assert_not_called()

    session = MagicMock()
    session.in_transaction.return_value = True
    with patch("app.infrastructure.database.unit_of_work.SessionLocal", return_value=session):
        with SQLAlchemyUnitOfWork() as uow:
            with pytest.raises(RuntimeError, match="prior transaction ends"):
                uow.begin_workforce_consistent_read()
