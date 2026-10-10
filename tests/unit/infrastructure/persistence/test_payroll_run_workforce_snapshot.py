from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.shared.exceptions import BusinessRuleViolation

from sqlalchemy.dialects import mysql

from app.domain.payroll.payroll_run_workforce_snapshot import (
    PayrollRunWorkforceSnapshot,
)
from app.infrastructure.persistence.models.payroll_result import PayrollResultModel
from app.infrastructure.persistence.models.payroll_run import PayrollRunModel
from app.infrastructure.persistence.models.payroll_run_workforce_snapshot import (
    PayrollRunWorkforceSnapshotModel,
)
from app.infrastructure.persistence.models.base import Base
from app.infrastructure.persistence.repositories.payroll_run_workforce_snapshot_repository import (
    PayrollRunWorkforceSnapshotRepository,
)


def test_payroll_run_attempt_foundation_defaults_and_types() -> None:
    table = PayrollRunModel.__table__
    attempt_number = table.c.attempt_number
    lease_expiration = table.c.attempt_lease_expires_at

    assert attempt_number.nullable is False
    assert str(attempt_number.server_default.arg) == "0"
    assert attempt_number.type.compile(dialect=mysql.dialect()) == "BIGINT UNSIGNED"
    assert lease_expiration.nullable is True
    assert lease_expiration.server_default is None
    assert lease_expiration.type.compile(dialect=mysql.dialect()) == "DATETIME(6)"


def test_workforce_snapshot_model_has_required_schema_shape() -> None:
    table = PayrollRunWorkforceSnapshotModel.__table__

    assert tuple(column.name for column in table.primary_key.columns) == (
        "payroll_run_id",
        "employee_id",
    )
    assert table.c.payroll_run_id.type.compile(dialect=mysql.dialect()) == "BIGINT UNSIGNED"
    assert table.c.employee_id.type.compile(dialect=mysql.dialect()) == "BIGINT UNSIGNED"
    assert table.c.attempt_number.type.compile(dialect=mysql.dialect()) == "BIGINT UNSIGNED"
    assert table.c.attempt_number.nullable is False
    assert table.c.snapshot_at.type.compile(dialect=mysql.dialect()) == "DATETIME(6)"
    assert table.c.snapshot_at.nullable is False
    assert table.c.snapshot.type.compile(dialect=mysql.dialect()) == "JSON"
    assert table.c.snapshot.nullable is False
    assert {
        foreign_key.target_fullname
        for foreign_key in table.c.payroll_run_id.foreign_keys
    } == {"payroll_runs.payroll_run_id"}
    assert {
        foreign_key.target_fullname
        for foreign_key in table.c.employee_id.foreign_keys
    } == {"employees.employee_id"}
    assert all(
        foreign_key.ondelete == "RESTRICT" and foreign_key.onupdate == "RESTRICT"
        for column in (table.c.payroll_run_id, table.c.employee_id)
        for foreign_key in column.foreign_keys
    )
    assert any(
        index.name == "idx_payroll_run_workforce_snapshots_attempt"
        and tuple(column.name for column in index.columns)
        == ("payroll_run_id", "attempt_number")
        for index in table.indexes
    )


def test_payroll_run_workforce_snapshot_creation_and_retrieval() -> None:
    session = MagicMock()
    payroll_runs = MagicMock()
    payroll_runs.lock_active_attempt.return_value = object()
    repository = PayrollRunWorkforceSnapshotRepository(session, payroll_runs)
    timestamp = datetime(2026, 10, 7, 9, 30, 0, 123456)
    source_json = {"format_version": "1", "attendance": [{"status": "PRESENT"}]}
    snapshot = PayrollRunWorkforceSnapshot(
        payroll_run_id=8,
        employee_id=13,
        attempt_number=2,
        snapshot_at=timestamp,
        snapshot=source_json,
    )
    source_json["format_version"] = "mutated"
    assert snapshot.snapshot["format_version"] == "1"
    assert snapshot.snapshot["attendance"][0]["status"] == "PRESENT"
    try:
        snapshot.snapshot["format_version"] = "mutated"
    except TypeError:
        pass
    else:
        raise AssertionError("Snapshot persistence DTO must be immutable.")

    created = repository.add(snapshot, expected_attempt_number=2)

    payroll_runs.lock_active_attempt.assert_called_once_with(8, 2)
    session.add.assert_called_once()
    session.flush.assert_called_once()
    assert created == snapshot
    model = session.add.call_args.args[0]
    session.get.return_value = model
    assert repository.get_by_run_and_employee(8, 13) == snapshot
    session.get.assert_called_once_with(PayrollRunWorkforceSnapshotModel, (8, 13))


