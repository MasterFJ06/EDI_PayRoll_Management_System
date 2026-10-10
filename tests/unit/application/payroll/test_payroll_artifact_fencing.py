from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.application.payroll.payroll_processing_issue_service import (
    PayrollProcessingIssueService,
)
from app.application.payroll.payroll_result_component_service import (
    PayrollResultComponentService,
)
from app.application.payroll.payroll_result_service import PayrollResultService
from app.application.payroll.schemas import (
    PayrollProcessingIssueCreateRequest,
    PayrollResultComponentCreateRequest,
    PayrollResultCreateRequest,
)
from app.domain.shared.exceptions import BusinessRuleViolation
from app.infrastructure.persistence.repositories.payroll_processing_issue_repository import (
    PayrollProcessingIssueRepository,
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


@pytest.fixture
def artifact_uow():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE payroll_runs ("
            "payroll_run_id INTEGER PRIMARY KEY, payroll_year INTEGER NOT NULL, "
            "payroll_month INTEGER NOT NULL, status VARCHAR(20) NOT NULL, "
            "initiated_by_user_id INTEGER NOT NULL, started_at DATETIME NULL, "
            "attempt_number INTEGER NOT NULL, attempt_lease_expires_at DATETIME NULL, "
            "completed_at DATETIME NULL, finalized_at DATETIME NULL, "
            "created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, "
            "updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP)"
        )
        connection.exec_driver_sql(
            "CREATE TABLE payroll_results ("
            "payroll_result_id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "payroll_run_id INTEGER NOT NULL, employee_id INTEGER NOT NULL, "
            "salary_assignment_id INTEGER NOT NULL, gross_earnings NUMERIC NOT NULL, "
            "total_deductions NUMERIC NOT NULL, net_salary NUMERIC NOT NULL, "
            "workforce_calculation_snapshot JSON NULL, "
            "processed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, "
            "UNIQUE (payroll_run_id, employee_id))"
        )
        connection.exec_driver_sql(
            "CREATE TABLE payroll_result_components ("
            "payroll_result_component_id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "payroll_result_id INTEGER NOT NULL, salary_component_id INTEGER NOT NULL, "
            "component_type VARCHAR(20) NOT NULL, amount NUMERIC NOT NULL, "
            "calculation_order INTEGER NOT NULL, "
            "UNIQUE (payroll_result_id, salary_component_id))"
        )
        connection.exec_driver_sql(
            "CREATE TABLE payroll_processing_issues ("
            "payroll_issue_id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "payroll_run_id INTEGER NOT NULL, employee_id INTEGER NULL, "
            "issue_code VARCHAR(100) NOT NULL, issue_message VARCHAR(1000) NOT NULL, "
            "status VARCHAR(20) NOT NULL, "
            "detected_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, "
            "resolved_at DATETIME NULL)"
        )

    session = Session(engine)
    session.execute(
        text(
            "INSERT INTO payroll_runs (payroll_run_id, payroll_year, payroll_month, "
            "status, initiated_by_user_id, attempt_number, attempt_lease_expires_at) "
            "VALUES (1, 2026, 10, 'PROCESSING', 1, 1, :lease)"
        ),
        {"lease": "2099-01-01 00:00:00"},
    )
    session.commit()
    uow = SimpleNamespace(
        session=session,
        payroll_runs=PayrollRunRepository(session),
        payroll_results=PayrollResultRepository(session),
        payroll_result_components=PayrollResultComponentRepository(session),
        payroll_processing_issues=PayrollProcessingIssueRepository(session),
        employees=SimpleNamespace(get_by_id=lambda employee_id: object()),
        employee_salary_assignments=SimpleNamespace(
            get_by_id=lambda assignment_id: object()
        ),
        salary_components=SimpleNamespace(get_by_id=lambda component_id: object()),
        commit=session.commit,
        rollback=session.rollback,
    )
    try:
        yield uow
    finally:
        session.close()
        engine.dispose()


def _result_request() -> PayrollResultCreateRequest:
    return PayrollResultCreateRequest(
        payroll_run_id=1,
        employee_id=10,
        salary_assignment_id=20,
        gross_earnings=Decimal("100.00"),
        total_deductions=Decimal("10.00"),
        net_salary=Decimal("90.00"),
    )


def _component_request(
    payroll_result_id: int, salary_component_id: int = 30
) -> PayrollResultComponentCreateRequest:
    return PayrollResultComponentCreateRequest(
        payroll_result_id=payroll_result_id,
        salary_component_id=salary_component_id,
        component_type="EARNING",
        amount=Decimal("100.00"),
        calculation_order=0,
    )


@pytest.mark.parametrize(
    ("status", "attempt_number", "lease", "expected_attempt"),
    [
        ("CREATED", 1, "2099-01-01 00:00:00", 1),
        ("PROCESSING", 2, "2099-01-01 00:00:00", 1),
        ("PROCESSING", 1, "2000-01-01 00:00:00", 1),
        ("FAILED", 1, "2099-01-01 00:00:00", 1),
        ("PROCESSED", 1, "2099-01-01 00:00:00", 1),
        ("FINALIZED", 1, "2099-01-01 00:00:00", 1),
    ],
)
def test_payroll_result_rejects_non_current_attempt(
    artifact_uow, status, attempt_number, lease, expected_attempt
) -> None:
    artifact_uow.session.execute(
        text(
            "UPDATE payroll_runs SET status=:status, attempt_number=:attempt, "
            "attempt_lease_expires_at=:lease WHERE payroll_run_id=1"
        ),
        {"status": status, "attempt": attempt_number, "lease": lease},
    )
    artifact_uow.commit()

    with pytest.raises(BusinessRuleViolation, match="attempt is no longer active"):
        PayrollResultService(artifact_uow).create(
            _result_request(), attempt_number=expected_attempt
        )
    assert artifact_uow.session.scalar(text("SELECT COUNT(*) FROM payroll_results")) == 0


def test_payroll_result_accepts_current_attempt_and_rejects_duplicate(
    artifact_uow,
) -> None:
    result = PayrollResultService(artifact_uow).create(
        _result_request(), attempt_number=1
    )
    assert result.payroll_result_id == 1
    with pytest.raises(BusinessRuleViolation, match="already exists"):
        PayrollResultService(artifact_uow).create(
            _result_request(), attempt_number=1
        )


def test_payroll_result_fences_parent_before_result_insert(artifact_uow) -> None:
    calls = []
    parent_lock = artifact_uow.payroll_runs.lock_active_attempt
    result_add = artifact_uow.payroll_results.add

    def lock_parent(payroll_run_id, attempt_number):
        calls.append("payroll_run")
        return parent_lock(payroll_run_id, attempt_number)

    def add_result(result):
        calls.append("payroll_result")
        return result_add(result)

    artifact_uow.payroll_runs.lock_active_attempt = lock_parent
    artifact_uow.payroll_results.add = add_result
    PayrollResultService(artifact_uow).create(_result_request(), attempt_number=1)
    assert calls == ["payroll_run", "payroll_result"]


@pytest.mark.parametrize(
    ("status", "attempt_number", "lease", "expected_attempt"),
    [
        ("CREATED", 1, "2099-01-01 00:00:00", 1),
        ("PROCESSING", 2, "2099-01-01 00:00:00", 1),
        ("PROCESSING", 1, "2000-01-01 00:00:00", 1),
        ("FAILED", 1, "2099-01-01 00:00:00", 1),
        ("PROCESSED", 1, "2099-01-01 00:00:00", 1),
        ("FINALIZED", 1, "2099-01-01 00:00:00", 1),
    ],
)
def test_result_component_rejects_non_current_parent_attempt(
    artifact_uow, status, attempt_number, lease, expected_attempt
) -> None:
    result = PayrollResultService(artifact_uow).create(
        _result_request(), attempt_number=1
    )
    artifact_uow.session.execute(
        text(
            "UPDATE payroll_runs SET status=:status, attempt_number=:attempt, "
            "attempt_lease_expires_at=:lease WHERE payroll_run_id=1"
        ),
        {"status": status, "attempt": attempt_number, "lease": lease},
    )
    artifact_uow.commit()

    with pytest.raises(BusinessRuleViolation, match="attempt is no longer active"):
        PayrollResultComponentService(artifact_uow).create(
            _component_request(result.payroll_result_id),
            attempt_number=expected_attempt,
        )
    assert artifact_uow.session.scalar(
        text("SELECT COUNT(*) FROM payroll_result_components")
    ) == 0


def test_result_component_uses_parent_fence_then_locks_result(artifact_uow) -> None:
    result = PayrollResultService(artifact_uow).create(
        _result_request(), attempt_number=1
    )
    calls = []
    parent_lock = artifact_uow.payroll_runs.lock_active_attempt
    result_lock = artifact_uow.payroll_results.get_by_id_for_update
    component_add = artifact_uow.payroll_result_components.add

    def lock_parent(payroll_run_id, attempt_number):
        calls.append("payroll_run")
        return parent_lock(payroll_run_id, attempt_number)

    def lock_result(payroll_result_id):
        calls.append("payroll_result")
        return result_lock(payroll_result_id)

    def add_component(component):
        calls.append("payroll_result_component")
        return component_add(component)

    artifact_uow.payroll_runs.lock_active_attempt = lock_parent
    artifact_uow.payroll_results.get_by_id_for_update = lock_result
    artifact_uow.payroll_result_components.add = add_component
    response = PayrollResultComponentService(artifact_uow).create(
        _component_request(result.payroll_result_id), attempt_number=1
    )

    assert response.payroll_result_id == result.payroll_result_id
    assert calls == ["payroll_run", "payroll_result", "payroll_result_component"]


def test_result_and_components_can_be_rolled_back_as_one_employee_transaction(
    artifact_uow,
) -> None:
    result = PayrollResultService(artifact_uow).create(
        _result_request(), attempt_number=1, commit=False
    )
    components = PayrollResultComponentService(artifact_uow)
    components.create(
        _component_request(result.payroll_result_id),
        attempt_number=1,
        commit=False,
    )

    with pytest.raises(BusinessRuleViolation, match="already recorded"):
        components.create(
            _component_request(result.payroll_result_id),
            attempt_number=1,
            commit=False,
        )
    artifact_uow.rollback()

    assert artifact_uow.session.scalar(text("SELECT COUNT(*) FROM payroll_results")) == 0
    assert artifact_uow.session.scalar(
        text("SELECT COUNT(*) FROM payroll_result_components")
    ) == 0


@pytest.mark.parametrize(
    ("status", "attempt_number", "lease", "expected_attempt"),
    [
        ("CREATED", 1, "2099-01-01 00:00:00", 1),
        ("PROCESSING", 2, "2099-01-01 00:00:00", 1),
        ("PROCESSING", 1, "2000-01-01 00:00:00", 1),
        ("FAILED", 1, "2099-01-01 00:00:00", 1),
        ("PROCESSED", 1, "2099-01-01 00:00:00", 1),
        ("FINALIZED", 1, "2099-01-01 00:00:00", 1),
    ],
)
def test_processing_issue_rejects_non_current_attempt(
    artifact_uow, status, attempt_number, lease, expected_attempt
) -> None:
    artifact_uow.session.execute(
        text(
            "UPDATE payroll_runs SET status=:status, attempt_number=:attempt, "
            "attempt_lease_expires_at=:lease WHERE payroll_run_id=1"
        ),
        {"status": status, "attempt": attempt_number, "lease": lease},
    )
    artifact_uow.commit()

    with pytest.raises(BusinessRuleViolation, match="attempt is no longer active"):
        PayrollProcessingIssueService(artifact_uow).create(
            PayrollProcessingIssueCreateRequest(
                payroll_run_id=1, issue_code="QA", issue_message="Blocked"
            ),
            attempt_number=expected_attempt,
        )
    assert artifact_uow.session.scalar(
        text("SELECT COUNT(*) FROM payroll_processing_issues")
    ) == 0


def test_processing_issue_accepts_current_attempt(artifact_uow) -> None:
    issue = PayrollProcessingIssueService(artifact_uow).create(
        PayrollProcessingIssueCreateRequest(
            payroll_run_id=1, issue_code="QA", issue_message="Blocked"
        ),
        attempt_number=1,
    )
    assert issue.payroll_issue_id == 1
