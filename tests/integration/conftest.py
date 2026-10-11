from __future__ import annotations

import os
from typing import Iterator

import pytest
from sqlalchemy import Engine, create_engine, text

from scripts.prepare_mysql_test_schema import prepare_schema_snapshot
from tests.integration.mysql_support import (
    MySQLTestConfigurationError,
    SchemaVerificationError,
    _SCHEMA_PATH,
    _verify_schema_state,
    mysql_test_url_from_environment,
    parse_mysql_test_url,
)

_EXPECTED_LIVE_TESTS = {
    "test_processes_and_persists_a_payroll_run",
    "test_blocking_open_issue_fails_run_without_resolving_issue",
    "test_qa_issue_and_transition_roll_back_when_audit_write_fails",
    "test_stale_or_expired_attempt_cannot_complete_qa[stale-attempt]",
    "test_stale_or_expired_attempt_cannot_complete_qa[expired-lease]",
    "test_finalizes_processed_run_atomically",
    "test_finalization_rechecks_state_and_open_issues_under_lock",
    "test_repeated_finalization_returns_conflict",
    "test_concurrent_finalization_has_one_winner",
    "test_finalization_and_audit_roll_back_together_on_audit_failure",
    "test_generates_finalized_payslip_and_audit_atomically",
    "test_payslip_generation_requires_finalized_run",
    "test_duplicate_payslip_generation_returns_conflict",
    "test_concurrent_payslip_generation_has_one_winner",
    "test_payslip_and_audit_roll_back_together_on_audit_failure",
    "test_payslip_generation_preserves_finalized_financial_data",
    "test_finalized_payroll_summary_uses_persisted_results_and_rbac",
    "test_finalized_payroll_results_report_paginates_persisted_rows_and_is_run_scoped",
    "test_employee_report_uses_seeded_hr_permission_and_filters_persisted_rows",
    "test_attendance_report_uses_hr_permission_filters_rows_and_paginates_same_date",
    "test_leave_reports_use_persisted_hr_permission_and_reject_payroll_role",
    "test_leave_allocation_report_filters_paginates_and_preserves_allocations",
    "test_leave_balance_report_filters_paginates_and_returns_persisted_values",
    "test_leave_allocation_report_rejects_invalid_cursors_and_parameters",
    "test_leave_balance_report_rejects_invalid_cursors_and_parameters",
    "test_payroll_component_report_reads_persisted_rows_filters_and_paginates",
    "test_payroll_component_report_uses_persisted_authorization_and_run_state",
    "test_payroll_component_report_sanitizes_missing_definition_error",
    "test_compensation_salary_structure_create_persists",
    "test_compensation_salary_component_create_persists",
    "test_compensation_salary_revision_create_persists",
    "test_compensation_salary_revision_component_create_persists_and_rejects_cycle",
    "test_compensation_employee_salary_assignment_create_persists",
    "test_compensation_schema_enforces_existing_unique_check_and_foreign_key_constraints",
    "test_expired_attempt_recovery_audits_and_retry_starts_next_fenced_attempt",
    "test_recovery_rejects_missing_wrong_state_and_unexpired_attempt",
    "test_concurrent_expired_attempt_recovery_has_one_winner",
    "test_recovery_and_audit_roll_back_together_on_audit_failure",
    "test_recovery_requires_persisted_permission",
}


def _strict_mode() -> bool:
    return os.environ.get("EPMS_REQUIRE_MYSQL_TESTS", "0") == "1"


def pytest_configure(config: pytest.Config) -> None:
    """The shared disposable database is deliberately serial-only."""
    if os.environ.get("PYTEST_XDIST_WORKER"):
        raise pytest.UsageError("MySQL integration tests cannot run under pytest-xdist.")
    try:
        workers = config.getoption("numprocesses", default=0)
    except ValueError:
        workers = 0
    if workers not in (None, 0, "0", "no"):
        raise pytest.UsageError("MySQL integration tests cannot run under pytest-xdist.")


def pytest_collection_finish(session: pytest.Session) -> None:
    if not _strict_mode():
        return
    collected = {item.nodeid.rsplit("::", 1)[-1] for item in session.items}
    if collected != _EXPECTED_LIVE_TESTS:
        missing = sorted(_EXPECTED_LIVE_TESTS - collected)
        unexpected = sorted(collected - _EXPECTED_LIVE_TESTS)
        raise pytest.UsageError(
            f"Strict MySQL run must collect exactly thirty-nine live tests; missing={missing}, unexpected={unexpected}."
        )


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    if not _strict_mode():
        return
    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    passed = len(reporter.stats.get("passed", [])) if reporter else 0
    skipped = len(reporter.stats.get("skipped", [])) if reporter else 0
    if exitstatus != pytest.ExitCode.OK or passed != 39 or skipped != 0:
        session.exitstatus = pytest.ExitCode.TESTS_FAILED


@pytest.fixture(scope="session")
def mysql_payroll_database() -> Iterator[tuple[Engine, str]]:
    try:
        raw_url = mysql_test_url_from_environment()
    except MySQLTestConfigurationError as exc:
        pytest.fail(str(exc), pytrace=False)
    if raw_url is None:
        pytest.skip("EPMS_MYSQL_TEST_URL is unset; real-MySQL tests are opt-in.")
    try:
        target = parse_mysql_test_url(raw_url)
    except ValueError as exc:
        pytest.fail(str(exc), pytrace=False)

    # Preparing this temporary copy performs file I/O only. It does not execute
    # schema SQL or create/modify a database.
    prepared_schema = prepare_schema_snapshot(target.database_name, schema_path=_SCHEMA_PATH)
    engine = create_engine(target.url, pool_pre_ping=True, pool_recycle=300, echo=False)
    try:
        try:
            with engine.connect() as connection:
                version, selected_database = connection.execute(
                    text("SELECT VERSION(), DATABASE()")
                ).one()
                version_major = str(version).split(".", 1)[0]
                if not version_major.isdigit() or int(version_major) != 8:
                    pytest.fail("Real-MySQL payroll tests require MySQL 8.", pytrace=False)
                if selected_database != target.database_name:
                    pytest.fail("MySQL selected a database other than the test target.", pytrace=False)
                _verify_schema_state(connection, prepared_schema)
        except SchemaVerificationError as exc:
            pytest.fail(str(exc), pytrace=False)
        except pytest.fail.Exception:
            raise
        except Exception as exc:
            pytest.fail(
                f"Could not verify the isolated MySQL test database ({type(exc).__name__}).",
                pytrace=False,
            )
        yield engine, target.database_name
    finally:
        engine.dispose()
        prepared_schema.unlink(missing_ok=True)


@pytest.fixture
def mysql_test_engine(mysql_payroll_database: tuple[Engine, str]) -> Iterator[tuple[Engine, str]]:
    yield mysql_payroll_database
