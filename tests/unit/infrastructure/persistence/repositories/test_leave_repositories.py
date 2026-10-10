from unittest.mock import MagicMock
from datetime import date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects import mysql
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.infrastructure.persistence.models.leave_balance import LeaveBalanceModel
from app.infrastructure.persistence.models.leave_request import LeaveRequestModel
from app.infrastructure.persistence.models.leave_request_day import LeaveRequestDayModel
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
    expected = LeaveTypeModel(leave_type_id=1, leave_type_code="AL", leave_type_name="Annual", payroll_treatment="PAID")
    session.scalar.return_value = expected
    repository = LeaveTypeRepository(session)

    assert repository.get_by_id(1) is expected
    assert repository.get_by_code("AL") is expected
    assert repository.get_by_name("Annual") is expected
    assert session.scalar.call_count == 3


def test_leave_type_add_flushes_without_committing() -> None:
    session = MagicMock()
    model = LeaveTypeModel(leave_type_code="AL", leave_type_name="Annual", payroll_treatment="PAID")

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


def test_leave_request_day_repository_persists_exact_decimal_and_enforces_unique_date() -> None:
    engine = create_engine("sqlite://")
    LeaveRequestDayModel.__table__.create(engine)
    with Session(engine) as session:
        repository = LeaveRequestRepository(session)
        from app.domain.leave.leave_request_day import LeaveRequestDay

        repository.add_days(
            1,
            [LeaveRequestDay(date(2026, 10, 12), Decimal("0.75"))],
        )
        session.commit()
        loaded = repository.get_days(1)
        assert loaded[0].day_fraction == Decimal("0.75")
        with pytest.raises(IntegrityError):
            repository.add_days(
                1,
                [LeaveRequestDay(date(2026, 10, 12), Decimal("0.25"))],
            )
        session.rollback()
    engine.dispose()


def test_approved_allocation_read_is_employee_date_range_scoped_and_per_date() -> None:
    session = MagicMock()
    request = LeaveRequestModel(
        leave_request_id=10, employee_id=7, leave_type_id=1, status="APPROVED"
    )
    allocations = [
        LeaveRequestDayModel(
            leave_request_id=10,
            leave_date=date(2026, 6, 30),
            day_fraction=Decimal("0.50"),
        ),
        LeaveRequestDayModel(
            leave_request_id=10,
            leave_date=date(2026, 7, 1),
            day_fraction=Decimal("0.25"),
        ),
    ]
    leave_type = LeaveTypeModel(payroll_treatment="PAID")
    session.execute.return_value.all.return_value = [
        (request, allocation, leave_type) for allocation in allocations
    ]

    rows = LeaveRequestRepository(session).get_approved_allocations_for_employee_period(
        7, date(2026, 6, 30), date(2026, 7, 1)
    )
    assert [
        (row[0].leave_request_id, row[1].leave_date, row[1].day_fraction,
         row[2].payroll_treatment)
        for row in rows
    ] == [
        (10, date(2026, 6, 30), Decimal("0.50"), "PAID"),
        (10, date(2026, 7, 1), Decimal("0.25"), "PAID"),
    ]
    statement = session.execute.call_args.args[0]
    sql = str(statement.compile(dialect=mysql.dialect(), compile_kwargs={"literal_binds": True}))
    assert "leave_requests.employee_id = 7" in sql
    assert "leave_requests.status = 'APPROVED'" in sql
    assert "leave_request_days.leave_date >= '2026-06-30'" in sql
    assert "leave_request_days.leave_date <= '2026-07-01'" in sql
