from datetime import datetime
from queue import Queue
from threading import Barrier, Thread
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.application.payroll.payroll_run_retry_service import PayrollRunRetryService
from app.core.config import get_settings
from app.domain.shared.exceptions import BusinessRuleViolation
from app.infrastructure.persistence.repositories.audit_event_repository import (
    AuditEventRepository,
)
from app.infrastructure.persistence.repositories.payroll_result_component_repository import (
    PayrollResultComponentRepository,
)
from app.infrastructure.persistence.repositories.payroll_result_repository import (
    PayrollResultRepository,
)
from app.infrastructure.persistence.repositories.payroll_run_repository import (
    PayrollRunRepository,
)
from app.infrastructure.persistence.repositories.payroll_run_workforce_snapshot_repository import (
    PayrollRunWorkforceSnapshotRepository,
)
from app.infrastructure.persistence.repositories.payslip_repository import (
    PayslipRepository,
)


@pytest.fixture
def retry_uow():
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
            "CREATE TABLE payroll_results (payroll_result_id INTEGER PRIMARY KEY, "
            "payroll_run_id INTEGER NOT NULL, employee_id INTEGER NOT NULL, "
            "salary_assignment_id INTEGER NOT NULL, gross_earnings NUMERIC NOT NULL, "
            "total_deductions NUMERIC NOT NULL, net_salary NUMERIC NOT NULL, "
            "workforce_calculation_snapshot JSON NULL, "
            "processed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP)"
        )
        connection.exec_driver_sql(
            "CREATE TABLE payroll_result_components ("
            "payroll_result_component_id INTEGER PRIMARY KEY, "
            "payroll_result_id INTEGER NOT NULL, salary_component_id INTEGER NOT NULL, "
            "component_type VARCHAR(20) NOT NULL, amount NUMERIC NOT NULL, "
            "calculation_order INTEGER NOT NULL)"
        )
        connection.exec_driver_sql(
            "CREATE TABLE payroll_run_workforce_snapshots ("
            "payroll_run_id INTEGER NOT NULL, employee_id INTEGER NOT NULL, "
            "attempt_number INTEGER NOT NULL, snapshot_at DATETIME NOT NULL, "
            "snapshot JSON NOT NULL, PRIMARY KEY(payroll_run_id, employee_id))"
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
            "CREATE TABLE payroll_processing_issues (payroll_issue_id INTEGER PRIMARY KEY, "
            "payroll_run_id INTEGER NOT NULL, employee_id INTEGER NULL, "
            "issue_code VARCHAR(100) NOT NULL, issue_message VARCHAR(1000) NOT NULL, "
            "status VARCHAR(20) NOT NULL, detected_at DATETIME NOT NULL, "
            "resolved_at DATETIME NULL)"
        )

    session = Session(engine)
    session.execute(
        text(
            "INSERT INTO payroll_runs (payroll_run_id, payroll_year, payroll_month, "
            "status, initiated_by_user_id, started_at, attempt_number, "
            "attempt_lease_expires_at) VALUES "
            "(1, 2026, 10, 'FAILED', 99, '2000-01-01 00:00:00', 3, "
            "'2000-01-01 00:15:00')"
        )
    )
    session.execute(
        text(
            "INSERT INTO payroll_results (payroll_result_id, payroll_run_id, "
            "employee_id, salary_assignment_id, gross_earnings, total_deductions, "
            "net_salary) VALUES (10, 1, 20, 30, 1000, 100, 900)"
        )
    )
    session.execute(
        text(
            "INSERT INTO payroll_result_components VALUES "
            "(11, 10, 40, 'EARNING', 1000, 0)"
        )
    )
    session.execute(
        text(
            "INSERT INTO payroll_run_workforce_snapshots VALUES "
            "(1, 20, 3, '2000-01-01 00:00:00', '{}')"
        )
    )
    session.execute(
        text(
            "INSERT INTO payroll_processing_issues VALUES "
            "(12, 1, 20, 'OLD', 'Retain me', 'OPEN', CURRENT_TIMESTAMP, NULL)"
        )
    )
    session.execute(
        text(
            "INSERT INTO audit_events (audit_event_id, action_type, resource_type, "
            "resource_id, occurred_at) VALUES (13, 'OLD_EVENT', 'PAYROLL_RUN', 1, "
            "CURRENT_TIMESTAMP)"
        )
    )
    session.commit()
    payroll_runs = PayrollRunRepository(session)
    uow = SimpleNamespace(
        session=session,
        payroll_runs=payroll_runs,
        payroll_result_components=PayrollResultComponentRepository(session),
        payroll_results=PayrollResultRepository(session),
        payroll_run_workforce_snapshots=PayrollRunWorkforceSnapshotRepository(
            session, payroll_runs
        ),
        payslips=PayslipRepository(session),
        audit_events=AuditEventRepository(session),
        commit=session.commit,
        rollback=session.rollback,
    )
    try:
        yield uow
    finally:
        session.close()
        engine.dispose()


