from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.application.payroll.payroll_processing_orchestrator import (
    PayrollProcessingOrchestrator,
)
from app.application.payroll.workforce_snapshot_materializer import (
    WorkforceSnapshotMaterialization,
    WorkforceSnapshotMaterializer,
)
from app.infrastructure.persistence.repositories.audit_event_repository import (
    AuditEventRepository,
)
from app.infrastructure.persistence.repositories.employee_repository import (
    EmployeeRepository,
)
from app.infrastructure.persistence.repositories.payroll_run_repository import (
    PayrollRunRepository,
)
from app.infrastructure.persistence.repositories.payroll_processing_issue_repository import (
    PayrollProcessingIssueRepository,
)
from app.infrastructure.persistence.repositories.payroll_result_repository import (
    PayrollResultRepository,
)
from app.infrastructure.persistence.repositories.payroll_result_component_repository import (
    PayrollResultComponentRepository,
)
from app.infrastructure.persistence.repositories.payroll_run_workforce_snapshot_repository import (
    PayrollRunWorkforceSnapshotRepository,
)


class SQLiteUnitOfWork:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.events = []
        self.payroll_runs = PayrollRunRepository(session)
        self.payroll_processing_issues = PayrollProcessingIssueRepository(session)
        self.payroll_results = PayrollResultRepository(session)
        self.payroll_result_components = PayrollResultComponentRepository(session)
        self.payroll_run_workforce_snapshots = PayrollRunWorkforceSnapshotRepository(
            session, self.payroll_runs
        )
        self.audit_events = AuditEventRepository(session)
        self.employees = EmployeeRepository(session)
        self.employee_salary_assignments = SimpleNamespace(
            get_applicable_for_employee=lambda employee_id, snapshot_date: [
                SimpleNamespace(
                    salary_assignment_id=employee_id,
                    employee_id=employee_id,
                    salary_revision_id=employee_id + 100,
                    effective_from=date(2000, 1, 1),
                    effective_to=None,
                )
            ],
            get_intersecting_for_employee=lambda employee_id, period_start, period_end: [
                SimpleNamespace(
                    salary_assignment_id=employee_id,
                    employee_id=employee_id,
                    salary_revision_id=employee_id + 100,
                    effective_from=date(2000, 1, 1),
                    effective_to=None,
                )
            ],
        )
        self.salary_revisions = SimpleNamespace(
            get_by_id=lambda revision_id: SimpleNamespace(
                salary_revision_id=revision_id,
                salary_structure_id=revision_id + 100,
                revision_number=1,
                effective_from=date(2000, 1, 1),
                effective_to=None,
            )
        )
        self.salary_revision_components = SimpleNamespace(
            get_by_revision=lambda revision_id: []
        )
        self.salary_components = SimpleNamespace(get_by_ids=lambda component_ids: [])

    def commit(self) -> None:
        self.events.append("commit")
        self.session.commit()

    def begin_workforce_consistent_read(self) -> datetime:
        self.events.append("begin_workforce_read")
        value = self.session.scalar(text("SELECT CURRENT_TIMESTAMP"))
        return datetime.fromisoformat(value)

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
            "attempt_number INTEGER NOT NULL DEFAULT 0, "
            "attempt_lease_expires_at DATETIME NULL, "
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
            "CREATE TABLE employees ("
            "employee_id INTEGER PRIMARY KEY, employee_code VARCHAR(30) NOT NULL, "
            "user_id INTEGER NULL, first_name VARCHAR(100) NOT NULL, "
            "last_name VARCHAR(100) NOT NULL, department_id INTEGER NOT NULL, "
            "designation_id INTEGER NOT NULL, manager_employee_id INTEGER NULL, "
            "joining_date DATE NOT NULL, employment_end_date DATE NULL, "
            "employment_status VARCHAR(20) NOT NULL, "
            "created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, "
            "updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP)"
        )
        connection.exec_driver_sql(
            "INSERT INTO employees (employee_id, employee_code, first_name, "
            "last_name, department_id, designation_id, joining_date, "
            "employment_end_date, employment_status) VALUES "
            "(1, 'EMP001', 'Excluded', 'Employee', 1, 1, '2026-11-01', NULL, 'ACTIVE'), "
            "(2, 'EMP002', 'Eligible', 'Terminated', 1, 1, '2025-01-01', "
            "'2026-10-01', 'TERMINATED'), "
            "(3, 'EMP003', 'Eligible', 'Open', 1, 1, '2026-10-15', NULL, 'INACTIVE')"
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
        connection.exec_driver_sql(
            "CREATE TABLE payroll_processing_issues ("
            "payroll_issue_id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "payroll_run_id INTEGER NOT NULL, employee_id INTEGER NULL, "
            "issue_code VARCHAR(100) NOT NULL, issue_message VARCHAR(1000) NOT NULL, "
            "status VARCHAR(20) NOT NULL, detected_at DATETIME NOT NULL "
            "DEFAULT CURRENT_TIMESTAMP, resolved_at DATETIME NULL)"
        )
        connection.exec_driver_sql(
            "CREATE TABLE payroll_results ("
            "payroll_result_id INTEGER PRIMARY KEY, payroll_run_id INTEGER NOT NULL, "
            "employee_id INTEGER NOT NULL, salary_assignment_id INTEGER NOT NULL, "
            "gross_earnings NUMERIC NOT NULL, total_deductions NUMERIC NOT NULL, "
            "net_salary NUMERIC NOT NULL, workforce_calculation_snapshot JSON NULL, "
            "processed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP)"
        )
        connection.exec_driver_sql(
            "CREATE TABLE payroll_result_components ("
            "payroll_result_component_id INTEGER PRIMARY KEY, payroll_result_id INTEGER NOT NULL, "
            "salary_component_id INTEGER NOT NULL, component_type VARCHAR(20) NOT NULL, "
            "amount NUMERIC NOT NULL, calculation_order INTEGER NOT NULL)"
        )
        connection.exec_driver_sql(
            "CREATE TABLE payroll_run_workforce_snapshots ("
            "payroll_run_id INTEGER NOT NULL, employee_id INTEGER NOT NULL, "
            "attempt_number INTEGER NOT NULL, snapshot_at DATETIME NOT NULL, "
            "snapshot JSON NOT NULL, PRIMARY KEY (payroll_run_id, employee_id))"
        )
    return engine


def test_orchestrator_claim_commits_processing_state_and_audit_event(tmp_path) -> None:
    engine = _create_processing_database(str(tmp_path / "orchestrator.sqlite"))

    with Session(engine) as session, patch.object(
        WorkforceSnapshotMaterializer,
        "collect",
        return_value=WorkforceSnapshotMaterialization((), ()),
    ):
        uow = SQLiteUnitOfWork(session)
        response = PayrollProcessingOrchestrator(uow).process(
            77, 12, "test-correlation-id"
        )

    assert response is not None
    assert response.payroll_run.status == "FAILED"
    assert response.eligibility.payroll_period_start.isoformat() == "2026-10-01"
    assert response.eligibility.payroll_period_end.isoformat() == "2026-10-31"
    assert [item.employee_id for item in response.eligibility.eligible_employees] == [
        2,
        3,
    ]
    assert response.eligibility.excluded_employee_ids == (1,)
    assert [item.employee_id for item in response.compensation_snapshot.employees] == [2, 3]
    assert len(response.blocking_issue_ids) == 2
    assert response.blocking_issue_ids[0] < response.blocking_issue_ids[1]
    assert uow.events.index("commit") < uow.events.index("begin_workforce_read")
    assert uow.events.index("begin_workforce_read") < uow.events.index("commit", 1)
    assert len(response.period_segmentation.segments) == 2
    assert [
        segment.employee_id for segment in response.period_segmentation.segments
    ] == [2, 3]
    with engine.connect() as connection:
        run = connection.execute(
            text(
                "SELECT status, started_at, attempt_number, "
                "attempt_lease_expires_at FROM payroll_runs "
                "WHERE payroll_run_id = 77"
            )
        ).one()
        audit = connection.execute(
            text(
                "SELECT actor_user_id, action_type, resource_type, resource_id, "
                "correlation_id FROM audit_events ORDER BY audit_event_id"
            )
        ).all()
        change = connection.execute(
            text(
                "SELECT field_name, old_value, new_value FROM audit_event_changes"
                " ORDER BY audit_event_change_id"
            )
        ).all()
    assert run.status == "FAILED"
    assert run.started_at is not None
    assert run.attempt_number == 1
    assert run.attempt_lease_expires_at is None
    assert response.compensation_snapshot.processing_started_at == datetime.fromisoformat(
        run.started_at
    )
    assert audit == [
        (12, "PAYROLL_RUN_PROCESSING_STARTED", "PAYROLL_RUN", 77, "test-correlation-id"),
        (12, "PAYROLL_RUN_PROCESSING_FAILED", "PAYROLL_RUN", 77, "test-correlation-id"),
    ]
    assert change == [
        ("status", "CREATED", "PROCESSING"),
        ("status", "PROCESSING", "FAILED"),
    ]
    engine.dispose()


def test_orchestration_failure_atomically_marks_run_failed_and_audits(tmp_path) -> None:
    engine = _create_processing_database(str(tmp_path / "orchestration-failure.sqlite"))

    def fail_after_claim(self, payroll_run_id: int) -> None:
        raise RuntimeError("orchestration failure")

    with Session(engine) as session, patch.object(
        WorkforceSnapshotMaterializer,
        "collect",
        return_value=WorkforceSnapshotMaterialization((), ()),
    ):
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
        assert connection.scalar(
            text("SELECT attempt_number FROM payroll_runs WHERE payroll_run_id = 77")
        ) == 1
        assert connection.scalar(
            text(
                "SELECT attempt_lease_expires_at FROM payroll_runs "
                "WHERE payroll_run_id = 77"
            )
        ) is None
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


def test_qa_issue_and_transition_roll_back_when_completion_audit_fails(tmp_path) -> None:
    engine = _create_processing_database(str(tmp_path / "qa-audit-failure.sqlite"))
    with Session(engine) as session, patch.object(
        WorkforceSnapshotMaterializer,
        "collect",
        return_value=WorkforceSnapshotMaterialization((), ()),
    ):
        uow = SQLiteUnitOfWork(session)
        original_add = uow.audit_events.add
        fail_once = {"pending": True}

        def fail_qa_failure_audit(event, changes=()):
            if (
                event.action_type == "PAYROLL_RUN_PROCESSING_FAILED"
                and fail_once["pending"]
            ):
                fail_once["pending"] = False
                raise RuntimeError("injected QA audit failure")
            return original_add(event, changes)

        uow.audit_events.add = fail_qa_failure_audit
        with patch.object(
            PayrollProcessingOrchestrator,
            "_calculate_employee_results",
            return_value=(),
        ):
            try:
                PayrollProcessingOrchestrator(uow).process(
                    77, 12, "qa-audit-failure"
                )
            except RuntimeError as exc:
                assert str(exc) == "injected QA audit failure"
            else:
                raise AssertionError("Expected the injected QA audit failure.")

    with engine.connect() as connection:
        assert connection.scalar(
            text("SELECT status FROM payroll_runs WHERE payroll_run_id = 77")
        ) == "FAILED"
        assert connection.scalar(
            text("SELECT COUNT(*) FROM payroll_processing_issues")
        ) == 0
        events = connection.execute(
            text("SELECT action_type FROM audit_events ORDER BY audit_event_id")
        ).scalars().all()
    assert events == [
        "PAYROLL_RUN_PROCESSING_STARTED",
        "PAYROLL_RUN_PROCESSING_FAILED",
    ]
    engine.dispose()
