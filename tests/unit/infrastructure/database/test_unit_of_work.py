from unittest.mock import MagicMock, patch

from app.infrastructure.database.unit_of_work import SQLAlchemyUnitOfWork


def test_leave_repositories_share_unit_of_work_session_and_are_released() -> None:
    session = MagicMock()
    uow = SQLAlchemyUnitOfWork()

    with patch("app.infrastructure.database.unit_of_work.SessionLocal", return_value=session):
        entered = uow.__enter__()
        assert entered is uow
        assert uow.authorization.session is session
        assert uow.leave_types.session is session
        assert uow.leave_balances.session is session
        assert uow.leave_requests.session is session

        uow.__exit__(None, None, None)

    session.close.assert_called_once()
    assert uow.authorization is None
    assert uow.leave_types is None
    assert uow.leave_balances is None
    assert uow.leave_requests is None
