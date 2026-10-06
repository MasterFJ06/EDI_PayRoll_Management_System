from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.application.payroll.payroll_processing_orchestrator import (
    PayrollProcessingOrchestrator,
)
from app.infrastructure.persistence.repositories.audit_event_repository import (
    AuditEventRepository,
)
from app.infrastructure.persistence.repositories.payroll_run_repository import (
    PayrollRunRepository,
)


class SQLiteUnitOfWork:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.payroll_runs = PayrollRunRepository(session)
        self.audit_events = AuditEventRepository(session)

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()


def _create_processing_database(database_path: str):
    engine = create_engine(f"sqlite:///{database_path}")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE users (user_id INTEGER PRIMARY KEY)"
        )
        connection.exec_driver_sql("INSERT INTO users VALUES (12)")
        connection.exec_driver_sql(
            "CREATE TABLE payroll_runs ("
            "payroll_run_id INTEGER PRIMARY KEY, payroll_year INTEGER NOT NULL, "
            "payroll_month INTEGER NOT NULL, status VARCHAR(20) NOT NULL, "
            "initiated_by_user_id INTEGER NOT NULL, started_at DATETIME NULL, "
            "completed_at DATETIME NULL, finalized_at DATETIME NULL, "
            "created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, "
            "updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP)"
        )
        connection.exec_driver_sql(
            "INSERT INTO payroll_runs "
            "(payroll_run_id, payroll_year, payroll_month, status, initiated_by_user_id) "
            "VALUES (77, 2026, 10, 'CREATED', 12)"
        )
        connection.exec_driver_sql(
            "CREATE TABLE audit_events ("
            "audit_event_id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "actor_user_id INTEGER NULL, action_type VARCHAR(100) NOT NULL, "
            "resource_type VARCHAR(100) NOT NULL, resource_id INTEGER NULL, "
            "correlation_id VARCHAR(100) NULL, source_ip VARCHAR(45) NULL, "
            "user_agent VARCHAR(500) NULL, "
            "occurred_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP)"
        )
        connection.exec_driver_sql(
            "CREATE TABLE audit_event_changes ("
            "audit_event_change_id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "audit_event_id INTEGER NOT NULL, field_name VARCHAR(100) NOT NULL, "
            "old_value TEXT NULL, new_value TEXT NULL)"
        )
    return engine


def test_orchestrator_claim_commits_processing_state_and_audit_event(tmp_path) -> None:
    engine = _create_processing_database(str(tmp_path / "orchestrator.sqlite"))

    with Session(engine) as session:
        response = PayrollProcessingOrchestrator(SQLiteUnitOfWork(session)).process(
            77, 12, "test-correlation-id"
        )

    assert response is not None
    assert response.status == "PROCESSING"
    with engine.connect() as connection:
        run = connection.execute(
            text(
                "SELECT status, started_at FROM payroll_runs "
                "WHERE payroll_run_id = 77"
            )
        ).one()
        audit = connection.execute(
            text(
                "SELECT actor_user_id, action_type, resource_type, resource_id, "
                "correlation_id FROM audit_events"
            )
        ).one()
        change = connection.execute(
            text(
                "SELECT field_name, old_value, new_value FROM audit_event_changes"
            )
        ).one()
    assert run.status == "PROCESSING"
    assert run.started_at is not None
    assert audit == (
        12,
        "PAYROLL_RUN_PROCESSING_STARTED",
        "PAYROLL_RUN",
        77,
        "test-correlation-id",
    )
    assert change == ("status", "CREATED", "PROCESSING")
    engine.dispose()


def test_orchestration_failure_atomically_marks_run_failed_and_audits(tmp_path) -> None:
    engine = _create_processing_database(str(tmp_path / "orchestration-failure.sqlite"))

    def fail_after_claim(self, payroll_run_id: int) -> None:
        raise RuntimeError("orchestration failure")

    with Session(engine) as session:
        orchestrator = PayrollProcessingOrchestrator(SQLiteUnitOfWork(session))
        orchestrator._processing_pipeline_extension_point = fail_after_claim.__get__(
            orchestrator, PayrollProcessingOrchestrator
        )
        try:
            orchestrator.process(77, 12, "failure-correlation-id")
        except RuntimeError as exc:
            assert str(exc) == "orchestration failure"
        else:
            raise AssertionError("Expected the injected orchestration failure.")

    with engine.connect() as connection:
        assert connection.scalar(
            text("SELECT status FROM payroll_runs WHERE payroll_run_id = 77")
        ) == "FAILED"
        events = connection.execute(
            text("SELECT action_type FROM audit_events ORDER BY audit_event_id")
        ).scalars().all()
        changes = connection.execute(
            text(
                "SELECT old_value, new_value FROM audit_event_changes "
                "ORDER BY audit_event_change_id"
            )
        ).all()
    assert events == [
        "PAYROLL_RUN_PROCESSING_STARTED",
        "PAYROLL_RUN_PROCESSING_FAILED",
    ]
    assert changes == [("CREATED", "PROCESSING"), ("PROCESSING", "FAILED")]
    engine.dispose()
