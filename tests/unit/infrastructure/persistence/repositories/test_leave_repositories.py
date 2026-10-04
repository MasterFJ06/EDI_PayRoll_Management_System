from unittest.mock import MagicMock

from app.infrastructure.persistence.models.leave_balance import LeaveBalanceModel
from app.infrastructure.persistence.models.leave_request import LeaveRequestModel
from app.infrastructure.persistence.models.leave_type import LeaveTypeModel
from app.infrastructure.persistence.repositories.leave_balance_repository import (
    LeaveBalanceRepository,
)
from app.infrastructure.persistence.repositories.leave_request_repository import (
    LeaveRequestRepository,
)
from app.infrastructure.persistence.repositories.leave_type_repository import (
    LeaveTypeRepository,
)


def test_leave_type_getters_use_shared_session() -> None:
    session = MagicMock()
    expected = LeaveTypeModel(leave_type_id=1, leave_type_code="AL", leave_type_name="Annual")
    session.scalar.return_value = expected
    repository = LeaveTypeRepository(session)

    assert repository.get_by_id(1) is expected
    assert repository.get_by_code("AL") is expected
    assert repository.get_by_name("Annual") is expected
    assert session.scalar.call_count == 3


def test_leave_type_add_flushes_without_committing() -> None:
    session = MagicMock()
    model = LeaveTypeModel(leave_type_code="AL", leave_type_name="Annual")

    assert LeaveTypeRepository(session).add(model) is model
    session.add.assert_called_once_with(model)
    session.flush.assert_called_once()
    session.commit.assert_not_called()


def test_leave_balance_retrieval_and_add() -> None:
    session = MagicMock()
    expected = LeaveBalanceModel(leave_balance_id=1)
    session.scalar.return_value = expected
    repository = LeaveBalanceRepository(session)

    assert repository.get_by_id(1) is expected
    assert repository.get_by_employee_type_year(5, 2, 2026) is expected
    assert repository.add(expected) is expected
    assert session.scalar.call_count == 2
    session.add.assert_called_once_with(expected)
    session.flush.assert_called_once()
    session.commit.assert_not_called()


def test_leave_request_retrieval_and_add() -> None:
    session = MagicMock()
    expected = LeaveRequestModel(leave_request_id=1)
    session.scalar.return_value = expected
    repository = LeaveRequestRepository(session)

    assert repository.get_by_id(1) is expected
    assert repository.add(expected) is expected
    session.add.assert_called_once_with(expected)
    session.flush.assert_called_once()
    session.commit.assert_not_called()
