from queue import Queue
from threading import Barrier, Thread

from datetime import datetime

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Session

from app.infrastructure.persistence.repositories.payroll_run_repository import (
    PayrollRunRepository,
)


def _engine_with_created_run(database_path: str, status: str = "CREATED"):
    engine = create_engine(
        f"sqlite:///{database_path}", connect_args={"timeout": 10}
    )
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE payroll_runs ("
            "payroll_run_id INTEGER PRIMARY KEY, "
            "payroll_year INTEGER NOT NULL DEFAULT 2026, "
            "payroll_month INTEGER NOT NULL DEFAULT 10, "
            "status VARCHAR(20) NOT NULL, initiated_by_user_id INTEGER NOT NULL DEFAULT 1, "
            "started_at DATETIME NULL, "
            "attempt_number INTEGER NOT NULL DEFAULT 0, "
            "attempt_lease_expires_at DATETIME NULL, completed_at DATETIME NULL, "
            "finalized_at DATETIME NULL, "
            "created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, "
            "updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP)"
        )
        connection.exec_driver_sql(
            "INSERT INTO payroll_runs (payroll_run_id, status) "
            "VALUES (77, :status)",
            {"status": status},
        )
    return engine


def test_conditional_claim_changes_one_created_run_and_sets_started_at(
    tmp_path,
) -> None:
    engine = _engine_with_created_run(str(tmp_path / "claim.sqlite"))

    with Session(engine) as session:
        repository = PayrollRunRepository(session)
        assert repository.claim_for_processing(77) == 1
        session.commit()

    with engine.connect() as connection:
        run = connection.execute(
            text(
                "SELECT status, started_at, attempt_number, "
                "attempt_lease_expires_at FROM payroll_runs "
                "WHERE payroll_run_id = 77"
            )
        ).one()
    assert run.status == "PROCESSING"
    assert run.started_at is not None
    assert run.attempt_number == 1
    assert run.attempt_lease_expires_at is not None
    started_at = datetime.fromisoformat(run.started_at)
    lease_expires_at = datetime.fromisoformat(run.attempt_lease_expires_at)
    assert (lease_expires_at - started_at).total_seconds() == 900
    engine.dispose()


def test_second_claim_does_not_overwrite_started_at(tmp_path) -> None:
    engine = _engine_with_created_run(str(tmp_path / "duplicate.sqlite"))

    with Session(engine) as session:
        repository = PayrollRunRepository(session)
        assert repository.claim_for_processing(77) == 1
        session.commit()

    with engine.connect() as connection:
        original_started_at = connection.scalar(
            text("SELECT started_at FROM payroll_runs WHERE payroll_run_id = 77")
        )

    with Session(engine) as session:
        assert PayrollRunRepository(session).claim_for_processing(77) is None
        session.commit()

    with engine.connect() as connection:
        run = connection.execute(
            text(
                "SELECT status, started_at, attempt_number FROM payroll_runs "
                "WHERE payroll_run_id = 77"
            )
        ).one()
    assert run.status == "PROCESSING"
    assert run.started_at == original_started_at
    assert run.attempt_number == 1
    engine.dispose()


def test_simultaneous_claims_have_exactly_one_winner(tmp_path) -> None:
    engine = _engine_with_created_run(str(tmp_path / "concurrent.sqlite"))
    barrier = Barrier(2)
    results: Queue[int | None | BaseException] = Queue()

    def attempt_claim() -> None:
        try:
            with Session(engine) as session:
                barrier.wait(timeout=5)
                claimed = PayrollRunRepository(session).claim_for_processing(77)
                session.commit()
                results.put(claimed)
        except BaseException as exc:  # surfaced in the main test thread
            results.put(exc)

    threads = [Thread(target=attempt_claim) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=15)

    outcomes = [results.get(timeout=1), results.get(timeout=1)]
    assert all(not thread.is_alive() for thread in threads)
    assert not any(isinstance(result, BaseException) for result in outcomes)
    assert sorted(outcomes, key=lambda outcome: outcome is None) == [1, None]

    with engine.connect() as connection:
        assert connection.scalar(
            text("SELECT status FROM payroll_runs WHERE payroll_run_id = 77")
        ) == "PROCESSING"
        assert connection.scalar(
            text("SELECT COUNT(*) FROM payroll_runs WHERE status = 'PROCESSING'")
        ) == 1
        assert connection.scalar(
            text("SELECT attempt_number FROM payroll_runs WHERE payroll_run_id = 77")
        ) == 1
    engine.dispose()