def test_payroll_run_workforce_snapshot_list_and_delete_are_attempt_scoped() -> None:
    session = MagicMock()
    repository = PayrollRunWorkforceSnapshotRepository(session, MagicMock())
    model = PayrollRunWorkforceSnapshotModel(
        payroll_run_id=8,
        employee_id=13,
        attempt_number=2,
        snapshot_at=datetime(2026, 10, 7, 9, 30),
        snapshot={"format_version": "1"},
    )
    session.scalars.return_value = [model]
    session.execute.return_value.rowcount = 1

    listed = repository.list_by_run_and_attempt(8, 2)
    deleted = repository.delete_by_run_and_attempt(8, 2)

    assert len(listed) == 1
    assert (listed[0].payroll_run_id, listed[0].employee_id) == (8, 13)
    assert listed[0].attempt_number == 2
    assert deleted == 1
    assert "payroll_run_workforce_snapshots.attempt_number" in str(
        session.execute.call_args.args[0]
    )


def test_workforce_snapshot_add_rejects_inactive_attempt() -> None:
    session = MagicMock()
    payroll_runs = MagicMock()
    payroll_runs.lock_active_attempt.return_value = None
    repository = PayrollRunWorkforceSnapshotRepository(session, payroll_runs)
    snapshot = PayrollRunWorkforceSnapshot(
        payroll_run_id=8,
        employee_id=13,
        attempt_number=2,
        snapshot_at=datetime(2026, 10, 7, 9, 30),
        snapshot={"format_version": "1"},
    )

    with pytest.raises(BusinessRuleViolation, match="attempt is no longer active"):
        repository.add(snapshot, expected_attempt_number=2)
    session.add.assert_not_called()
    session.flush.assert_not_called()


def test_workforce_snapshot_add_rejects_mismatched_payload_attempt() -> None:
    session = MagicMock()
    payroll_runs = MagicMock()
    payroll_runs.lock_active_attempt.return_value = SimpleNamespace(
        payroll_run_id=8, attempt_number=2
    )
    repository = PayrollRunWorkforceSnapshotRepository(session, payroll_runs)
    snapshot = PayrollRunWorkforceSnapshot(
        payroll_run_id=8,
        employee_id=13,
        attempt_number=1,
        snapshot_at=datetime(2026, 10, 7, 9, 30),
        snapshot={"format_version": "1"},
    )

    with pytest.raises(BusinessRuleViolation, match="does not match the active attempt"):
        repository.add(snapshot, expected_attempt_number=2)
    session.add.assert_not_called()
    session.flush.assert_not_called()


def test_duplicate_active_attempt_snapshot_is_rejected_by_primary_key() -> None:
    engine = create_engine("sqlite://")
    table = PayrollRunWorkforceSnapshotModel.__table__
    Base.metadata.create_all(engine, tables=[table])
    timestamp = datetime(2026, 10, 7, 9, 30)
    snapshot = PayrollRunWorkforceSnapshot(
        payroll_run_id=8,
        employee_id=13,
        attempt_number=2,
        snapshot_at=timestamp,
        snapshot={"snapshot_format_version": 1},
    )
    parent = MagicMock()
    parent.lock_active_attempt.return_value = object()

    with Session(engine) as session:
        repository = PayrollRunWorkforceSnapshotRepository(session, parent)
        repository.add(snapshot, expected_attempt_number=2)
        session.commit()

        with pytest.raises(IntegrityError):
            repository.add(snapshot, expected_attempt_number=2)
        session.rollback()
        assert session.scalar(
            select(func.count()).select_from(PayrollRunWorkforceSnapshotModel)
        ) == 1
    engine.dispose()


def test_payroll_result_snapshot_and_uniqueness_remain_unchanged() -> None:
    result_table = PayrollResultModel.__table__
    snapshot = result_table.c.workforce_calculation_snapshot

    assert snapshot.nullable is True
    assert snapshot.type.compile(dialect=mysql.dialect()) == "JSON"
    assert any(
        tuple(column.name for column in constraint.columns)
        == ("payroll_run_id", "employee_id")
        for constraint in result_table.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    )
