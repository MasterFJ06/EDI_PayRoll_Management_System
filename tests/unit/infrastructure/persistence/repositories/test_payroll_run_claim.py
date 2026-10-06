from queue import Queue
from threading import Barrier, Thread

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.infrastructure.persistence.repositories.payroll_run_repository import (
    PayrollRunRepository,
)


def _engine_with_created_run(database_path: str):
    engine = create_engine(
        f"sqlite:///{database_path}", connect_args={"timeout": 10}
    )
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE payroll_runs ("
            "payroll_run_id INTEGER PRIMARY KEY, "
            "status VARCHAR(20) NOT NULL, started_at DATETIME NULL)"
        )
        connection.exec_driver_sql(
            "INSERT INTO payroll_runs (payroll_run_id, status) "
            "VALUES (77, 'CREATED')"
        )
    return engine


def test_conditional_claim_changes_one_created_run_and_sets_started_at(
    tmp_path,
) -> None:
    engine = _engine_with_created_run(str(tmp_path / "claim.sqlite"))

    with Session(engine) as session:
        repository = PayrollRunRepository(session)
        assert repository.claim_for_processing(77) is True
        session.commit()

    with engine.connect() as connection:
        run = connection.execute(
            text(
                "SELECT status, started_at FROM payroll_runs "
                "WHERE payroll_run_id = 77"
            )
        ).one()
    assert run.status == "PROCESSING"
    assert run.started_at is not None
    engine.dispose()


def test_second_claim_does_not_overwrite_started_at(tmp_path) -> None:
    engine = _engine_with_created_run(str(tmp_path / "duplicate.sqlite"))

    with Session(engine) as session:
        repository = PayrollRunRepository(session)
        assert repository.claim_for_processing(77) is True
        session.commit()

    with engine.connect() as connection:
        original_started_at = connection.scalar(
            text("SELECT started_at FROM payroll_runs WHERE payroll_run_id = 77")
        )

    with Session(engine) as session:
        assert PayrollRunRepository(session).claim_for_processing(77) is False
        session.commit()

    with engine.connect() as connection:
        run = connection.execute(
            text(
                "SELECT status, started_at FROM payroll_runs "
                "WHERE payroll_run_id = 77"
            )
        ).one()
    assert run.status == "PROCESSING"
    assert run.started_at == original_started_at
    engine.dispose()


def test_simultaneous_claims_have_exactly_one_winner(tmp_path) -> None:
    engine = _engine_with_created_run(str(tmp_path / "concurrent.sqlite"))
    barrier = Barrier(2)
    results: Queue[bool | BaseException] = Queue()

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
    assert sorted(outcomes) == [False, True]

    with engine.connect() as connection:
        assert connection.scalar(
            text("SELECT status FROM payroll_runs WHERE payroll_run_id = 77")
        ) == "PROCESSING"
        assert connection.scalar(
            text("SELECT COUNT(*) FROM payroll_runs WHERE status = 'PROCESSING'")
        ) == 1
    engine.dispose()


def test_failure_transition_is_conditional_on_processing_state(tmp_path) -> None:
    engine = _engine_with_created_run(str(tmp_path / "failed.sqlite"))
    with Session(engine) as session:
        repository = PayrollRunRepository(session)
        assert repository.mark_failed_if_processing(77) is False
        assert repository.claim_for_processing(77) is True
        session.commit()
        assert repository.mark_failed_if_processing(77) is True
        session.commit()
        assert repository.mark_failed_if_processing(77) is False

    with engine.connect() as connection:
        assert connection.scalar(
            text("SELECT status FROM payroll_runs WHERE payroll_run_id = 77")
        ) == "FAILED"
    engine.dispose()