def _retry(uow, expected_attempt: int = 3):
    return PayrollRunRetryService(uow).retry_failed_payroll_run(
        1, expected_attempt, 99, "retry-test-correlation"
    )


def _execute_with_rollback_on_error(uow, expected_attempt: int = 3):
    try:
        return _retry(uow, expected_attempt)
    except Exception:
        uow.rollback()
        raise


def test_retry_reconciles_artifacts_and_audits_atomically(retry_uow) -> None:
    outcome = _retry(retry_uow)

    assert outcome.old_attempt_number == 3
    assert outcome.new_attempt_number == 4
    assert outcome.deleted_result_count == 1
    assert outcome.deleted_component_count == 1
    assert outcome.deleted_workforce_snapshot_count == 1
    run = retry_uow.session.execute(
        text("SELECT status, attempt_number, started_at, attempt_lease_expires_at "
             "FROM payroll_runs WHERE payroll_run_id=1")
    ).one()
    assert run.status == "PROCESSING" and run.attempt_number == 4
    started_at = datetime.fromisoformat(run.started_at)
    lease_expires_at = datetime.fromisoformat(run.attempt_lease_expires_at)
    assert started_at != datetime(2000, 1, 1)
    assert lease_expires_at > started_at
    lease_delta = retry_uow.session.scalar(
        text("SELECT strftime('%s', attempt_lease_expires_at) - "
             "strftime('%s', started_at) FROM payroll_runs WHERE payroll_run_id=1")
    )
    assert lease_delta == get_settings().payroll_attempt_lease_seconds
    db_clock_delta = retry_uow.session.scalar(
        text("SELECT abs(strftime('%s', started_at) - strftime('%s', 'now')) "
             "FROM payroll_runs WHERE payroll_run_id=1")
    )
    assert db_clock_delta <= 2
    assert retry_uow.session.scalar(text("SELECT COUNT(*) FROM payroll_results")) == 0
    assert retry_uow.session.scalar(
        text("SELECT COUNT(*) FROM payroll_result_components")
    ) == 0
    assert retry_uow.session.scalar(
        text("SELECT COUNT(*) FROM payroll_run_workforce_snapshots")
    ) == 0
    assert retry_uow.session.scalar(
        text("SELECT COUNT(*) FROM payroll_processing_issues")
    ) == 1
    assert retry_uow.session.scalar(
        text("SELECT COUNT(*) FROM audit_events WHERE action_type='OLD_EVENT'")
    ) == 1
    audit = retry_uow.session.execute(
        text("SELECT actor_user_id, correlation_id FROM audit_events "
             "WHERE action_type='PAYROLL_RUN_RETRY_CLAIMED'")
    ).one()
    assert audit == (99, "retry-test-correlation")
    changes = dict(
        retry_uow.session.execute(
            text("SELECT field_name, new_value FROM audit_event_changes "
                 "WHERE audit_event_id=(SELECT audit_event_id FROM audit_events "
                 "WHERE action_type='PAYROLL_RUN_RETRY_CLAIMED')")
        ).all()
    )
    assert changes == {
        "attempt_number": "4",
        "deleted_result_count": "1",
        "deleted_component_count": "1",
        "deleted_workforce_snapshot_count": "1",
        "status": "PROCESSING",
    }
    assert not {"gross", "deductions", "net", "salary", "amount"} & changes.keys()