def test_failure_transition_is_conditional_on_processing_state(tmp_path) -> None:
    engine = _engine_with_created_run(str(tmp_path / "failed.sqlite"))
    with Session(engine) as session:
        repository = PayrollRunRepository(session)
        assert repository.mark_failed_if_processing(77, 1) is False
        assert repository.claim_for_processing(77) == 1
        session.commit()
        assert repository.mark_failed_if_processing(77, 1) is True
        session.commit()
        assert repository.mark_failed_if_processing(77, 1) is False

    with engine.connect() as connection:
        assert connection.scalar(
            text("SELECT status FROM payroll_runs WHERE payroll_run_id = 77")
        ) == "FAILED"
        assert connection.scalar(
            text(
                "SELECT attempt_lease_expires_at FROM payroll_runs "
                "WHERE payroll_run_id = 77"
            )
        ) is None
    engine.dispose()


def test_success_transition_is_fenced_sets_completed_at_and_clears_lease(tmp_path) -> None:
    engine = _engine_with_created_run(str(tmp_path / "processed.sqlite"))
    with Session(engine) as session:
        repository = PayrollRunRepository(session)
        assert repository.claim_for_processing(77) == 1
        session.commit()
        assert repository.mark_processed_if_processing(77, 2) is False
        assert repository.mark_processed_if_processing(77, 1) is True
        session.commit()
        assert repository.mark_processed_if_processing(77, 1) is False

    with engine.connect() as connection:
        run = connection.execute(
            text(
                "SELECT status, completed_at, attempt_lease_expires_at "
                "FROM payroll_runs WHERE payroll_run_id = 77"
            )
        ).one()
    assert run.status == "PROCESSED"
    assert run.completed_at is not None
    assert run.attempt_lease_expires_at is None
    engine.dispose()


@pytest.mark.parametrize("status", ["PROCESSING", "PROCESSED", "FAILED", "FINALIZED"])
def test_claim_rejects_every_non_created_state(tmp_path, status: str) -> None:
    engine = _engine_with_created_run(str(tmp_path / f"{status.lower()}.sqlite"), status)
    with Session(engine) as session:
        assert PayrollRunRepository(session).claim_for_processing(77) is None
        session.commit()
    with engine.connect() as connection:
        assert connection.scalar(
            text("SELECT attempt_number FROM payroll_runs WHERE payroll_run_id = 77")
        ) == 0
        assert connection.scalar(
            text("SELECT status FROM payroll_runs WHERE payroll_run_id = 77")
        ) == status
    engine.dispose()


def test_attempt_fence_requires_matching_active_attempt_and_unexpired_lease(
    tmp_path,
) -> None:
    engine = _engine_with_created_run(str(tmp_path / "attempt-fence.sqlite"))
    with Session(engine) as session:
        repository = PayrollRunRepository(session)
        assert repository.claim_for_processing(77) == 1
        session.commit()
        assert repository.lock_active_attempt(77, 1) is not None
        assert repository.lock_active_attempt(77, 2) is None
        session.rollback()

        session.execute(
            text(
                "UPDATE payroll_runs SET attempt_lease_expires_at = "
                "datetime(CURRENT_TIMESTAMP, '-1 second') WHERE payroll_run_id = 77"
            )
        )
        session.commit()
        assert repository.lock_active_attempt(77, 1) is None
        assert repository.mark_failed_if_processing(77, 1) is False
    engine.dispose()


def test_attempt_fence_rejects_non_processing_run(tmp_path) -> None:
    engine = _engine_with_created_run(str(tmp_path / "non-processing-fence.sqlite"))
    with Session(engine) as session:
        repository = PayrollRunRepository(session)
        assert repository.claim_for_processing(77) == 1
        session.commit()
        assert repository.mark_failed_if_processing(77, 1) is True
        session.commit()
        assert repository.lock_active_attempt(77, 1) is None
    engine.dispose()


def test_mysql_lease_expression_uses_database_current_timestamp() -> None:
    expression = PayrollRunRepository._lease_expiration("mysql", 900)
    compiled = str(expression.compile(dialect=mysql.dialect()))

    assert "TIMESTAMPADD(SECOND" in compiled.upper()
    assert "CURRENT_TIMESTAMP" in compiled.upper()
