from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.application.payroll.payroll_run_finalization_service import (
    PayrollRunFinalizationService,
)
from app.domain.shared.exceptions import BusinessRuleViolation
from app.infrastructure.persistence.repositories.audit_event_repository import (
    AuditEventRepository,
)
from app.infrastructure.persistence.repositories.payroll_processing_issue_repository import (
    PayrollProcessingIssueRepository,
)
from app.infrastructure.persistence.repositories.payroll_run_repository import (
    PayrollRunRepository,
)
from app.infrastructure.persistence.repositories.payslip_repository import (
    PayslipRepository,
)


@pytest.fixture
def finalization_uow():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE payroll_runs (payroll_run_id INTEGER PRIMARY KEY, "
            "payroll_year INTEGER NOT NULL, payroll_month INTEGER NOT NULL, "
            "status VARCHAR(20) NOT NULL, initiated_by_user_id INTEGER NOT NULL, "
            "started_at DATETIME NULL, attempt_number INTEGER NOT NULL, "
            "attempt_lease_expires_at DATETIME NULL, completed_at DATETIME NULL, "
            "finalized_at DATETIME NULL, created_at DATETIME NOT NULL "
            "DEFAULT CURRENT_TIMESTAMP, updated_at DATETIME NOT NULL "
            "DEFAULT CURRENT_TIMESTAMP)"
        )
        connection.exec_driver_sql(
            "CREATE TABLE payroll_processing_issues (payroll_issue_id INTEGER PRIMARY KEY, "
            "payroll_run_id INTEGER NOT NULL, employee_id INTEGER NULL, "
            "issue_code VARCHAR(100) NOT NULL, issue_message VARCHAR(1000) NOT NULL, "
            "status VARCHAR(20) NOT NULL, detected_at DATETIME NOT NULL, "
            "resolved_at DATETIME NULL)"
        )
        connection.exec_driver_sql(
            "CREATE TABLE payroll_results (payroll_result_id INTEGER PRIMARY KEY, "
            "payroll_run_id INTEGER NOT NULL, employee_id INTEGER NOT NULL, "
            "salary_assignment_id INTEGER NOT NULL, gross_earnings NUMERIC NOT NULL, "
            "total_deductions NUMERIC NOT NULL, net_salary NUMERIC NOT NULL, "
            "workforce_calculation_snapshot JSON NULL, "
            "processed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP)"
        )
        connection.exec_driver_sql(
            "CREATE TABLE payslips (payslip_id INTEGER PRIMARY KEY, "
            "payroll_result_id INTEGER NOT NULL, payslip_number VARCHAR(50) NOT NULL, "
            "generated_by_user_id INTEGER NOT NULL, generated_at DATETIME NOT NULL, "
            "document_path VARCHAR(500) NOT NULL)"
        )
        connection.exec_driver_sql(
            "CREATE TABLE audit_events (audit_event_id INTEGER PRIMARY KEY, "
            "actor_user_id INTEGER NULL, action_type VARCHAR(100) NOT NULL, "
            "resource_type VARCHAR(100) NOT NULL, resource_id INTEGER NULL, "
            "correlation_id VARCHAR(100) NULL, source_ip VARCHAR(45) NULL, "
            "user_agent VARCHAR(500) NULL, occurred_at DATETIME NOT NULL "
            "DEFAULT CURRENT_TIMESTAMP)"
        )
        connection.exec_driver_sql(
            "CREATE TABLE audit_event_changes (audit_event_change_id INTEGER PRIMARY KEY, "
            "audit_event_id INTEGER NOT NULL, field_name VARCHAR(100) NOT NULL, "
            "old_value TEXT NULL, new_value TEXT NULL)"
        )
        connection.exec_driver_sql(
            "INSERT INTO payroll_runs (payroll_run_id, payroll_year, payroll_month, "
            "status, initiated_by_user_id, attempt_number) "
            "VALUES (1, 2026, 10, 'PROCESSED', 99, 1)"
        )
        connection.exec_driver_sql(
            "CREATE TRIGGER fail_finalization_audit BEFORE INSERT ON audit_events "
            "BEGIN SELECT RAISE(ABORT, 'forced finalization audit failure'); END"
        )
    session = Session(engine)
    uow = SimpleNamespace(
        session=session,
        payroll_runs=PayrollRunRepository(session),
        payroll_processing_issues=PayrollProcessingIssueRepository(session),
        payslips=PayslipRepository(session),
        audit_events=AuditEventRepository(session),
        commit=session.commit,
    )
    yield uow
    session.close()
    engine.dispose()


def test_audit_failure_rolls_back_finalized_state(finalization_uow) -> None:
    with pytest.raises(Exception, match="forced finalization audit failure"):
        PayrollRunFinalizationService(finalization_uow).finalize(
            1, 99, "finalization-test"
        )
        # Match SQLAlchemyUnitOfWork.__exit__: any failure rolls back all writes.
    finalization_uow.session.rollback()

    row = finalization_uow.session.execute(
        text("SELECT status, finalized_at FROM payroll_runs WHERE payroll_run_id=1")
    ).one()
    audit_count = finalization_uow.session.scalar(
        text("SELECT COUNT(*) FROM audit_events")
    )
    assert row == ("PROCESSED", None)
    assert audit_count == 0


def test_open_issue_blocks_finalization_without_transition(finalization_uow) -> None:
    finalization_uow.session.execute(
        text(
            "INSERT INTO payroll_processing_issues "
            "(payroll_issue_id, payroll_run_id, issue_code, issue_message, status, detected_at) "
            "VALUES (1, 1, 'QA_BLOCK', 'Open issue', 'OPEN', CURRENT_TIMESTAMP)"
        )
    )
    finalization_uow.session.commit()
    with pytest.raises(BusinessRuleViolation, match="OPEN issues"):
        PayrollRunFinalizationService(finalization_uow).finalize(
            1, 99, "finalization-test"
        )
    status = finalization_uow.session.scalar(
        text("SELECT status FROM payroll_runs WHERE payroll_run_id=1")
    )
    assert status == "PROCESSED"