@pytest.mark.parametrize(
    ("status", "expected", "message"),
    [
        ("FAILED", 2, "Expected Payroll Run attempt"),
        ("CREATED", 3, "cannot be retried from CREATED"),
        ("PROCESSING", 3, "cannot be retried from PROCESSING"),
        ("PROCESSED", 3, "cannot be retried from PROCESSED"),
        ("FINALIZED", 3, "cannot be retried from FINALIZED"),
    ],
)
def test_retry_rejects_wrong_attempt_or_ineligible_state(
    retry_uow, status, expected, message
) -> None:
    retry_uow.session.execute(
        text("UPDATE payroll_runs SET status=:status WHERE payroll_run_id=1"),
        {"status": status},
    )
    retry_uow.commit()
    with pytest.raises(BusinessRuleViolation, match=message):
        _execute_with_rollback_on_error(retry_uow, expected)
    assert retry_uow.session.scalar(text("SELECT COUNT(*) FROM payroll_results")) == 1
    assert retry_uow.session.scalar(text("SELECT COUNT(*) FROM audit_events")) == 1


def test_retry_with_payslip_aborts_before_deleting_anything(retry_uow) -> None:
    retry_uow.session.execute(
        text("INSERT INTO payslips VALUES (1, 10, 'SYNTHETIC', 99, "
             "CURRENT_TIMESTAMP, '/tmp/payslip')")
    )
    retry_uow.commit()
    with pytest.raises(BusinessRuleViolation, match="payslip exists"):
        _execute_with_rollback_on_error(retry_uow)
    assert retry_uow.session.scalar(text("SELECT COUNT(*) FROM payroll_results")) == 1
    assert retry_uow.session.scalar(
        text("SELECT COUNT(*) FROM payroll_result_components")
    ) == 1
    assert retry_uow.session.scalar(
        text("SELECT COUNT(*) FROM payroll_run_workforce_snapshots")
    ) == 1
    assert retry_uow.session.scalar(text("SELECT COUNT(*) FROM payslips")) == 1


def test_retry_uses_parent_first_lock_and_reconciles_in_dependency_order(retry_uow) -> None:
    calls = []
    for owner, method, label in (
        (retry_uow.payroll_runs, "lock_failed_attempt", "run_lock"),
        (retry_uow.payslips, "get_by_run_id", "payslip_check"),
        (retry_uow.payroll_result_components, "delete_by_run", "components"),
        (retry_uow.payroll_results, "delete_by_run", "results"),
        (
            retry_uow.payroll_run_workforce_snapshots,
            "delete_by_run_and_attempt",
            "snapshots",
        ),
        (retry_uow.payroll_runs, "retry_failed_attempt", "run_update"),
        (retry_uow.audit_events, "add", "audit"),
    ):
        original = getattr(owner, method)

        def recorded(*args, _original=original, _label=label, **kwargs):
            calls.append(_label)
            return _original(*args, **kwargs)

        setattr(owner, method, recorded)
    original_commit = retry_uow.commit

    def recorded_commit():
        calls.append("commit")
        original_commit()

    retry_uow.commit = recorded_commit
    _retry(retry_uow)
    assert calls == [
        "run_lock",
        "payslip_check",
        "components",
        "results",
        "snapshots",
        "run_update",
        "audit",
        "commit",
    ]


