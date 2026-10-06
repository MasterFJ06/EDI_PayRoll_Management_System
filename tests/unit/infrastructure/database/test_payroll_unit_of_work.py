from unittest.mock import MagicMock, patch

import pytest

from app.infrastructure.database.unit_of_work import SQLAlchemyUnitOfWork


def test_payroll_repositories_share_uow_session_and_are_released() -> None:
    session = MagicMock()
    uow = SQLAlchemyUnitOfWork()
    with patch("app.infrastructure.database.unit_of_work.SessionLocal", return_value=session):
        with uow:
            repositories = (
                uow.audit_events,
                uow.payroll_runs,
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
