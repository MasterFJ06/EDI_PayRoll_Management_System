from unittest.mock import MagicMock, patch

from app.infrastructure.database.unit_of_work import SQLAlchemyUnitOfWork


def test_compensation_repositories_share_unit_of_work_session_and_are_released() -> None:
    session = MagicMock()
    uow = SQLAlchemyUnitOfWork()
    with patch("app.infrastructure.database.unit_of_work.SessionLocal", return_value=session):
        uow.__enter__()
        repositories = (
            uow.salary_structures,
            uow.salary_components,
            uow.salary_revisions,
            uow.salary_revision_components,
            uow.employee_salary_assignments,
        )
        assert all(repository.session is session for repository in repositories)
        uow.__exit__(None, None, None)

    session.close.assert_called_once()
    assert uow.salary_structures is None
    assert uow.salary_components is None
    assert uow.salary_revisions is None
    assert uow.salary_revision_components is None
    assert uow.employee_salary_assignments is None


def test_unit_of_work_commits_through_shared_session() -> None:
    session = MagicMock()
    with patch("app.infrastructure.database.unit_of_work.SessionLocal", return_value=session):
        with SQLAlchemyUnitOfWork() as uow:
            uow.commit()

    session.commit.assert_called_once()
    session.rollback.assert_not_called()
    session.close.assert_called_once()


def test_unit_of_work_rolls_back_on_exception() -> None:
    session = MagicMock()
    with patch("app.infrastructure.database.unit_of_work.SessionLocal", return_value=session):
        try:
            with SQLAlchemyUnitOfWork():
                raise RuntimeError("transaction failure")
        except RuntimeError:
            pass
        else:
            raise AssertionError("the context must propagate transaction failures")

    session.rollback.assert_called_once()
    session.close.assert_called_once()