def test_concurrent_retry_claim_update_has_exactly_one_winner(tmp_path) -> None:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'retry-claim.sqlite'}", connect_args={"timeout": 10}
    )
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE payroll_runs (payroll_run_id INTEGER PRIMARY KEY, "
            "status VARCHAR(20) NOT NULL, attempt_number INTEGER NOT NULL, "
            "started_at DATETIME NULL, attempt_lease_expires_at DATETIME NULL)"
        )
        connection.exec_driver_sql(
            "INSERT INTO payroll_runs VALUES "
            "(1, 'FAILED', 3, '2000-01-01 00:00:00', '2000-01-01 00:15:00')"
        )

    barrier = Barrier(2)
    results = Queue()

    def retry_claim() -> None:
        try:
            with Session(engine) as session:
                barrier.wait(timeout=5)
                claimed = PayrollRunRepository(session).retry_failed_attempt(1, 3)
                session.commit()
                results.put(claimed)
        except BaseException as exc:
            results.put(exc)

    threads = [Thread(target=retry_claim) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=15)
    outcomes = [results.get(timeout=1), results.get(timeout=1)]
    assert all(not thread.is_alive() for thread in threads)
    assert not any(isinstance(outcome, BaseException) for outcome in outcomes)
    assert sorted(outcomes, key=lambda outcome: outcome is None) == [4, None]
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT status, attempt_number FROM payroll_runs WHERE payroll_run_id=1")
        ).one() == ("PROCESSING", 4)
    engine.dispose()


def test_retry_with_zero_artifacts_succeeds_and_second_retry_is_rejected(
    retry_uow,
) -> None:
    retry_uow.session.execute(text("DELETE FROM payroll_result_components"))
    retry_uow.session.execute(text("DELETE FROM payroll_results"))
    retry_uow.session.execute(text("DELETE FROM payroll_run_workforce_snapshots"))
    retry_uow.commit()
    outcome = _retry(retry_uow)
    assert (
        outcome.deleted_result_count,
        outcome.deleted_component_count,
        outcome.deleted_workforce_snapshot_count,
    ) == (0, 0, 0)
    with pytest.raises(BusinessRuleViolation, match="cannot be retried from PROCESSING"):
        _execute_with_rollback_on_error(retry_uow, 3)
    with pytest.raises(BusinessRuleViolation, match="cannot be retried from PROCESSING"):
        _execute_with_rollback_on_error(retry_uow, 4)


@pytest.mark.parametrize(
    "target",
    [
        "components",
        "results",
        "snapshots",
        "run_update",
        "audit",
    ],
)
def test_retry_database_failure_rolls_back_full_reconciliation(
    retry_uow, target
) -> None:
    trigger_action = "SELECT RAISE(ABORT, 'forced retry failure')"
    table, operation = {
        "components": ("payroll_result_components", "DELETE"),
        "results": ("payroll_results", "DELETE"),
        "snapshots": ("payroll_run_workforce_snapshots", "DELETE"),
        "run_update": ("payroll_runs", "UPDATE"),
        "audit": ("audit_events", "INSERT"),
    }[target]
    retry_uow.session.execute(
        text(
            f"CREATE TRIGGER fail_retry BEFORE {operation} ON {table} "
            f"BEGIN {trigger_action}; END"
        )
    )
    retry_uow.commit()
    with pytest.raises(Exception, match="forced retry failure"):
        _execute_with_rollback_on_error(retry_uow)
    run = retry_uow.session.execute(
        text("SELECT status, attempt_number, started_at, attempt_lease_expires_at "
             "FROM payroll_runs WHERE payroll_run_id=1")
    ).one()
    assert run == ("FAILED", 3, "2000-01-01 00:00:00", "2000-01-01 00:15:00")
    assert retry_uow.session.scalar(text("SELECT COUNT(*) FROM payroll_results")) == 1
    assert retry_uow.session.scalar(
        text("SELECT COUNT(*) FROM payroll_result_components")
    ) == 1
    assert retry_uow.session.scalar(
        text("SELECT COUNT(*) FROM payroll_run_workforce_snapshots")
    ) == 1
    assert retry_uow.session.scalar(text("SELECT COUNT(*) FROM audit_events")) == 1
