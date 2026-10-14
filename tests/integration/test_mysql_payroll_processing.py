"""Opt-in payroll integration coverage against an isolated MySQL 8 snapshot.

Set EPMS_MYSQL_TEST_URL to run these tests. The target must be an empty,
snapshot-initialized database named epms_*test* on a local MySQL service.
Run the suite serially; concurrent pytest processes against one target are
unsupported because each test starts from an empty-database check.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

@dataclass
class SeededPayroll:
    user_id: int
    username: str
    password: str
    employee_id: int
    department_id: int
    designation_id: int
    role_id: int
    created_role: bool
    created_role_permission_ids: tuple[int, ...]
    hr_role_id: int
    created_hr_role: bool
    created_hr_role_permission: bool
    hr_permission_id: int
    created_hr_permission: bool
    attendance_report_permission_id: int
    created_hr_attendance_role_permission: bool
    permission_id: int
    recover_permission_id: int
    finalize_permission_id: int
    payslip_permission_id: int
    report_permission_id: int
    created_permission_ids: tuple[int, ...]
    salary_structure_id: int
    salary_component_id: int
    salary_revision_id: int
    salary_assignment_id: int
    calendar_version_id: int
    policy_version_id: int
    payroll_run_id: int
    correlation_id: str
    extra_employee_ids: tuple[int, ...] = ()
    extra_salary_structure_ids: tuple[int, ...] = ()
    extra_salary_revision_ids: tuple[int, ...] = ()
    extra_salary_assignment_ids: tuple[int, ...] = ()
    extra_salary_component_ids: tuple[int, ...] = ()
    extra_payroll_run_ids: tuple[int, ...] = ()
    extra_users: tuple[tuple[int, str], ...] = ()


@pytest.fixture
def real_mysql_payroll(mysql_test_engine, monkeypatch: pytest.MonkeyPatch):
    engine, _database_name = mysql_test_engine
    from app.core.config import Settings
    from app.infrastructure.database.session import SessionLocal
    from app.infrastructure.security import jwt

    previous_bind = SessionLocal.kw["bind"]
    SessionLocal.configure(bind=engine)
    monkeypatch.setattr(
        jwt,
        "settings",
        Settings.model_construct(
            database_host="127.0.0.1",
            database_port=3306,
            database_name="epms_r6_test",
            database_user="epms_r6_test",
            database_password="test-only-unused",
            jwt_secret_key=uuid4().hex,
            jwt_algorithm="HS256",
            access_token_expire_minutes=15,
            refresh_token_expire_days=7,
            payroll_worker_count=1,
            payroll_attempt_lease_seconds=900,
        ),
    )
    try:
        seed = _seed_valid_payroll(engine)
        try:
            yield engine, seed
        finally:
            _cleanup_seed(engine, seed)
    finally:
        SessionLocal.configure(bind=previous_bind)


def test_processes_and_persists_a_payroll_run(real_mysql_payroll) -> None:
    engine, seed = real_mysql_payroll
    from app.infrastructure.security.jwt import create_access_token
    from app.main import app

    token = create_access_token(seed.user_id, seed.username)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            f"/api/v1/payroll/runs/{seed.payroll_run_id}/process",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "PROCESSED"
    with Session(engine) as session:
        from app.infrastructure.persistence.models.audit_event import AuditEventModel
        from app.infrastructure.persistence.models.payroll_processing_issue import PayrollProcessingIssueModel
        from app.infrastructure.persistence.models.payroll_result import PayrollResultModel
        from app.infrastructure.persistence.models.payroll_result_component import PayrollResultComponentModel
        from app.infrastructure.persistence.models.payroll_run import PayrollRunModel
        from app.infrastructure.persistence.models.payroll_run_workforce_snapshot import PayrollRunWorkforceSnapshotModel

        run = session.get(PayrollRunModel, seed.payroll_run_id)
        results = session.scalars(
            select(PayrollResultModel).where(PayrollResultModel.payroll_run_id == seed.payroll_run_id)
        ).all()
        components = session.scalars(
            select(PayrollResultComponentModel).where(
                PayrollResultComponentModel.payroll_result_id == results[0].payroll_result_id
            )
        ).all()
        snapshot = session.get(
            PayrollRunWorkforceSnapshotModel,
            (seed.payroll_run_id, seed.employee_id),
        )
        events = session.scalars(
            select(AuditEventModel).where(
                AuditEventModel.resource_type == "PAYROLL_RUN",
                AuditEventModel.resource_id == seed.payroll_run_id,
            )
        ).all()
        open_issues = session.scalar(
            select(func.count()).select_from(PayrollProcessingIssueModel).where(
                PayrollProcessingIssueModel.payroll_run_id == seed.payroll_run_id,
                PayrollProcessingIssueModel.status == "OPEN",
            )
        )

        assert run is not None and run.status == "PROCESSED"
        assert run.completed_at is not None
        assert run.attempt_number == 1
        assert len(results) == 1
        assert results[0].gross_earnings > 0
        assert results[0].net_salary == results[0].gross_earnings - results[0].total_deductions
        assert len(components) == 1
        assert components[0].amount == results[0].gross_earnings
        assert snapshot is not None
        assert snapshot.attempt_number == run.attempt_number
        assert snapshot.snapshot.get("monthly_working_day_count", 0) > 0
        assert {event.action_type for event in events} == {
            "PAYROLL_RUN_PROCESSING_STARTED",
            "PAYROLL_RUN_PROCESSING_COMPLETED",
        }
        assert open_issues == 0


def test_blocking_open_issue_fails_run_without_resolving_issue(real_mysql_payroll) -> None:
    engine, seed = real_mysql_payroll
    from app.infrastructure.persistence.models.payroll_processing_issue import PayrollProcessingIssueModel
    from app.infrastructure.security.jwt import create_access_token
    from app.main import app

    with Session(engine) as session:
        issue = PayrollProcessingIssueModel(
            payroll_run_id=seed.payroll_run_id,
            employee_id=None,
            issue_code="R6_TEST_RUN_BLOCKER",
            issue_message="Controlled integration-test blocking issue.",
            status="OPEN",
        )
        session.add(issue)
        session.commit()
        issue_id = issue.payroll_issue_id

    token = create_access_token(seed.user_id, seed.username)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            f"/api/v1/payroll/runs/{seed.payroll_run_id}/process",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "FAILED"
    with Session(engine) as session:
        from app.infrastructure.persistence.models.payroll_result import PayrollResultModel
        from app.infrastructure.persistence.models.payroll_run import PayrollRunModel

        run = session.get(PayrollRunModel, seed.payroll_run_id)
        issue = session.get(PayrollProcessingIssueModel, issue_id)
        result_count = session.scalar(
            select(func.count()).select_from(PayrollResultModel).where(
                PayrollResultModel.payroll_run_id == seed.payroll_run_id
            )
        )
        assert run is not None and run.status == "FAILED"
        assert issue is not None and issue.status == "OPEN"
        assert result_count == 1


def test_qa_issue_and_transition_roll_back_when_audit_write_fails(
    real_mysql_payroll, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine, seed = real_mysql_payroll
    from app.application.payroll.employee_eligibility_resolver import (
        EligibleEmployee,
        EmployeeEligibilityResult,
    )
    from app.application.payroll.payroll_quality_assurance_service import PayrollQualityAssuranceService
    from app.domain.shared.exceptions import BusinessRuleViolation
    from app.infrastructure.database.unit_of_work import SQLAlchemyUnitOfWork
    from app.infrastructure.persistence.models.audit_event import AuditEventModel
    from app.infrastructure.persistence.models.payroll_processing_issue import PayrollProcessingIssueModel
    from app.infrastructure.persistence.models.payroll_run import PayrollRunModel
    from app.infrastructure.persistence.repositories.audit_event_repository import AuditEventRepository

    with Session(engine) as session:
        run = session.get(PayrollRunModel, seed.payroll_run_id)
        assert run is not None
        run.status = "PROCESSING"
        run.attempt_number = 1
        run.attempt_lease_expires_at = datetime.utcnow() + timedelta(minutes=5)
        session.commit()

    original_add = AuditEventRepository.add

    def fail_terminal_audit(repository, event, changes=()):
        if event.action_type == "PAYROLL_RUN_PROCESSING_FAILED":
            raise RuntimeError("R6 controlled audit persistence fault")
        return original_add(repository, event, changes)

    monkeypatch.setattr(AuditEventRepository, "add", fail_terminal_audit)
    eligibility = EmployeeEligibilityResult(
        payroll_period_start=date.today().replace(day=1),
        payroll_period_end=date.today(),
        eligible_employees=(
            EligibleEmployee(seed.employee_id, date.today().replace(day=1), date.today()),
        ),
        excluded_employee_ids=(),
    )
    with pytest.raises(RuntimeError, match="controlled audit persistence fault"):
        with SQLAlchemyUnitOfWork() as uow:
            PayrollQualityAssuranceService(uow).evaluate_and_transition(
                seed.payroll_run_id,
                1,
                seed.user_id,
                seed.correlation_id,
                eligibility,
                {seed.employee_id: seed.salary_assignment_id},
            )

    with Session(engine) as fresh_session:
        run = fresh_session.get(PayrollRunModel, seed.payroll_run_id)
        qa_issues = fresh_session.scalars(
            select(PayrollProcessingIssueModel).where(
                PayrollProcessingIssueModel.payroll_run_id == seed.payroll_run_id,
                PayrollProcessingIssueModel.issue_code == "PAYROLL_QA_RESULT_MISSING",
            )
        ).all()
        terminal_audits = fresh_session.scalars(
            select(AuditEventModel).where(
                AuditEventModel.resource_id == seed.payroll_run_id,
                AuditEventModel.action_type == "PAYROLL_RUN_PROCESSING_FAILED",
            )
        ).all()
        assert run is not None and run.status == "PROCESSING"
        assert qa_issues == []
        assert terminal_audits == []


@pytest.mark.parametrize(
    ("qa_attempt_number", "current_attempt_number", "lease_expired"),
    [
        pytest.param(1, 2, False, id="stale-attempt"),
        pytest.param(2, 2, True, id="expired-lease"),
    ],
)
def test_stale_or_expired_attempt_cannot_complete_qa(
    real_mysql_payroll,
    qa_attempt_number: int,
    current_attempt_number: int,
    lease_expired: bool,
) -> None:
    engine, seed = real_mysql_payroll
    from app.application.payroll.employee_eligibility_resolver import EmployeeEligibilityResult
    from app.application.payroll.payroll_quality_assurance_service import PayrollQualityAssuranceService
    from app.domain.shared.exceptions import BusinessRuleViolation
    from app.infrastructure.database.unit_of_work import SQLAlchemyUnitOfWork
    from app.infrastructure.persistence.models.payroll_run import PayrollRunModel

    with Session(engine) as session:
        run = session.get(PayrollRunModel, seed.payroll_run_id)
        assert run is not None
        run.status = "PROCESSING"
        run.attempt_number = current_attempt_number
        run.attempt_lease_expires_at = (
            datetime(2000, 1, 1)
            if lease_expired
            else datetime.utcnow() + timedelta(minutes=5)
        )
        session.commit()

    with pytest.raises(BusinessRuleViolation, match="no longer active"):
        with SQLAlchemyUnitOfWork() as uow:
            PayrollQualityAssuranceService(uow).evaluate_and_transition(
                seed.payroll_run_id,
                qa_attempt_number,
                seed.user_id,
                seed.correlation_id,
                EmployeeEligibilityResult(
                    date.today().replace(day=1), date.today(), (), ()
                ),
                {},
            )

    with Session(engine) as fresh_session:
        run = fresh_session.get(PayrollRunModel, seed.payroll_run_id)
        assert run is not None
        assert run.status == "PROCESSING"
        assert run.attempt_number == current_attempt_number
        if lease_expired:
            assert run.attempt_lease_expires_at == datetime(2000, 1, 1)
        else:
            assert run.attempt_lease_expires_at is not None
            assert run.attempt_lease_expires_at > datetime.utcnow()


def _process_for_finalization(seed: SeededPayroll) -> None:
    from app.infrastructure.security.jwt import create_access_token
    from app.main import app

    token = create_access_token(seed.user_id, seed.username)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            f"/api/v1/payroll/runs/{seed.payroll_run_id}/process",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "PROCESSED"


def _finalize_request(seed: SeededPayroll):
    from app.infrastructure.security.jwt import create_access_token
    from app.main import app

    token = create_access_token(seed.user_id, seed.username)
    with TestClient(app, raise_server_exceptions=False) as client:
        return client.post(
            f"/api/v1/payroll/runs/{seed.payroll_run_id}/finalize",
            headers={"Authorization": f"Bearer {token}"},
        )


def test_finalizes_processed_run_atomically(real_mysql_payroll) -> None:
    engine, seed = real_mysql_payroll
    from app.infrastructure.persistence.models.audit_event import AuditEventModel
    from app.infrastructure.persistence.models.payroll_result import PayrollResultModel
    from app.infrastructure.persistence.models.payroll_run import PayrollRunModel
    from app.infrastructure.persistence.models.payroll_run_workforce_snapshot import PayrollRunWorkforceSnapshotModel

    _process_for_finalization(seed)
    with Session(engine) as session:
        before_result = session.scalar(
            select(PayrollResultModel).where(PayrollResultModel.payroll_run_id == seed.payroll_run_id)
        )
        before_snapshot = session.get(PayrollRunWorkforceSnapshotModel, (seed.payroll_run_id, seed.employee_id))
        assert before_result is not None and before_snapshot is not None
        result_id = before_result.payroll_result_id
        result_snapshot = before_result.workforce_calculation_snapshot
        frozen_workforce = before_snapshot.snapshot

    response = _finalize_request(seed)
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "FINALIZED"
    with Session(engine) as session:
        run = session.get(PayrollRunModel, seed.payroll_run_id)
        result = session.get(PayrollResultModel, result_id)
        snapshot = session.get(PayrollRunWorkforceSnapshotModel, (seed.payroll_run_id, seed.employee_id))
        audit = session.scalar(
            select(AuditEventModel).where(
                AuditEventModel.action_type == "PAYROLL_RUN_FINALIZED",
                AuditEventModel.resource_id == seed.payroll_run_id,
            )
        )
        assert run is not None and run.status == "FINALIZED" and run.finalized_at is not None
        assert result is not None and result.workforce_calculation_snapshot == result_snapshot
        assert snapshot is not None and snapshot.snapshot == frozen_workforce
        assert audit is not None
        assert audit.actor_user_id == seed.user_id
        assert audit.correlation_id is not None


def test_finalization_rechecks_state_and_open_issues_under_lock(real_mysql_payroll) -> None:
    engine, seed = real_mysql_payroll
    from app.infrastructure.security.jwt import create_access_token
    from app.main import app
    from app.infrastructure.persistence.models.audit_event import AuditEventModel
    from app.infrastructure.persistence.models.payroll_processing_issue import PayrollProcessingIssueModel
    from app.infrastructure.persistence.models.payroll_run import PayrollRunModel

    token = create_access_token(seed.user_id, seed.username)
    with TestClient(app, raise_server_exceptions=False) as client:
        created_response = client.post(
            f"/api/v1/payroll/runs/{seed.payroll_run_id}/finalize",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert created_response.status_code == 409

    with Session(engine) as session:
        run = session.get(PayrollRunModel, seed.payroll_run_id)
        assert run is not None
        run.status = "PROCESSED"
        issue = PayrollProcessingIssueModel(
            payroll_run_id=seed.payroll_run_id,
            employee_id=seed.employee_id,
            issue_code="R7_FINALIZATION_BLOCKER",
            issue_message="Controlled finalization prerequisite test.",
            status="OPEN",
        )
        session.add(issue)
        session.commit()
    with TestClient(app, raise_server_exceptions=False) as client:
        open_issue_response = client.post(
            f"/api/v1/payroll/runs/{seed.payroll_run_id}/finalize",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert open_issue_response.status_code == 409
    with Session(engine) as session:
        run = session.get(PayrollRunModel, seed.payroll_run_id)
        finalization_audit = session.scalar(
            select(AuditEventModel).where(
                AuditEventModel.action_type == "PAYROLL_RUN_FINALIZED",
                AuditEventModel.resource_id == seed.payroll_run_id,
            )
        )
        assert run is not None and run.status == "PROCESSED"
        assert finalization_audit is None


def test_repeated_finalization_returns_conflict(real_mysql_payroll) -> None:
    _process_for_finalization(real_mysql_payroll[1])
    first = _finalize_request(real_mysql_payroll[1])
    second = _finalize_request(real_mysql_payroll[1])
    assert first.status_code == 200, first.text
    assert second.status_code == 409


def test_concurrent_finalization_has_one_winner(real_mysql_payroll) -> None:
    seed = real_mysql_payroll[1]
    _process_for_finalization(seed)
    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(lambda _index: _finalize_request(seed), range(2)))
    assert sorted(response.status_code for response in responses) == [200, 409]


def test_finalization_and_audit_roll_back_together_on_audit_failure(
    real_mysql_payroll, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine, seed = real_mysql_payroll
    from app.infrastructure.persistence.models.audit_event import AuditEventModel
    from app.infrastructure.persistence.models.payroll_run import PayrollRunModel
    from app.infrastructure.persistence.repositories.audit_event_repository import AuditEventRepository

    _process_for_finalization(seed)
    original_add = AuditEventRepository.add

    def fail_finalization_audit(repository, event, changes=()):
        if event.action_type == "PAYROLL_RUN_FINALIZED":
            raise RuntimeError("R7 controlled finalization audit fault")
        return original_add(repository, event, changes)

    monkeypatch.setattr(AuditEventRepository, "add", fail_finalization_audit)
    response = _finalize_request(seed)
    assert response.status_code == 500
    with Session(engine) as session:
        run = session.get(PayrollRunModel, seed.payroll_run_id)
        audit = session.scalar(
            select(AuditEventModel).where(
                AuditEventModel.action_type == "PAYROLL_RUN_FINALIZED",
                AuditEventModel.resource_id == seed.payroll_run_id,
            )
        )
        assert run is not None and run.status == "PROCESSED" and run.finalized_at is None
        assert audit is None


def _finalize_seed_run(seed: SeededPayroll) -> None:
    _process_for_finalization(seed)
    response = _finalize_request(seed)
    assert response.status_code == 200, response.text


def _generate_payslip(engine, seed: SeededPayroll):
    from app.infrastructure.security.jwt import create_access_token
    from app.main import app

    token = create_access_token(seed.user_id, seed.username)
    with TestClient(app, raise_server_exceptions=False) as client:
        return client.post(
            f"/api/v1/payroll/runs/{seed.payroll_run_id}/results/{_result_id(engine, seed)}/payslip",
            json={"payslip_number": f"PS-{seed.correlation_id}"},
            headers={"Authorization": f"Bearer {token}"},
        )


def _result_id(engine, seed: SeededPayroll) -> int:
    from app.infrastructure.persistence.models.payroll_result import PayrollResultModel

    with Session(engine) as session:
        result_id = session.scalar(
            select(PayrollResultModel.payroll_result_id).where(
                PayrollResultModel.payroll_run_id == seed.payroll_run_id
            )
        )
    assert result_id is not None
    return result_id


def test_generates_finalized_payslip_and_audit_atomically(real_mysql_payroll) -> None:
    engine, seed = real_mysql_payroll
    _finalize_seed_run(seed)
    response = _generate_payslip(engine, seed)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["payroll_result_id"] == _result_id(engine, seed)
    assert body["generated_by_user_id"] == seed.user_id
    assert body["generated_at"]
    assert body["document_path"] is None
    from app.infrastructure.persistence.models.audit_event import AuditEventModel
    from app.infrastructure.persistence.models.payslip import PayslipModel
    with Session(engine) as session:
        payslip = session.get(PayslipModel, body["payslip_id"])
        audit = session.scalar(select(AuditEventModel).where(
            AuditEventModel.action_type == "PAYSLIP_GENERATED",
            AuditEventModel.resource_id == body["payslip_id"],
        ))
        assert payslip is not None and payslip.document_path is None
        assert audit is not None and audit.actor_user_id == seed.user_id
        assert audit.correlation_id == response.headers["X-Request-ID"]


def test_payslip_generation_requires_finalized_run(real_mysql_payroll) -> None:
    engine, seed = real_mysql_payroll
    _process_for_finalization(seed)
    response = _generate_payslip(engine, seed)
    assert response.status_code == 409
    from app.infrastructure.persistence.models.payslip import PayslipModel
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(PayslipModel)) == 0


def test_duplicate_payslip_generation_returns_conflict(real_mysql_payroll) -> None:
    _engine, seed = real_mysql_payroll
    _finalize_seed_run(seed)
    assert _generate_payslip(_engine, seed).status_code == 201
    assert _generate_payslip(_engine, seed).status_code == 409


def test_concurrent_payslip_generation_has_one_winner(real_mysql_payroll) -> None:
    _engine, seed = real_mysql_payroll
    _finalize_seed_run(seed)
    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(lambda _index: _generate_payslip(_engine, seed), range(2)))
    assert sorted(response.status_code for response in responses) == [201, 409]


def test_payslip_and_audit_roll_back_together_on_audit_failure(
    real_mysql_payroll, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine, seed = real_mysql_payroll
    _finalize_seed_run(seed)
    from app.infrastructure.persistence.models.audit_event import AuditEventModel
    from app.infrastructure.persistence.models.payslip import PayslipModel
    from app.infrastructure.persistence.repositories.audit_event_repository import AuditEventRepository

    original_add = AuditEventRepository.add

    def fail_payslip_audit(repository, event, changes=()):
        if event.action_type == "PAYSLIP_GENERATED":
            raise RuntimeError("R8 controlled payslip audit fault")
        return original_add(repository, event, changes)

    monkeypatch.setattr(AuditEventRepository, "add", fail_payslip_audit)
    response = _generate_payslip(engine, seed)
    assert response.status_code == 500
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(PayslipModel)) == 0
        assert session.scalar(select(func.count()).select_from(AuditEventModel).where(
            AuditEventModel.action_type == "PAYSLIP_GENERATED"
        )) == 0


def test_payslip_generation_preserves_finalized_financial_data(real_mysql_payroll) -> None:
    engine, seed = real_mysql_payroll
    _finalize_seed_run(seed)
    from app.infrastructure.persistence.models.payroll_result import PayrollResultModel
    from app.infrastructure.persistence.models.payroll_result_component import PayrollResultComponentModel
    from app.infrastructure.persistence.models.payroll_run import PayrollRunModel
    from app.infrastructure.persistence.models.payroll_run_workforce_snapshot import PayrollRunWorkforceSnapshotModel
    with Session(engine) as session:
        result = session.scalar(select(PayrollResultModel).where(PayrollResultModel.payroll_run_id == seed.payroll_run_id))
        assert result is not None
        result_values = (result.gross_earnings, result.total_deductions, result.net_salary, result.workforce_calculation_snapshot)
        components = list(session.scalars(select(PayrollResultComponentModel).where(PayrollResultComponentModel.payroll_result_id == result.payroll_result_id)))
        component_values = [(row.salary_component_id, row.component_type, row.amount, row.calculation_order) for row in components]
        snapshot = session.get(PayrollRunWorkforceSnapshotModel, (seed.payroll_run_id, seed.employee_id))
        snapshot_value = snapshot.snapshot
    assert _generate_payslip(engine, seed).status_code == 201
    with Session(engine) as session:
        result = session.get(PayrollResultModel, result.payroll_result_id)
        components = list(session.scalars(select(PayrollResultComponentModel).where(PayrollResultComponentModel.payroll_result_id == result.payroll_result_id)))
        snapshot = session.get(PayrollRunWorkforceSnapshotModel, (seed.payroll_run_id, seed.employee_id))
        run = session.get(PayrollRunModel, seed.payroll_run_id)
        assert (result.gross_earnings, result.total_deductions, result.net_salary, result.workforce_calculation_snapshot) == result_values
        assert [(row.salary_component_id, row.component_type, row.amount, row.calculation_order) for row in components] == component_values
        assert snapshot.snapshot == snapshot_value
        assert run.status == "FINALIZED"


def test_finalized_payroll_summary_uses_persisted_results_and_rbac(real_mysql_payroll) -> None:
    engine, seed = real_mysql_payroll
    from app.infrastructure.persistence.models.payroll_result import PayrollResultModel
    from app.infrastructure.security.jwt import create_access_token
    from app.main import app

    token = create_access_token(seed.user_id, seed.username)
    with TestClient(app, raise_server_exceptions=False) as client:
        non_finalized = client.get(
            f"/api/v1/reports/payroll/runs/{seed.payroll_run_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert non_finalized.status_code == 409, non_finalized.text

    _finalize_seed_run(seed)
    with Session(engine) as session:
        expected = session.execute(
            select(
                func.count(PayrollResultModel.payroll_result_id),
                func.sum(PayrollResultModel.gross_earnings),
                func.sum(PayrollResultModel.total_deductions),
                func.sum(PayrollResultModel.net_salary),
            ).where(PayrollResultModel.payroll_run_id == seed.payroll_run_id)
        ).one()

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(
            f"/api/v1/reports/payroll/runs/{seed.payroll_run_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload == {
        "payroll_run_id": seed.payroll_run_id,
        "payroll_year": date.today().year,
        "payroll_month": date.today().month,
        "status": "FINALIZED",
        "initiated_by_user_id": seed.user_id,
        "employee_result_count": expected[0],
        "total_gross_pay": str(expected[1]),
        "total_deductions": str(expected[2]),
        "total_net_pay": str(expected[3]),
    }
    sensitive_fields = {
        "employee_id",
        "employee_name",
        "components",
        "workforce_calculation_snapshot",
    }
    assert not sensitive_fields & payload.keys()


def test_finalized_payroll_results_report_paginates_persisted_rows_and_is_run_scoped(
    real_mysql_payroll,
) -> None:
    engine, seed = real_mysql_payroll
    _add_report_employee(engine, seed)
    unprivileged_user_id, unprivileged_username = _add_report_unprivileged_user(
        engine, seed
    )
    from app.infrastructure.persistence.models.employee import Employee
    from app.infrastructure.persistence.models.payroll_result import PayrollResultModel
    from app.infrastructure.security.jwt import create_access_token
    from app.main import app

    token = create_access_token(seed.user_id, seed.username)
    with TestClient(app, raise_server_exceptions=False) as client:
        non_finalized = client.get(
            f"/api/v1/reports/payroll/runs/{seed.payroll_run_id}/results",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert non_finalized.status_code == 409, non_finalized.text
        unprivileged_token = create_access_token(
            unprivileged_user_id, unprivileged_username
        )
        forbidden = client.get(
            f"/api/v1/reports/payroll/runs/{seed.payroll_run_id}/results",
            headers={"Authorization": f"Bearer {unprivileged_token}"},
        )
        assert forbidden.status_code == 403, forbidden.text

    _finalize_seed_run(seed)
    other_run_id = _add_other_run_result(engine, seed)
    from app.application.reporting.payroll_results_report_service import (
        encode_payroll_results_cursor,
    )

    with Session(engine) as session:
        expected_rows = session.execute(
            select(
                PayrollResultModel.payroll_result_id,
                PayrollResultModel.payroll_run_id,
                PayrollResultModel.employee_id,
                PayrollResultModel.salary_assignment_id,
                PayrollResultModel.gross_earnings,
                PayrollResultModel.total_deductions,
                PayrollResultModel.net_salary,
                Employee.employee_code,
                Employee.first_name,
                Employee.last_name,
            )
            .outerjoin(Employee, Employee.employee_id == PayrollResultModel.employee_id)
            .where(PayrollResultModel.payroll_run_id == seed.payroll_run_id)
            .order_by(PayrollResultModel.employee_id, PayrollResultModel.payroll_result_id)
        ).all()
    headers = {"Authorization": f"Bearer {token}"}
    with TestClient(app, raise_server_exceptions=False) as client:
        first = client.get(
            f"/api/v1/reports/payroll/runs/{seed.payroll_run_id}/results?limit=1",
            headers=headers,
        )
        assert first.status_code == 200, first.text
        first_page = first.json()
        assert len(first_page["results"]) == 1
        assert first_page["pagination"]["has_more"] is True
        cursor = first_page["pagination"]["next_cursor"]

        second = client.get(
            f"/api/v1/reports/payroll/runs/{seed.payroll_run_id}/results",
            params={"limit": 1, "cursor": cursor},
            headers=headers,
        )
        assert second.status_code == 200, second.text
        second_page = second.json()
        assert len(second_page["results"]) == 1
        assert second_page["pagination"]["has_more"] is False
        assert second_page["pagination"]["next_cursor"] is None

        malformed = client.get(
            f"/api/v1/reports/payroll/runs/{seed.payroll_run_id}/results",
            params={"cursor": "not-a-cursor"},
            headers=headers,
        )
        assert malformed.status_code == 422
        cross_run = client.get(
            f"/api/v1/reports/payroll/runs/{seed.payroll_run_id}/results",
            params={
                "cursor": encode_payroll_results_cursor(other_run_id, seed.employee_id, 1)
            },
            headers=headers,
        )
        assert cross_run.status_code == 422
        other_run_page = client.get(
            f"/api/v1/reports/payroll/runs/{other_run_id}/results",
            headers=headers,
        )
        assert other_run_page.status_code == 200, other_run_page.text

    report_rows = first_page["results"] + second_page["results"]
    assert [row["employee_id"] for row in report_rows] == [
        row.employee_id for row in expected_rows
    ]
    assert len({row["payroll_result_id"] for row in report_rows}) == 2
    assert all(row["payroll_run_id"] == seed.payroll_run_id for row in report_rows)
    assert other_run_page.json()["payroll_run_id"] == other_run_id
    assert [row["payroll_run_id"] for row in other_run_page.json()["results"]] == [
        other_run_id
    ]
    for actual, expected in zip(report_rows, expected_rows, strict=True):
        assert actual == {
            "payroll_result_id": expected.payroll_result_id,
            "payroll_run_id": expected.payroll_run_id,
            "employee_id": expected.employee_id,
            "salary_assignment_id": expected.salary_assignment_id,
            "gross_earnings": str(expected.gross_earnings),
            "total_deductions": str(expected.total_deductions),
            "net_salary": str(expected.net_salary),
            "employee_code": expected.employee_code,
            "employee_name": f"{expected.first_name} {expected.last_name}",
        }


def test_payroll_component_report_reads_persisted_rows_filters_and_paginates(
    real_mysql_payroll,
) -> None:
    engine, seed = real_mysql_payroll
    _add_report_employee(engine, seed)
    deduction_component_id = _add_report_deduction_component(engine, seed)
    _finalize_seed_run(seed)
    other_run_id = _add_other_run_result(engine, seed)
    _add_component_to_other_finalized_run(engine, seed, other_run_id)

    from app.infrastructure.persistence.models.employee import Employee
    from app.infrastructure.persistence.models.payroll_result import PayrollResultModel
    from app.infrastructure.persistence.models.payroll_result_component import (
        PayrollResultComponentModel,
    )
    from app.infrastructure.persistence.models.payroll_run import PayrollRunModel
    from app.infrastructure.persistence.models.salary_component import SalaryComponentModel
    from app.infrastructure.security.jwt import create_access_token
    from app.main import app

    token = create_access_token(seed.user_id, seed.username)
    headers = {"Authorization": f"Bearer {token}"}
    with Session(engine) as session:
        expected = session.execute(
            select(
                PayrollResultComponentModel.payroll_result_component_id,
                PayrollRunModel.payroll_run_id,
                PayrollResultModel.payroll_result_id,
                PayrollResultModel.employee_id,
                Employee.employee_code,
                Employee.first_name,
                Employee.last_name,
                PayrollResultComponentModel.salary_component_id,
                SalaryComponentModel.component_code,
                SalaryComponentModel.component_name,
                PayrollResultComponentModel.component_type,
                PayrollResultComponentModel.amount,
                PayrollResultComponentModel.calculation_order,
                SalaryComponentModel.status,
            )
            .join(
                PayrollResultModel,
                PayrollResultModel.payroll_result_id
                == PayrollResultComponentModel.payroll_result_id,
            )
            .join(PayrollRunModel, PayrollRunModel.payroll_run_id == PayrollResultModel.payroll_run_id)
            .outerjoin(Employee, Employee.employee_id == PayrollResultModel.employee_id)
            .join(
                SalaryComponentModel,
                SalaryComponentModel.salary_component_id
                == PayrollResultComponentModel.salary_component_id,
            )
            .where(PayrollRunModel.payroll_run_id == seed.payroll_run_id)
            .order_by(
                PayrollResultModel.payroll_result_id,
                PayrollResultComponentModel.salary_component_id,
            )
        ).all()
        persisted_amounts_and_orders = [
            (row.amount, row.calculation_order) for row in expected
        ]
        assert {row.component_type for row in expected} == {"EARNING", "DEDUCTION"}
        assert any(row.salary_component_id == deduction_component_id for row in expected)
        assert any(
            row.component_name.startswith("Report Deduction ") and row.status == "INACTIVE"
            for row in expected
        )

    expected_payload = [
        {
            "payroll_result_component_id": row.payroll_result_component_id,
            "payroll_run_id": row.payroll_run_id,
            "payroll_result_id": row.payroll_result_id,
            "employee_id": row.employee_id,
            "employee_code": row.employee_code,
            "employee_name": f"{row.first_name} {row.last_name}",
            "salary_component_id": row.salary_component_id,
            "component_code": row.component_code,
            "component_name": row.component_name,
            "component_type": row.component_type,
            "amount": str(row.amount),
            "calculation_order": row.calculation_order,
        }
        for row in expected
    ]

    pages = []
    cursor = None
    with TestClient(app, raise_server_exceptions=False) as client:
        while True:
            response = client.get(
                f"/api/v1/reports/payroll/runs/{seed.payroll_run_id}/components",
                params={"limit": 1, **({"cursor": cursor} if cursor else {})},
                headers=headers,
            )
            assert response.status_code == 200, response.text
            page = response.json()
            pages.extend(page["components"])
            if not page["pagination"]["has_more"]:
                assert page["pagination"]["next_cursor"] is None
                break
            cursor = page["pagination"]["next_cursor"]
            assert cursor

        employee_filter = client.get(
            f"/api/v1/reports/payroll/runs/{seed.payroll_run_id}/components",
            params={"employee_id": seed.employee_id},
            headers=headers,
        )
        component_filter = client.get(
            f"/api/v1/reports/payroll/runs/{seed.payroll_run_id}/components",
            params={"salary_component_id": deduction_component_id},
            headers=headers,
        )
        type_filter = client.get(
            f"/api/v1/reports/payroll/runs/{seed.payroll_run_id}/components",
            params={"component_type": "DEDUCTION"},
            headers=headers,
        )
        other_run = client.get(
            f"/api/v1/reports/payroll/runs/{other_run_id}/components",
            headers=headers,
        )

    assert pages == expected_payload
    assert len(pages) == 4
    assert len({(row["payroll_result_id"], row["salary_component_id"]) for row in pages}) == 4
    assert [(row["amount"], row["calculation_order"]) for row in pages] == [
        (str(amount), order) for amount, order in persisted_amounts_and_orders
    ]
    for filtered in (employee_filter, component_filter, type_filter):
        assert filtered.status_code == 200, filtered.text
    assert {row["employee_id"] for row in employee_filter.json()["components"]} == {
        seed.employee_id
    }
    assert {row["salary_component_id"] for row in component_filter.json()["components"]} == {
        deduction_component_id
    }
    assert {row["component_type"] for row in type_filter.json()["components"]} == {
        "DEDUCTION"
    }
    assert len(component_filter.json()["components"]) == 2
    assert len(type_filter.json()["components"]) == 2
    assert other_run.status_code == 200, other_run.text
    assert len(other_run.json()["components"]) == 1
    assert other_run.json()["components"][0]["payroll_run_id"] == other_run_id
    assert all(row["payroll_run_id"] == seed.payroll_run_id for row in pages)


def test_payroll_component_report_uses_persisted_authorization_and_run_state(
    real_mysql_payroll,
) -> None:
    engine, seed = real_mysql_payroll
    unprivileged_user_id, unprivileged_username = _add_report_unprivileged_user(
        engine, seed
    )
    empty_finalized_run_id = _add_empty_finalized_run(engine, seed)
    from app.infrastructure.security.jwt import create_access_token
    from app.main import app

    payroll_headers = {
        "Authorization": f"Bearer {create_access_token(seed.user_id, seed.username)}"
    }
    unprivileged_headers = {
        "Authorization": f"Bearer {create_access_token(unprivileged_user_id, unprivileged_username)}"
    }
    with TestClient(app, raise_server_exceptions=False) as client:
        non_finalized = client.get(
            f"/api/v1/reports/payroll/runs/{seed.payroll_run_id}/components",
            headers=payroll_headers,
        )
        missing = client.get(
            "/api/v1/reports/payroll/runs/999999999/components",
            headers=payroll_headers,
        )
        empty = client.get(
            f"/api/v1/reports/payroll/runs/{empty_finalized_run_id}/components",
            headers=payroll_headers,
        )
        forbidden = client.get(
            f"/api/v1/reports/payroll/runs/{empty_finalized_run_id}/components",
            headers=unprivileged_headers,
        )

    assert non_finalized.status_code == 409, non_finalized.text
    assert missing.status_code == 404, missing.text
    assert empty.status_code == 200, empty.text
    assert empty.json() == {
        "payroll_run_id": empty_finalized_run_id,
        "components": [],
        "pagination": {"limit": 50, "has_more": False, "next_cursor": None},
    }
    assert forbidden.status_code == 403, forbidden.text


def test_payroll_component_report_sanitizes_missing_definition_error(
    real_mysql_payroll, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine, seed = real_mysql_payroll
    _finalize_seed_run(seed)
    from dataclasses import replace

    from app.infrastructure.persistence.repositories.payroll_result_component_repository import (
        PayrollResultComponentRepository,
    )
    from app.infrastructure.persistence.models.salary_component import (
        SalaryComponentModel,
    )
    from app.infrastructure.security.jwt import create_access_token
    from app.main import app

    original_list_report_page = PayrollResultComponentRepository.list_report_page

    def report_missing_definition(self, *args, **kwargs):
        records = original_list_report_page(self, *args, **kwargs)
        if records:
            records[0] = replace(
                records[0],
                salary_component_definition_exists=False,
                component_code=None,
                component_name=None,
            )
        return records

    monkeypatch.setattr(
        PayrollResultComponentRepository,
        "list_report_page",
        report_missing_definition,
    )
    token = create_access_token(seed.user_id, seed.username)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(
            f"/api/v1/reports/payroll/runs/{seed.payroll_run_id}/components",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 500
    body = response.json()
    error = body["error"]
    request_id = error["request_id"]
    UUID(request_id)
    assert body == {
        "error": {
            "code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred.",
            "request_id": request_id,
        }
    }
    assert "SELECT" not in response.text
    assert "salary_components" not in response.text
    with Session(engine) as session:
        component = session.get(SalaryComponentModel, seed.salary_component_id)
        assert component is not None
        assert component.component_code not in response.text
        assert component.component_name not in response.text


def test_employee_report_uses_seeded_hr_permission_and_filters_persisted_rows(
    real_mysql_payroll,
) -> None:
    engine, seed = real_mysql_payroll
    from app.infrastructure.persistence.models.department import Department
    from app.infrastructure.persistence.models.designation import Designation
    from app.infrastructure.persistence.models.employee import Employee
    from app.infrastructure.persistence.models.permission import Permission
    from app.infrastructure.persistence.models.role import Role
    from app.infrastructure.persistence.models.role_permission import RolePermission
    from app.infrastructure.persistence.models.user import User
    from app.infrastructure.persistence.models.user_role import UserRole
    from app.infrastructure.security.jwt import create_access_token
    from app.main import app

    username = f"r9c1_hr_{uuid4().hex[:12]}"
    unprivileged_user_id, unprivileged_username = _add_report_unprivileged_user(
        engine, seed
    )
    with Session(engine) as session:
        hr_role = session.scalar(
            select(Role).where(Role.role_name == "HR Administrator")
        )
        permission = session.scalar(
            select(Permission).where(
                Permission.permission_code == "report.employee.read"
            )
        )
        assert hr_role is not None
        assert permission is not None
        assert session.get(
            RolePermission, (hr_role.role_id, permission.permission_id)
        ) is not None
        hr_permission_codes = session.scalars(
            select(Permission.permission_code)
            .join(RolePermission, RolePermission.permission_id == Permission.permission_id)
            .where(RolePermission.role_id == hr_role.role_id)
            .order_by(Permission.permission_code)
        ).all()
        assert hr_permission_codes == [
            "report.attendance.read",
            "report.employee.read",
        ]

        hr_user = User(
            username=username,
            email=f"{username}@example.invalid",
            password_hash="integration-only-not-used-for-login",
            status="ACTIVE",
        )
        second_employee = Employee(
            employee_code=f"R9C1-{uuid4().hex[:12]}",
            user_id=None,
            first_name="Inactive",
            last_name="Report",
            department_id=seed.department_id,
            designation_id=seed.designation_id,
            joining_date=date(2018, 5, 1),
            employment_end_date=date(2025, 2, 1),
            employment_status="INACTIVE",
        )
        third_employee = Employee(
            employee_code=f"R9C1-{uuid4().hex[:12]}",
            user_id=None,
            first_name="Terminated",
            last_name="Report",
            department_id=seed.department_id,
            designation_id=seed.designation_id,
            joining_date=date(2017, 4, 1),
            employment_end_date=date(2024, 3, 1),
            employment_status="TERMINATED",
        )
        session.add_all([hr_user, second_employee, third_employee])
        session.flush()
        session.add(
            UserRole(
                user_id=hr_user.user_id,
                role_id=hr_role.role_id,
                assigned_by_user_id=seed.user_id,
            )
        )
        session.commit()
        hr_user_id = hr_user.user_id
        seed.extra_users += ((hr_user_id, username),)
        seed.extra_employee_ids += (
            second_employee.employee_id,
            third_employee.employee_id,
        )
        first_employee_code = session.get(Employee, seed.employee_id).employee_code
        expected_department_name = session.get(
            Department, seed.department_id
        ).department_name
        expected_designation_name = session.get(
            Designation, seed.designation_id
        ).designation_name

    hr_headers = {
        "Authorization": f"Bearer {create_access_token(hr_user_id, username)}"
    }
    payroll_headers = {
        "Authorization": f"Bearer {create_access_token(seed.user_id, seed.username)}"
    }
    unprivileged_headers = {
        "Authorization": f"Bearer {create_access_token(unprivileged_user_id, unprivileged_username)}"
    }
    with TestClient(app, raise_server_exceptions=False) as client:
        denied = client.get("/api/v1/reports/employees", headers=payroll_headers)
        assert denied.status_code == 403, denied.text
        no_role = client.get(
            "/api/v1/reports/employees", headers=unprivileged_headers
        )
        assert no_role.status_code == 403, no_role.text

        first = client.get(
            "/api/v1/reports/employees", params={"limit": 1}, headers=hr_headers
        )
        assert first.status_code == 200, first.text
        first_body = first.json()
        assert first_body["pagination"]["has_more"] is True
        assert first_body["employees"][0]["employee_id"] == seed.employee_id
        assert first_body["employees"][0]["department_name"] == expected_department_name
        assert first_body["employees"][0]["designation_name"] == expected_designation_name
        assert set(first_body["employees"][0]) == {
            "employee_id", "employee_code", "first_name", "last_name",
            "department_id", "department_name", "designation_id",
            "designation_name", "joining_date", "employment_end_date",
            "employment_status",
        }

        second = client.get(
            "/api/v1/reports/employees",
            params={"limit": 1, "cursor": first_body["pagination"]["next_cursor"]},
            headers=hr_headers,
        )
        assert second.status_code == 200, second.text
        assert second.json()["employees"][0]["employee_id"] == seed.employee_id + 1

        exact_code = client.get(
            "/api/v1/reports/employees",
            params={"employee_code": first_employee_code},
            headers=hr_headers,
        )
        assert exact_code.status_code == 200
        assert [row["employee_code"] for row in exact_code.json()["employees"]] == [
            first_employee_code
        ]

        filtered = client.get(
            "/api/v1/reports/employees",
            params={
                "department_id": seed.department_id,
                "designation_id": seed.designation_id,
                "employment_status": "TERMINATED",
            },
            headers=hr_headers,
        )
        assert filtered.status_code == 200
        assert [row["employment_status"] for row in filtered.json()["employees"]] == [
            "TERMINATED"
        ]
        mismatch = client.get(
            "/api/v1/reports/employees",
            params={
                "limit": 1,
                "cursor": first_body["pagination"]["next_cursor"],
                "employment_status": "ACTIVE",
            },
            headers=hr_headers,
        )
        assert mismatch.status_code == 422


def test_attendance_report_uses_hr_permission_filters_rows_and_paginates_same_date(
    real_mysql_payroll,
) -> None:
    engine, seed = real_mysql_payroll
    from app.infrastructure.persistence.models.attendance import AttendanceRecord
    from app.infrastructure.persistence.models.audit_event import AuditEventModel
    from app.infrastructure.persistence.models.employee import Employee
    from app.infrastructure.persistence.models.permission import Permission
    from app.infrastructure.persistence.models.role import Role
    from app.infrastructure.persistence.models.role_permission import RolePermission
    from app.infrastructure.persistence.models.user import User
    from app.infrastructure.persistence.models.user_role import UserRole
    from app.infrastructure.security.jwt import create_access_token
    from app.main import app

    username = f"r9c2_hr_{uuid4().hex[:12]}"
    day = date(2025, 1, 2)
    unprivileged_user_id, unprivileged_username = _add_report_unprivileged_user(
        engine, seed
    )
    with Session(engine) as session:
        hr_role = session.scalar(
            select(Role).where(Role.role_name == "HR Administrator")
        )
        assert hr_role is not None
        hr_permission_codes = session.scalars(
            select(Permission.permission_code)
            .join(RolePermission, RolePermission.permission_id == Permission.permission_id)
            .where(RolePermission.role_id == hr_role.role_id)
            .order_by(Permission.permission_code)
        ).all()
        assert hr_permission_codes == [
            "report.attendance.read",
            "report.employee.read",
        ]
        payroll_codes = session.scalars(
            select(Permission.permission_code)
            .join(RolePermission, RolePermission.permission_id == Permission.permission_id)
            .where(RolePermission.role_id == seed.role_id)
        ).all()
        assert "report.attendance.read" not in payroll_codes

        hr_user = User(
            username=username,
            email=f"{username}@example.invalid",
            password_hash="integration-only-not-used-for-login",
            status="ACTIVE",
        )
        employees = [
            Employee(
                employee_code=f"R9C2-{uuid4().hex[:12]}",
                user_id=None,
                first_name=first_name,
                last_name=last_name,
                department_id=seed.department_id,
                designation_id=seed.designation_id,
                joining_date=date(2019, 1, 1),
                employment_end_date=None,
                employment_status="ACTIVE",
            )
            for first_name, last_name in (("Present", "Report"), ("Absent", "Report"))
        ]
        session.add_all([hr_user, *employees])
        session.flush()
        session.add(
            UserRole(
                user_id=hr_user.user_id,
                role_id=hr_role.role_id,
                assigned_by_user_id=seed.user_id,
            )
        )
        attendance_rows = [
            AttendanceRecord(
                employee_id=employees[0].employee_id,
                attendance_date=day,
                attendance_status="PRESENT",
                check_in_time=None,
                check_out_time=None,
            ),
            AttendanceRecord(
                employee_id=employees[1].employee_id,
                attendance_date=day,
                attendance_status="ABSENT",
                check_in_time=datetime.combine(day, time(9, 0)),
                check_out_time=None,
            ),
        ]
        session.add_all(attendance_rows)
        session.commit()
        hr_user_id = hr_user.user_id
        seed.extra_users += ((hr_user_id, username),)
        seed.extra_employee_ids += tuple(employee.employee_id for employee in employees)
        attendance_ids = [row.attendance_id for row in attendance_rows]

    with Session(engine) as session:
        audit_count_before = session.scalar(
            select(func.count()).select_from(AuditEventModel)
        )

    hr_headers = {
        "Authorization": f"Bearer {create_access_token(hr_user_id, username)}"
    }
    payroll_headers = {
        "Authorization": f"Bearer {create_access_token(seed.user_id, seed.username)}"
    }
    unprivileged_headers = {
        "Authorization": f"Bearer {create_access_token(unprivileged_user_id, unprivileged_username)}"
    }
    with TestClient(app, raise_server_exceptions=False) as client:
        payroll_denied = client.get(
            "/api/v1/reports/attendance", headers=payroll_headers
        )
        assert payroll_denied.status_code == 403, payroll_denied.text
        unprivileged_denied = client.get(
            "/api/v1/reports/attendance", headers=unprivileged_headers
        )
        assert unprivileged_denied.status_code == 403, unprivileged_denied.text

        params = {
            "date_from": day.isoformat(),
            "date_to": day.isoformat(),
            "department_id": seed.department_id,
            "limit": 1,
        }
        first = client.get(
            "/api/v1/reports/attendance", params=params, headers=hr_headers
        )
        assert first.status_code == 200, first.text
        first_body = first.json()
        assert first_body["pagination"]["has_more"] is True
        first_row = first_body["attendance_records"][0]
        assert first_row["attendance_id"] == min(attendance_ids)
        assert first_row["attendance_date"] == day.isoformat()
        assert set(first_row) == {
            "attendance_id", "employee_id", "employee_code", "first_name", "last_name",
            "department_id", "department_name", "designation_id", "designation_name",
            "attendance_date", "attendance_status", "check_in_time", "check_out_time",
        }

        second = client.get(
            "/api/v1/reports/attendance",
            params={**params, "cursor": first_body["pagination"]["next_cursor"]},
            headers=hr_headers,
        )
        assert second.status_code == 200, second.text
        second_body = second.json()
        assert second_body["pagination"]["has_more"] is False
        second_row = second_body["attendance_records"][0]
        assert second_row["attendance_id"] == max(attendance_ids)
        assert second_row["attendance_date"] == day.isoformat()
        assert second_row["check_in_time"] == "2025-01-02T09:00:00"
        assert second_row["check_out_time"] is None
        assert first_row["check_in_time"] is None
        assert first_row["check_out_time"] is None

        filtered = client.get(
            "/api/v1/reports/attendance",
            params={**params, "attendance_status": "ABSENT"},
            headers=hr_headers,
        )
        assert filtered.status_code == 200, filtered.text
        assert [row["attendance_status"] for row in filtered.json()["attendance_records"]] == [
            "ABSENT"
        ]

    with Session(engine) as session:
        audit_count_after = session.scalar(
            select(func.count()).select_from(AuditEventModel)
        )
    assert audit_count_after == audit_count_before


def _add_report_employee(engine, seed: SeededPayroll) -> None:
    from app.infrastructure.persistence.models.attendance import AttendanceRecord
    from app.infrastructure.persistence.models.employee import Employee
    from app.infrastructure.persistence.models.employee_salary_assignment import (
        EmployeeSalaryAssignmentModel,
    )

    marker = uuid4().hex[:12]
    today = date.today()
    period_start = today.replace(day=1)
    period_end = today.replace(day=28) + timedelta(days=4)
    period_end = period_end.replace(day=1) - timedelta(days=1)
    with Session(engine) as session:
        employee = Employee(
            employee_code=f"R9B-E{marker}",
            user_id=None,
            first_name="Report",
            last_name=marker,
            department_id=seed.department_id,
            designation_id=seed.designation_id,
            joining_date=date(2000, 1, 1),
            employment_end_date=None,
            employment_status="ACTIVE",
        )
        session.add(employee)
        session.flush()
        assignment = EmployeeSalaryAssignmentModel(
            employee_id=employee.employee_id,
            salary_revision_id=seed.salary_revision_id,
            effective_from=date(2000, 1, 1),
            effective_to=date(2099, 12, 31),
        )
        session.add(assignment)
        cursor = period_start
        while cursor <= period_end:
            if cursor.isoweekday() < 6:
                session.add(
                    AttendanceRecord(
                        employee_id=employee.employee_id,
                        attendance_date=cursor,
                        check_in_time=datetime.combine(cursor, time(9, 0)),
                        check_out_time=datetime.combine(cursor, time(17, 0)),
                        attendance_status="PRESENT",
                    )
                )
            cursor += timedelta(days=1)
        session.commit()
        seed.extra_employee_ids += (employee.employee_id,)
        seed.extra_salary_assignment_ids += (assignment.salary_assignment_id,)


def _add_report_deduction_component(engine, seed: SeededPayroll) -> int:
    """Add a fixture-owned deduction to the revision before payroll processing."""
    from app.infrastructure.persistence.models.salary_component import SalaryComponentModel
    from app.infrastructure.persistence.models.salary_revision_component import (
        SalaryRevisionComponentModel,
    )

    marker = uuid4().hex[:12]
    with Session(engine) as session:
        component = SalaryComponentModel(
            component_code=f"R9D{marker}",
            component_name=f"Report Deduction {marker}",
            component_type="DEDUCTION",
            status="INACTIVE",
        )
        session.add(component)
        session.flush()
        session.add(
            SalaryRevisionComponentModel(
                salary_revision_id=seed.salary_revision_id,
                salary_component_id=component.salary_component_id,
                calculation_type="FIXED",
                is_overtime_base=False,
                fixed_amount=Decimal("250.00"),
                percentage_value=None,
                base_component_id=None,
            )
        )
        session.commit()
        seed.extra_salary_component_ids += (component.salary_component_id,)
        return component.salary_component_id


def _add_component_to_other_finalized_run(engine, seed: SeededPayroll, run_id: int) -> None:
    """Create one valid persisted component row for a separate finalized run."""
    from app.infrastructure.persistence.models.payroll_result import PayrollResultModel
    from app.infrastructure.persistence.models.payroll_result_component import (
        PayrollResultComponentModel,
    )

    with Session(engine) as session:
        result = session.scalar(
            select(PayrollResultModel).where(PayrollResultModel.payroll_run_id == run_id)
        )
        assert result is not None
        session.add(
            PayrollResultComponentModel(
                payroll_result_id=result.payroll_result_id,
                salary_component_id=seed.salary_component_id,
                component_type="EARNING",
                amount=Decimal("100.00"),
                calculation_order=1,
            )
        )
        session.commit()


def _add_empty_finalized_run(engine, seed: SeededPayroll) -> int:
    from app.infrastructure.persistence.models.payroll_run import PayrollRunModel

    today = date.today()
    year = today.year - 1 if today.month <= 2 else today.year
    month = 12 if today.month == 1 else 1 if today.month == 2 else today.month - 2
    finalized_at = datetime.now()
    with Session(engine) as session:
        run = PayrollRunModel(
            payroll_year=year,
            payroll_month=month,
            status="FINALIZED",
            initiated_by_user_id=seed.user_id,
            completed_at=finalized_at,
            finalized_at=finalized_at,
        )
        session.add(run)
        session.commit()
        seed.extra_payroll_run_ids += (run.payroll_run_id,)
        return run.payroll_run_id


def _add_report_unprivileged_user(engine, seed: SeededPayroll) -> tuple[int, str]:
    from app.infrastructure.persistence.models.user import User
    from app.infrastructure.security.password import hash_password

    username = f"r9b_noperm_{uuid4().hex[:12]}"
    with Session(engine) as session:
        user = User(
            username=username,
            email=f"{username}@example.invalid",
            password_hash=hash_password("R9B synthetic credential"),
            status="ACTIVE",
        )
        session.add(user)
        session.commit()
        seed.extra_users += ((user.user_id, username),)
        return user.user_id, username


def _add_other_run_result(engine, seed: SeededPayroll) -> int:
    from app.infrastructure.persistence.models.payroll_result import PayrollResultModel
    from app.infrastructure.persistence.models.payroll_run import PayrollRunModel

    today = date.today()
    previous_year = today.year - 1 if today.month == 1 else today.year
    previous_month = 12 if today.month == 1 else today.month - 1
    finalized_at = datetime.now()
    with Session(engine) as session:
        run = PayrollRunModel(
            payroll_year=previous_year,
            payroll_month=previous_month,
            status="FINALIZED",
            initiated_by_user_id=seed.user_id,
            completed_at=finalized_at,
            finalized_at=finalized_at,
        )
        session.add(run)
        session.flush()
        session.add(
            PayrollResultModel(
                payroll_run_id=run.payroll_run_id,
                employee_id=seed.employee_id,
                salary_assignment_id=seed.salary_assignment_id,
                gross_earnings=Decimal("100.00"),
                total_deductions=Decimal("0.00"),
                net_salary=Decimal("100.00"),
                workforce_calculation_snapshot=None,
            )
        )
        session.commit()
        seed.extra_payroll_run_ids += (run.payroll_run_id,)
        return run.payroll_run_id


def _seed_valid_payroll(engine) -> SeededPayroll:
    from app.infrastructure.persistence.models.attendance import AttendanceRecord
    from app.infrastructure.persistence.models.department import Department
    from app.infrastructure.persistence.models.designation import Designation
    from app.infrastructure.persistence.models.employee import Employee
    from app.infrastructure.persistence.models.payroll_run import PayrollRunModel
    from app.infrastructure.persistence.models.role import Role
    from app.infrastructure.persistence.models.role_permission import RolePermission
    from app.infrastructure.persistence.models.salary_component import SalaryComponentModel
    from app.infrastructure.persistence.models.salary_revision import SalaryRevisionModel
    from app.infrastructure.persistence.models.salary_revision_component import SalaryRevisionComponentModel
    from app.infrastructure.persistence.models.salary_structure import SalaryStructureModel
    from app.infrastructure.persistence.models.employee_salary_assignment import EmployeeSalaryAssignmentModel
    from app.infrastructure.persistence.models.user import User
    from app.infrastructure.persistence.models.user_role import UserRole
    from app.infrastructure.persistence.models.work_calendar_version import WorkCalendarVersionModel
    from app.infrastructure.persistence.models.work_calendar_weekly_rule import WorkCalendarWeeklyRuleModel
    from app.infrastructure.persistence.models.workforce_overtime_policy_version import WorkforceOvertimePolicyVersionModel
    from app.infrastructure.security.password import hash_password

    marker = uuid4().hex[:12]
    today = date.today()
    period_start = today.replace(day=1)
    period_end = today.replace(day=28) + timedelta(days=4)
    period_end = period_end.replace(day=1) - timedelta(days=1)
    with Session(engine) as session:
        user = User(
            username=f"r6_{marker}",
            email=f"r6_{marker}@example.invalid",
            password_hash=hash_password("R6-only synthetic credential"),
            status="ACTIVE",
        )
        role = session.scalar(
            select(Role).where(Role.role_name == "Payroll Administrator")
        )
        created_role = role is None
        if role is None:
            role = Role(role_name="Payroll Administrator", is_active=True)
        hr_role = session.scalar(
            select(Role).where(Role.role_name == "HR Administrator")
        )
        created_hr_role = hr_role is None
        if hr_role is None:
            hr_role = Role(role_name="HR Administrator", is_active=True)
        permission, created_permission = _get_or_create_permission(
            session, "payroll.run.process", "R6 test"
        )
        compensation_permission, created_compensation_permission = (
            _get_or_create_permission(
                session, "compensation.write", "Create compensation data."
            )
        )
        recover_permission, created_recover_permission = _get_or_create_permission(
            session, "payroll.run.recover", "Expired attempt recovery"
        )
        retry_permission, created_retry_permission = _get_or_create_permission(
            session, "payroll.run.retry", "Retry failed payroll attempt"
        )
        finalize_permission, created_finalize_permission = _get_or_create_permission(
            session, "payroll.run.finalize", "R7 test"
        )
        payslip_permission, created_payslip_permission = _get_or_create_permission(
            session, "payroll.payslip.create", "R8 test"
        )
        report_permission, created_report_permission = _get_or_create_permission(
            session, "report.payroll.read", "Payroll summary read"
        )
        hr_permission, created_hr_permission = _get_or_create_permission(
            session, "report.employee.read", "Employee report read"
        )
        attendance_report_permission, created_attendance_report_permission = (
            _get_or_create_permission(
                session,
                "report.attendance.read",
                "Attendance report read",
            )
        )
        department = Department(
            department_code=f"R6D{marker}", department_name=f"R6 Department {marker}", status="ACTIVE"
        )
        designation = Designation(
            designation_code=f"R6T{marker}", designation_name=f"R6 Employee {marker}", status="ACTIVE"
        )
        structure = SalaryStructureModel(
            structure_code=f"R6S{marker}", structure_name=f"R6 Structure {marker}", status="ACTIVE"
        )
        component = SalaryComponentModel(
            component_code=f"R6C{marker}", component_name=f"R6 Base {marker}", component_type="EARNING", status="ACTIVE"
        )
        session.add_all([user, department, designation, structure, component])
        if created_role:
            session.add(role)
        if created_hr_role:
            session.add(hr_role)
        session.flush()
        session.add(
            UserRole(
                user_id=user.user_id,
                role_id=role.role_id,
                assigned_by_user_id=user.user_id,
            )
        )
        created_role_permission_ids = []
        for item in (
            compensation_permission,
            permission,
            recover_permission,
            retry_permission,
            finalize_permission,
            payslip_permission,
            report_permission,
        ):
            if session.get(RolePermission, (role.role_id, item.permission_id)) is None:
                session.add(
                    RolePermission(role_id=role.role_id, permission_id=item.permission_id)
                )
                created_role_permission_ids.append(item.permission_id)
        created_hr_role_permission = session.get(
            RolePermission, (hr_role.role_id, hr_permission.permission_id)
        ) is None
        if created_hr_role_permission:
            session.add(
                RolePermission(
                    role_id=hr_role.role_id,
                    permission_id=hr_permission.permission_id,
                )
            )
        created_hr_attendance_role_permission = session.get(
            RolePermission,
            (hr_role.role_id, attendance_report_permission.permission_id),
        ) is None
        if created_hr_attendance_role_permission:
            session.add(
                RolePermission(
                    role_id=hr_role.role_id,
                    permission_id=attendance_report_permission.permission_id,
                )
            )
        employee = Employee(
            employee_code=f"R6E{marker}", user_id=None, first_name="Test", last_name=marker,
            department_id=department.department_id, designation_id=designation.designation_id,
            joining_date=date(2000, 1, 1), employment_end_date=None, employment_status="ACTIVE",
        )
        session.add(employee)
        calendar = WorkCalendarVersionModel(
            version_number=1000000 + int(marker[:5], 16), effective_from=date(2000, 1, 1),
            effective_to=date(2099, 12, 31), time_zone="UTC", created_by_user_id=user.user_id,
        )
        policy = WorkforceOvertimePolicyVersionModel(
            version_number=1000000 + int(marker[:5], 16), effective_from=date(2000, 1, 1),
            effective_to=date(2099, 12, 31), non_working_multiplier=Decimal("1.5000"),
            created_by_user_id=user.user_id,
        )
        session.add_all([calendar, policy])
        session.flush()
        session.add_all([
            WorkCalendarWeeklyRuleModel(
                work_calendar_version_id=calendar.work_calendar_version_id,
                iso_weekday=weekday,
                classification="WORKING_DAY" if weekday < 6 else "NON_WORKING_DAY",
                scheduled_minutes=480 if weekday < 6 else 0,
            )
            for weekday in range(1, 8)
        ])
        revision = SalaryRevisionModel(
            salary_structure_id=structure.salary_structure_id,
            revision_number=1,
            effective_from=date(2000, 1, 1),
            effective_to=date(2099, 12, 31),
        )
        session.add(revision)
        session.flush()
        session.add(SalaryRevisionComponentModel(
            salary_revision_id=revision.salary_revision_id,
            salary_component_id=component.salary_component_id,
            calculation_type="FIXED",
            is_overtime_base=True,
            fixed_amount=Decimal("5000.00"),
            percentage_value=None,
            base_component_id=None,
        ))
        assignment = EmployeeSalaryAssignmentModel(
            employee_id=employee.employee_id,
            salary_revision_id=revision.salary_revision_id,
            effective_from=date(2000, 1, 1),
            effective_to=date(2099, 12, 31),
        )
        run = PayrollRunModel(
            payroll_year=today.year,
            payroll_month=today.month,
            status="CREATED",
            initiated_by_user_id=user.user_id,
        )
        session.add_all([assignment, run])
        session.flush()
        cursor = period_start
        while cursor <= period_end:
            if cursor.isoweekday() < 6:
                session.add(AttendanceRecord(
                    employee_id=employee.employee_id,
                    attendance_date=cursor,
                    check_in_time=datetime.combine(cursor, time(9, 0)),
                    check_out_time=datetime.combine(cursor, time(17, 0)),
                    attendance_status="PRESENT",
                ))
            cursor += timedelta(days=1)
        session.commit()
        return SeededPayroll(
            user_id=user.user_id,
            username=user.username,
            password="R6-only synthetic credential",
            employee_id=employee.employee_id,
            department_id=department.department_id,
            designation_id=designation.designation_id,
            role_id=role.role_id,
            created_role=created_role,
            created_role_permission_ids=tuple(created_role_permission_ids),
            hr_role_id=hr_role.role_id,
            created_hr_role=created_hr_role,
            created_hr_role_permission=created_hr_role_permission,
            hr_permission_id=hr_permission.permission_id,
            created_hr_permission=created_hr_permission,
            attendance_report_permission_id=attendance_report_permission.permission_id,
            created_hr_attendance_role_permission=created_hr_attendance_role_permission,
            permission_id=permission.permission_id,
            recover_permission_id=recover_permission.permission_id,
            finalize_permission_id=finalize_permission.permission_id,
            payslip_permission_id=payslip_permission.permission_id,
            report_permission_id=report_permission.permission_id,
            created_permission_ids=tuple(
                item.permission_id
                for item, created in (
                    (compensation_permission, created_compensation_permission),
                    (permission, created_permission),
                    (recover_permission, created_recover_permission),
                    (retry_permission, created_retry_permission),
                    (finalize_permission, created_finalize_permission),
                    (payslip_permission, created_payslip_permission),
                    (report_permission, created_report_permission),
                    (hr_permission, created_hr_permission),
                    (
                        attendance_report_permission,
                        created_attendance_report_permission,
                    ),
                )
                if created
            ),
            salary_structure_id=structure.salary_structure_id,
            salary_component_id=component.salary_component_id,
            salary_revision_id=revision.salary_revision_id,
            salary_assignment_id=assignment.salary_assignment_id,
            calendar_version_id=calendar.work_calendar_version_id,
            policy_version_id=policy.workforce_overtime_policy_version_id,
            payroll_run_id=run.payroll_run_id,
            correlation_id=f"r6-{marker}",
        )


def _cleanup_seed(engine, seed: SeededPayroll) -> None:
    from app.infrastructure.persistence.models.audit_event import AuditEventModel
    from app.infrastructure.persistence.models.audit_event_change import AuditEventChangeModel
    from app.infrastructure.persistence.models.attendance import AttendanceRecord
    from app.infrastructure.persistence.models.department import Department
    from app.infrastructure.persistence.models.designation import Designation
    from app.infrastructure.persistence.models.employee import Employee
    from app.infrastructure.persistence.models.employee_salary_assignment import EmployeeSalaryAssignmentModel
    from app.infrastructure.persistence.models.payroll_processing_issue import PayrollProcessingIssueModel
    from app.infrastructure.persistence.models.payroll_result import PayrollResultModel
    from app.infrastructure.persistence.models.payroll_result_component import PayrollResultComponentModel
    from app.infrastructure.persistence.models.payroll_run import PayrollRunModel
    from app.infrastructure.persistence.models.payroll_run_workforce_snapshot import PayrollRunWorkforceSnapshotModel
    from app.infrastructure.persistence.models.payslip import PayslipModel
    from app.infrastructure.persistence.models.permission import Permission
    from app.infrastructure.persistence.models.refresh_token import RefreshToken
    from app.infrastructure.persistence.models.role import Role
    from app.infrastructure.persistence.models.role_permission import RolePermission
    from app.infrastructure.persistence.models.salary_component import SalaryComponentModel
    from app.infrastructure.persistence.models.salary_revision import SalaryRevisionModel
    from app.infrastructure.persistence.models.salary_revision_component import SalaryRevisionComponentModel
    from app.infrastructure.persistence.models.salary_structure import SalaryStructureModel
    from app.infrastructure.persistence.models.user import User
    from app.infrastructure.persistence.models.user_role import UserRole
    from app.infrastructure.persistence.models.work_calendar_version import WorkCalendarVersionModel
    from app.infrastructure.persistence.models.work_calendar_weekly_rule import WorkCalendarWeeklyRuleModel
    from app.infrastructure.persistence.models.workforce_overtime_policy_version import WorkforceOvertimePolicyVersionModel

    owned_run_ids = (seed.payroll_run_id, *seed.extra_payroll_run_ids)
    owned_employee_ids = (seed.employee_id, *seed.extra_employee_ids)
    owned_user_ids = (seed.user_id, *(user_id for user_id, _ in seed.extra_users))
    owned_assignment_ids = (
        seed.salary_assignment_id,
        *seed.extra_salary_assignment_ids,
    )
    owned_salary_revision_ids = (
        seed.salary_revision_id,
        *seed.extra_salary_revision_ids,
    )
    owned_salary_structure_ids = (
        seed.salary_structure_id,
        *seed.extra_salary_structure_ids,
    )
    with Session(engine) as session, session.begin():
        result_ids = select(PayrollResultModel.payroll_result_id).where(
            PayrollResultModel.payroll_run_id.in_(owned_run_ids)
        )
        owned_payslip_ids = list(session.scalars(
            select(PayslipModel.payslip_id)
            .join(PayrollResultModel, PayslipModel.payroll_result_id == PayrollResultModel.payroll_result_id)
            .where(PayrollResultModel.payroll_run_id.in_(owned_run_ids))
        ).all())
        _delete_owned_audit_events(
            session,
            AuditEventModel,
            AuditEventChangeModel,
            seed.payroll_run_id,
            owned_payslip_ids,
            seed.user_id,
        )
        session.execute(
            delete(RefreshToken).where(RefreshToken.user_id.in_(owned_user_ids))
        )
        session.execute(delete(PayslipModel).where(
            PayslipModel.payslip_id.in_(owned_payslip_ids)
        ))
        session.execute(delete(PayrollResultComponentModel).where(PayrollResultComponentModel.payroll_result_id.in_(result_ids)))
        session.execute(delete(PayrollResultModel).where(PayrollResultModel.payroll_run_id.in_(owned_run_ids)))
        session.execute(delete(PayrollProcessingIssueModel).where(PayrollProcessingIssueModel.payroll_run_id.in_(owned_run_ids)))
        session.execute(delete(PayrollRunWorkforceSnapshotModel).where(PayrollRunWorkforceSnapshotModel.payroll_run_id.in_(owned_run_ids)))
        session.execute(delete(AttendanceRecord).where(AttendanceRecord.employee_id.in_(owned_employee_ids)))
        session.execute(delete(EmployeeSalaryAssignmentModel).where(EmployeeSalaryAssignmentModel.salary_assignment_id.in_(owned_assignment_ids)))
        session.execute(
            delete(SalaryRevisionComponentModel).where(
                SalaryRevisionComponentModel.salary_revision_id.in_(
                    owned_salary_revision_ids
                )
            )
        )
        session.execute(
            delete(SalaryRevisionModel).where(
                SalaryRevisionModel.salary_revision_id.in_(owned_salary_revision_ids)
            )
        )
        session.execute(
            delete(SalaryStructureModel).where(
                SalaryStructureModel.salary_structure_id.in_(
                    owned_salary_structure_ids
                )
            )
        )
        session.execute(
            delete(SalaryComponentModel).where(
                SalaryComponentModel.salary_component_id.in_(
                    (seed.salary_component_id, *seed.extra_salary_component_ids)
                )
            )
        )
        session.execute(delete(WorkCalendarWeeklyRuleModel).where(WorkCalendarWeeklyRuleModel.work_calendar_version_id == seed.calendar_version_id))
        session.execute(delete(WorkCalendarVersionModel).where(WorkCalendarVersionModel.work_calendar_version_id == seed.calendar_version_id))
        session.execute(delete(WorkforceOvertimePolicyVersionModel).where(WorkforceOvertimePolicyVersionModel.workforce_overtime_policy_version_id == seed.policy_version_id))
        session.execute(delete(PayrollRunModel).where(PayrollRunModel.payroll_run_id.in_(owned_run_ids)))
        session.execute(delete(Employee).where(Employee.employee_id.in_(owned_employee_ids)))
        session.execute(delete(Department).where(Department.department_id == seed.department_id))
        session.execute(delete(Designation).where(Designation.designation_id == seed.designation_id))
        if seed.created_role_permission_ids:
            session.execute(
                delete(RolePermission).where(
                    RolePermission.role_id == seed.role_id,
                    RolePermission.permission_id.in_(seed.created_role_permission_ids),
                )
            )
        if seed.created_hr_role_permission:
            session.execute(
                delete(RolePermission).where(
                    RolePermission.role_id == seed.hr_role_id,
                    RolePermission.permission_id == seed.hr_permission_id,
                )
            )
        if seed.created_hr_attendance_role_permission:
            session.execute(
                delete(RolePermission).where(
                    RolePermission.role_id == seed.hr_role_id,
                    RolePermission.permission_id
                    == seed.attendance_report_permission_id,
                )
            )
        session.execute(delete(UserRole).where(UserRole.user_id.in_(owned_user_ids)))
        if seed.created_permission_ids:
            referenced_permission_ids = set(
                session.scalars(
                    select(RolePermission.permission_id).where(
                        RolePermission.permission_id.in_(seed.created_permission_ids)
                    )
                ).all()
            )
            unused_created_permission_ids = (
                set(seed.created_permission_ids) - referenced_permission_ids
            )
            if unused_created_permission_ids:
                session.execute(
                    delete(Permission).where(
                        Permission.permission_id.in_(unused_created_permission_ids)
                    )
                )
        if seed.created_role:
            session.execute(delete(Role).where(Role.role_id == seed.role_id))
        if seed.created_hr_role:
            session.execute(delete(Role).where(Role.role_id == seed.hr_role_id))
        session.execute(delete(User).where(User.user_id.in_(owned_user_ids)))


def _delete_owned_audit_events(
    session: Session,
    audit_event_model,
    audit_event_change_model,
    payroll_run_id: int,
    payslip_ids: list[int] | None = None,
    actor_user_id: int | None = None,
) -> list[int]:
    """Delete only fixture-owned audit rows without a MySQL self-select DELETE."""
    conditions = [
        and_(
            audit_event_model.resource_type == "PAYROLL_RUN",
            audit_event_model.resource_id == payroll_run_id,
        )
    ]
    if payslip_ids:
        conditions.append(
            and_(
                audit_event_model.resource_type == "PAYSLIP",
                audit_event_model.resource_id.in_(payslip_ids),
            )
        )
    if actor_user_id is not None:
        # The fixture creates a unique synthetic user and all endpoint-generated
        # audit events for that identity are owned by this fixture.
        conditions.append(audit_event_model.actor_user_id == actor_user_id)
    audit_ids = list(
        session.scalars(
            select(audit_event_model.audit_event_id).where(or_(*conditions))
        ).all()
    )
    if audit_ids:
        session.execute(
            delete(audit_event_change_model).where(
                audit_event_change_model.audit_event_id.in_(audit_ids)
            )
        )
        session.execute(
            delete(audit_event_model).where(
                audit_event_model.audit_event_id.in_(audit_ids)
            )
        )
    return audit_ids


def _get_or_create_permission(session: Session, code: str, description: str):
    """Reuse shared permissions and report whether this fixture owns a new row."""
    from app.infrastructure.persistence.models.permission import Permission

    permission = session.scalar(
        select(Permission).where(Permission.permission_code == code)
    )
    if permission is not None:
        return permission, False
    permission = Permission(permission_code=code, description=description)
    session.add(permission)
    session.flush()
    return permission, True


def test_compensation_salary_structure_create_persists(real_mysql_payroll) -> None:
    engine, seed = real_mysql_payroll
    from app.infrastructure.security.jwt import create_access_token
    from app.main import app
    from app.infrastructure.persistence.models.salary_structure import SalaryStructureModel

    marker = uuid4().hex[:16]
    payload = {
        "structure_code": f"IT{marker}",
        "structure_name": f"Integration Structure {marker}",
        "description": "Disposable integration record",
        "status": "ACTIVE",
    }
    token = create_access_token(seed.user_id, seed.username)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/api/v1/salary-structures",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 201, response.text
    structure_id = response.json()["salary_structure_id"]
    seed.extra_salary_structure_ids += (structure_id,)
    with Session(engine) as session:
        persisted = session.get(SalaryStructureModel, structure_id)
        assert persisted is not None
        assert persisted.structure_code == payload["structure_code"]
        assert persisted.structure_name == payload["structure_name"]
        assert persisted.description == payload["description"]
        assert persisted.status == payload["status"]


def test_compensation_salary_component_create_persists(real_mysql_payroll) -> None:
    engine, seed = real_mysql_payroll
    from app.infrastructure.persistence.models.salary_component import SalaryComponentModel
    from app.infrastructure.security.jwt import create_access_token
    from app.main import app

    marker = uuid4().hex[:16]
    payload = {
        "component_code": f"IT{marker}",
        "component_name": f"Integration Component {marker}",
        "component_type": "DEDUCTION",
        "status": "INACTIVE",
    }
    token = create_access_token(seed.user_id, seed.username)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/api/v1/salary-components",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 201, response.text
    component_id = response.json()["salary_component_id"]
    seed.extra_salary_component_ids += (component_id,)
    with Session(engine) as session:
        persisted = session.get(SalaryComponentModel, component_id)
        assert persisted is not None
        assert persisted.component_code == payload["component_code"]
        assert persisted.component_name == payload["component_name"]
        assert persisted.component_type == "DEDUCTION"
        assert persisted.status == "INACTIVE"


def test_compensation_salary_revision_create_persists(real_mysql_payroll) -> None:
    engine, seed = real_mysql_payroll
    from app.infrastructure.persistence.models.salary_revision import SalaryRevisionModel
    from app.infrastructure.security.jwt import create_access_token
    from app.main import app

    payload = {
        "salary_structure_id": seed.salary_structure_id,
        "revision_number": 2,
        "effective_from": "2100-01-01",
        "effective_to": "2100-12-31",
    }
    token = create_access_token(seed.user_id, seed.username)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/api/v1/salary-revisions",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 201, response.text
    revision_id = response.json()["salary_revision_id"]
    seed.extra_salary_revision_ids += (revision_id,)
    with Session(engine) as session:
        persisted = session.get(SalaryRevisionModel, revision_id)
        assert persisted is not None
        assert persisted.salary_structure_id == seed.salary_structure_id
        assert persisted.revision_number == 2
        assert persisted.effective_from == date(2100, 1, 1)
        assert persisted.effective_to == date(2100, 12, 31)


def test_compensation_salary_revision_component_create_persists_and_rejects_cycle(
    real_mysql_payroll,
) -> None:
    engine, seed = real_mysql_payroll
    from app.infrastructure.persistence.models.salary_component import SalaryComponentModel
    from app.infrastructure.persistence.models.salary_revision_component import (
        SalaryRevisionComponentModel,
    )
    from app.infrastructure.security.jwt import create_access_token
    from app.main import app

    token = create_access_token(seed.user_id, seed.username)
    with TestClient(app, raise_server_exceptions=False) as client:
        marker = uuid4().hex[:12]

        def create_component(suffix: str) -> int:
            response = client.post(
                "/api/v1/salary-components",
                json={
                    "component_code": f"IT{marker}{suffix}",
                    "component_name": f"Integration {suffix} {marker}",
                    "component_type": "EARNING",
                    "status": "ACTIVE",
                },
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 201, response.text
            component_id = response.json()["salary_component_id"]
            seed.extra_salary_component_ids += (component_id,)
            return component_id

        persisted_component_id = create_component("P")
        fixed_payload = {
            "salary_revision_id": seed.salary_revision_id,
            "salary_component_id": persisted_component_id,
            "calculation_type": "FIXED",
            "fixed_amount": "1234.56",
            "percentage_value": None,
            "base_component_id": None,
            "is_overtime_base": False,
        }
        response = client.post(
            "/api/v1/salary-revision-components",
            json=fixed_payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201, response.text

        cycle_a_id = create_component("A")
        cycle_b_id = create_component("B")
        cycle_a = client.post(
            "/api/v1/salary-revision-components",
            json={
                "salary_revision_id": seed.salary_revision_id,
                "salary_component_id": cycle_a_id,
                "calculation_type": "PERCENTAGE",
                "fixed_amount": None,
                "percentage_value": "12.3456",
                "base_component_id": cycle_b_id,
                "is_overtime_base": False,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert cycle_a.status_code == 201, cycle_a.text
        cycle_b = client.post(
            "/api/v1/salary-revision-components",
            json={
                "salary_revision_id": seed.salary_revision_id,
                "salary_component_id": cycle_b_id,
                "calculation_type": "PERCENTAGE",
                "fixed_amount": None,
                "percentage_value": "1.2500",
                "base_component_id": cycle_a_id,
                "is_overtime_base": False,
            },
            headers={"Authorization": f"Bearer {token}"},
        )

    assert cycle_b.status_code == 409, cycle_b.text
    assert cycle_b.json()["error"]["code"] == "BUSINESS_RULE_VIOLATION"
    with Session(engine) as session:
        fixed = session.get(
            SalaryRevisionComponentModel,
            (seed.salary_revision_id, persisted_component_id),
        )
        valid_percentage = session.get(
            SalaryRevisionComponentModel,
            (seed.salary_revision_id, cycle_a_id),
        )
        rejected_cycle = session.get(
            SalaryRevisionComponentModel,
            (seed.salary_revision_id, cycle_b_id),
        )
        assert fixed is not None
        assert fixed.fixed_amount == Decimal("1234.56")
        assert fixed.calculation_type == "FIXED"
        assert valid_percentage is not None
        assert valid_percentage.percentage_value == Decimal("12.3456")
        assert rejected_cycle is None
        # Component definitions are the valid parents for the persisted pivot rows.
        assert session.get(SalaryComponentModel, cycle_a_id) is not None
        assert session.get(SalaryComponentModel, cycle_b_id) is not None


def test_compensation_employee_salary_assignment_create_persists(real_mysql_payroll) -> None:
    engine, seed = real_mysql_payroll
    from app.infrastructure.persistence.models.employee_salary_assignment import (
        EmployeeSalaryAssignmentModel,
    )
    from app.infrastructure.persistence.models.salary_revision import SalaryRevisionModel
    from app.infrastructure.security.jwt import create_access_token
    from app.main import app

    token = create_access_token(seed.user_id, seed.username)
    with TestClient(app, raise_server_exceptions=False) as client:
        revision_response = client.post(
            "/api/v1/salary-revisions",
            json={
                "salary_structure_id": seed.salary_structure_id,
                "revision_number": 2,
                "effective_from": "2100-01-01",
                "effective_to": "2100-12-31",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert revision_response.status_code == 201, revision_response.text
        revision_id = revision_response.json()["salary_revision_id"]
        seed.extra_salary_revision_ids += (revision_id,)
        payload = {
            "employee_id": seed.employee_id,
            "salary_revision_id": revision_id,
            "effective_from": "2100-01-01",
            "effective_to": "2100-12-31",
        }
        response = client.post(
            "/api/v1/employee-salary-assignments",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 201, response.text
    assignment_id = response.json()["salary_assignment_id"]
    seed.extra_salary_assignment_ids += (assignment_id,)
    with Session(engine) as session:
        persisted = session.get(EmployeeSalaryAssignmentModel, assignment_id)
        revision = session.get(SalaryRevisionModel, revision_id)
        assert persisted is not None
        assert revision is not None
        assert persisted.employee_id == seed.employee_id
        assert persisted.salary_revision_id == revision.salary_revision_id
        assert persisted.effective_from == date(2100, 1, 1)
        assert persisted.effective_to == date(2100, 12, 31)


def test_compensation_schema_enforces_existing_unique_check_and_foreign_key_constraints(
    real_mysql_payroll,
) -> None:
    from sqlalchemy.exc import DBAPIError

    from app.infrastructure.persistence.models.employee_salary_assignment import (
        EmployeeSalaryAssignmentModel,
    )
    from app.infrastructure.persistence.models.salary_component import SalaryComponentModel
    from app.infrastructure.persistence.models.salary_revision import SalaryRevisionModel
    from app.infrastructure.persistence.models.salary_revision_component import (
        SalaryRevisionComponentModel,
    )
    from app.infrastructure.persistence.models.salary_structure import SalaryStructureModel

    engine, seed = real_mysql_payroll
    marker = uuid4().hex[:16]
    with Session(engine) as session:
        existing_structure = session.get(SalaryStructureModel, seed.salary_structure_id)
        existing_component = session.get(SalaryComponentModel, seed.salary_component_id)
        assert existing_structure is not None
        assert existing_component is not None

        def assert_rejected_by_mysql(record, expected_error_code: int) -> None:
            with pytest.raises(DBAPIError) as error:
                with session.begin_nested():
                    session.add(record)
                    session.flush()
            assert error.value.orig.args[0] == expected_error_code

        assert_rejected_by_mysql(
            SalaryStructureModel(
                structure_code=existing_structure.structure_code,
                structure_name=f"Duplicate structure {marker}",
                status="ACTIVE",
            ),
            1062,
        )
        assert_rejected_by_mysql(
            SalaryComponentModel(
                component_code=existing_component.component_code,
                component_name=f"Duplicate component {marker}",
                component_type="EARNING",
                status="ACTIVE",
            ),
            1062,
        )
        assert_rejected_by_mysql(
            SalaryRevisionModel(
                salary_structure_id=seed.salary_structure_id,
                revision_number=1,
                effective_from=date(2000, 1, 1),
                effective_to=date(2099, 12, 31),
            ),
            1062,
        )
        assert_rejected_by_mysql(
            SalaryStructureModel(
                structure_code=f"IT{marker}",
                structure_name=f"Invalid status {marker}",
                status="INVALID",
            ),
            3819,
        )
        assert_rejected_by_mysql(
            SalaryComponentModel(
                component_code=f"IT{marker}",
                component_name=f"Invalid type {marker}",
                component_type="INVALID",
                status="ACTIVE",
            ),
            3819,
        )
        assert_rejected_by_mysql(
            SalaryRevisionModel(
                salary_structure_id=seed.salary_structure_id,
                revision_number=2,
                effective_from=date(2100, 1, 2),
                effective_to=date(2100, 1, 1),
            ),
            3819,
        )
        assert_rejected_by_mysql(
            EmployeeSalaryAssignmentModel(
                employee_id=seed.employee_id,
                salary_revision_id=seed.salary_revision_id,
                effective_from=date(2100, 1, 2),
                effective_to=date(2100, 1, 1),
            ),
            3819,
        )
        assert_rejected_by_mysql(
            EmployeeSalaryAssignmentModel(
                employee_id=9_223_372_036_854_770_000,
                salary_revision_id=seed.salary_revision_id,
                effective_from=date(2100, 1, 1),
                effective_to=date(2100, 12, 31),
            ),
            1452,
        )

        component = SalaryComponentModel(
            component_code=f"ITC{marker}",
            component_name=f"Constraint component {marker}",
            component_type="EARNING",
            status="ACTIVE",
        )
        session.add(component)
        session.flush()
        seed.extra_salary_component_ids += (component.salary_component_id,)
        assert_rejected_by_mysql(
            SalaryRevisionComponentModel(
                salary_revision_id=seed.salary_revision_id,
                salary_component_id=seed.salary_component_id,
                calculation_type="FIXED",
                fixed_amount=Decimal("5000.00"),
                percentage_value=None,
                base_component_id=None,
                is_overtime_base=True,
            ),
            1062,
        )
        assert_rejected_by_mysql(
            SalaryRevisionComponentModel(
                salary_revision_id=seed.salary_revision_id,
                salary_component_id=component.salary_component_id,
                calculation_type="FIXED",
                fixed_amount=None,
                percentage_value=None,
                base_component_id=None,
                is_overtime_base=False,
            ),
            3819,
        )
        session.rollback()


@dataclass(frozen=True)
class SeededLeaveReport:
    hr_user_id: int
    hr_username: str
    payroll_user_id: int
    payroll_username: str
    hr_role_id: int
    payroll_role_id: int
    department_id: int
    department_name: str
    designation_id: int
    designation_name: str
    active_employee_id: int
    terminated_employee_id: int
    leave_type_ids: tuple[int, int]
    allocation_request_pairs: tuple[tuple[int, int], ...]
    balance_ids: tuple[int, ...]
    user_ids: tuple[int, int]
    employee_ids: tuple[int, int]
    created_role_ids: tuple[int, ...]
    created_permission_ids: tuple[int, ...]
    created_role_permission_keys: tuple[tuple[int, int], ...]
    work_calendar_version_id: int


@pytest.fixture
def real_mysql_leave_report(mysql_test_engine, monkeypatch: pytest.MonkeyPatch):
    engine, _database_name = mysql_test_engine
    from app.core.config import Settings
    from app.infrastructure.database.session import SessionLocal
    from app.infrastructure.security import jwt

    previous_bind = SessionLocal.kw["bind"]
    SessionLocal.configure(bind=engine)
    monkeypatch.setattr(
        jwt,
        "settings",
        Settings.model_construct(
            database_host="127.0.0.1",
            database_port=3306,
            database_name="epms_r7_runtime_test",
            database_user="epms_ci",
            database_password="test-only-unused",
            jwt_secret_key=uuid4().hex,
            jwt_algorithm="HS256",
            access_token_expire_minutes=15,
            refresh_token_expire_days=1,
            payroll_worker_count=1,
            payroll_attempt_lease_seconds=900,
        ),
    )
    try:
        leave_seed = _seed_leave_report_data(engine)
        try:
            yield engine, leave_seed
        finally:
            _cleanup_leave_report_data(engine, leave_seed)
    finally:
        SessionLocal.configure(bind=previous_bind)


def _get_or_create_role(session: Session, role_name: str, description: str):
    from app.infrastructure.persistence.models.role import Role

    role = session.scalar(select(Role).where(Role.role_name == role_name))
    if role is not None:
        return role, False
    role = Role(role_name=role_name, description=description, is_active=True)
    session.add(role)
    session.flush()
    return role, True


def _seed_leave_report_data(engine) -> SeededLeaveReport:
    from app.infrastructure.persistence.models.department import Department
    from app.infrastructure.persistence.models.employee import Employee
    from app.infrastructure.persistence.models.leave_balance import LeaveBalanceModel
    from app.infrastructure.persistence.models.leave_request import LeaveRequestModel
    from app.infrastructure.persistence.models.leave_request_day import LeaveRequestDayModel
    from app.infrastructure.persistence.models.leave_type import LeaveTypeModel
    from app.infrastructure.persistence.models.designation import Designation
    from app.infrastructure.persistence.models.role_permission import RolePermission
    from app.infrastructure.persistence.models.user import User
    from app.infrastructure.persistence.models.user_role import UserRole
    from app.infrastructure.persistence.models.work_calendar_version import WorkCalendarVersionModel
    from app.infrastructure.persistence.models.work_calendar_weekly_rule import WorkCalendarWeeklyRuleModel
    from app.infrastructure.security.password import hash_password

    marker = uuid4().hex[:12]
    allocation_request_pairs = []
    balance_ids: list[int] = []
    created_role_ids: list[int] = []
    created_permission_ids: list[int] = []
    created_role_permission_keys: list[tuple[int, int]] = []
    with Session(engine) as session, session.begin():
        hr_role, created_hr_role = _get_or_create_role(
            session, "HR Administrator", "Administration of employee reporting."
        )
        payroll_role, created_payroll_role = _get_or_create_role(
            session, "Payroll Administrator", "Administration of payroll operations."
        )
        for role, created in ((hr_role, created_hr_role), (payroll_role, created_payroll_role)):
            if created:
                created_role_ids.append(role.role_id)

        leave_permission, created_leave_permission = _get_or_create_permission(
            session, "report.leave.read", "View organization-wide Leave reports."
        )
        leave_request_permission, created_leave_request_permission = _get_or_create_permission(
            session,
            "workforce.leave.request.create_for_others",
            "Create Leave Requests for other employees.",
        )
        leave_balance_permission, created_leave_balance_permission = _get_or_create_permission(
            session,
            "workforce.leave.balance.manage_for_others",
            "Create or adjust Leave Balances for other employees.",
        )
        payroll_permissions = [
            _get_or_create_permission(
                session, "payroll.run.read", "View payroll runs."
            ),
            _get_or_create_permission(
                session, "report.payroll.read", "View finalized payroll run summaries."
            )
        ]
        if created_leave_permission:
            created_permission_ids.append(leave_permission.permission_id)
        if created_leave_request_permission:
            created_permission_ids.append(leave_request_permission.permission_id)
        if created_leave_balance_permission:
            created_permission_ids.append(leave_balance_permission.permission_id)
        created_permission_ids.extend(
            permission.permission_id
            for permission, created in payroll_permissions
            if created
        )

        role_permission_pairs = [
            (hr_role.role_id, leave_permission.permission_id),
            (hr_role.role_id, leave_request_permission.permission_id),
            (hr_role.role_id, leave_balance_permission.permission_id),
        ] + [
            (payroll_role.role_id, permission.permission_id)
            for permission, _created in payroll_permissions
        ]
        for role_id, permission_id in role_permission_pairs:
            if session.get(RolePermission, (role_id, permission_id)) is None:
                session.add(RolePermission(role_id=role_id, permission_id=permission_id))
                created_role_permission_keys.append((role_id, permission_id))

        hr_user = User(
            username=f"leave_hr_{marker}",
            email=f"leave_hr_{marker}@example.invalid",
            password_hash=hash_password("Synthetic Leave HR integration credential"),
            status="ACTIVE",
        )
        payroll_user = User(
            username=f"leave_pay_{marker}",
            email=f"leave_pay_{marker}@example.invalid",
            password_hash=hash_password("Synthetic Payroll integration credential"),
            status="ACTIVE",
        )
        department = Department(
            department_code=f"LVD{marker}",
            department_name=f"Leave Department {marker}",
            status="ACTIVE",
        )
        designation = Designation(
            designation_code=f"LVT{marker}",
            designation_name=f"Leave Analyst {marker}",
            status="ACTIVE",
        )
        leave_types = [
            LeaveTypeModel(
                leave_type_code=f"LVA{marker}",
                leave_type_name=f"Annual {marker}",
                description="Synthetic report fixture leave type.",
                payroll_treatment="PAID",
                is_active=True,
            ),
            LeaveTypeModel(
                leave_type_code=f"LVS{marker}",
                leave_type_name=f"Special {marker}",
                description="Synthetic report fixture leave type.",
                payroll_treatment="UNPAID",
                is_active=True,
            ),
        ]
        session.add_all([hr_user, payroll_user, department, designation, *leave_types])
        session.flush()
        work_calendar = WorkCalendarVersionModel(
            version_number=2_000_000 + int(marker[:5], 16),
            effective_from=date(2000, 1, 1),
            effective_to=date(2099, 12, 31),
            time_zone="UTC",
            created_by_user_id=hr_user.user_id,
        )
        session.add(work_calendar)
        session.flush()
        session.add_all(
            [
                WorkCalendarWeeklyRuleModel(
                    work_calendar_version_id=work_calendar.work_calendar_version_id,
                    iso_weekday=weekday,
                    classification="WORKING_DAY" if weekday < 6 else "NON_WORKING_DAY",
                    scheduled_minutes=480 if weekday < 6 else 0,
                )
                for weekday in range(1, 8)
            ]
        )
        terminated_employee = Employee(
            employee_code=f"LVR{marker}",
            user_id=None,
            first_name="Terminated",
            last_name="ReportSubject",
            department_id=department.department_id,
            designation_id=designation.designation_id,
            joining_date=date(2020, 1, 1),
            employment_end_date=date(2025, 12, 31),
            employment_status="TERMINATED",
        )
        active_employee = Employee(
            employee_code=f"LVA{marker}",
            user_id=payroll_user.user_id,
            first_name="Active",
            last_name="ReportSubject",
            department_id=department.department_id,
            designation_id=designation.designation_id,
            joining_date=date(2020, 1, 1),
            employment_status="ACTIVE",
        )
        session.add_all([active_employee, terminated_employee])
        session.flush()
        session.add_all(
            [
                UserRole(
                    user_id=hr_user.user_id,
                    role_id=hr_role.role_id,
                    assigned_by_user_id=hr_user.user_id,
                ),
                UserRole(
                    user_id=payroll_user.user_id,
                    role_id=payroll_role.role_id,
                    assigned_by_user_id=payroll_user.user_id,
                ),
            ]
        )

        statuses = ("PENDING", "APPROVED", "REJECTED", "CANCELLED")
        requests: list[LeaveRequestModel] = []
        for leave_status in statuses:
            requests.append(
                LeaveRequestModel(
                    employee_id=active_employee.employee_id,
                    leave_type_id=leave_types[0].leave_type_id,
                    start_date=date(2026, 3, 10),
                    end_date=date(2026, 3, 11),
                    requested_days=Decimal("1.50"),
                    reason=f"PRIVATE_REASON_{marker}",
                    status=leave_status,
                    reviewed_by_employee_id=(
                        active_employee.employee_id
                        if leave_status in {"APPROVED", "REJECTED"}
                        else None
                    ),
                    reviewed_at=(
                        datetime(2026, 3, 1)
                        if leave_status in {"APPROVED", "REJECTED"}
                        else None
                    ),
                    review_comment=(
                        f"PRIVATE_REVIEW_{marker}"
                        if leave_status in {"APPROVED", "REJECTED"}
                        else None
                    ),
                )
            )
        requests.append(
            LeaveRequestModel(
                employee_id=terminated_employee.employee_id,
                leave_type_id=leave_types[1].leave_type_id,
                start_date=date(2026, 3, 10),
                end_date=date(2026, 3, 11),
                requested_days=Decimal("1.50"),
                reason=f"PRIVATE_REASON_{marker}",
                status="APPROVED",
                reviewed_by_employee_id=active_employee.employee_id,
                reviewed_at=datetime(2026, 3, 1),
                review_comment=f"PRIVATE_REVIEW_{marker}",
            )
        )
        session.add_all(requests)
        session.flush()

        allocations: list[LeaveRequestDayModel] = []
        for request in requests:
            for allocation_date, fraction in (
                (date(2026, 3, 10), Decimal("0.50")),
                (date(2026, 3, 11), Decimal("1.00")),
            ):
                allocation = LeaveRequestDayModel(
                    leave_request_id=request.leave_request_id,
                    leave_date=allocation_date,
                    day_fraction=fraction,
                )
                allocations.append(allocation)
                allocation_request_pairs.append((allocation, request.leave_request_id))
        session.add_all(allocations)
        balances = [
            LeaveBalanceModel(
                employee_id=active_employee.employee_id,
                leave_type_id=leave_types[0].leave_type_id,
                balance_year=2025,
                allocated_days=Decimal("10.00"),
                used_days=Decimal("2.50"),
            ),
            LeaveBalanceModel(
                employee_id=active_employee.employee_id,
                leave_type_id=leave_types[0].leave_type_id,
                balance_year=2026,
                allocated_days=Decimal("12.00"),
                used_days=Decimal("3.25"),
            ),
            LeaveBalanceModel(
                employee_id=active_employee.employee_id,
                leave_type_id=leave_types[1].leave_type_id,
                balance_year=0,
                allocated_days=Decimal("8.00"),
                used_days=Decimal("1.00"),
            ),
            LeaveBalanceModel(
                employee_id=terminated_employee.employee_id,
                leave_type_id=leave_types[1].leave_type_id,
                balance_year=2025,
                allocated_days=Decimal("5.00"),
                used_days=Decimal("1.00"),
            ),
        ]
        session.add_all(balances)
        session.flush()
        balance_ids.extend(balance.leave_balance_id for balance in balances)
        return SeededLeaveReport(
            hr_user_id=hr_user.user_id,
            hr_username=hr_user.username,
            payroll_user_id=payroll_user.user_id,
            payroll_username=payroll_user.username,
            hr_role_id=hr_role.role_id,
            payroll_role_id=payroll_role.role_id,
            department_id=department.department_id,
            department_name=department.department_name,
            designation_id=designation.designation_id,
            designation_name=designation.designation_name,
            active_employee_id=active_employee.employee_id,
            terminated_employee_id=terminated_employee.employee_id,
            leave_type_ids=(leave_types[0].leave_type_id, leave_types[1].leave_type_id),
            allocation_request_pairs=tuple(
                (allocation.leave_request_day_id, request_id)
                for allocation, request_id in allocation_request_pairs
            ),
            balance_ids=tuple(balance_ids),
            user_ids=(hr_user.user_id, payroll_user.user_id),
            employee_ids=(active_employee.employee_id, terminated_employee.employee_id),
            created_role_ids=tuple(created_role_ids),
            created_permission_ids=tuple(created_permission_ids),
            created_role_permission_keys=tuple(created_role_permission_keys),
            work_calendar_version_id=work_calendar.work_calendar_version_id,
        )


def _cleanup_leave_report_data(engine, leave_seed: SeededLeaveReport) -> None:
    from app.infrastructure.persistence.models.audit_event import AuditEventModel
    from app.infrastructure.persistence.models.audit_event_change import AuditEventChangeModel
    from app.infrastructure.persistence.models.department import Department
    from app.infrastructure.persistence.models.employee import Employee
    from app.infrastructure.persistence.models.designation import Designation
    from app.infrastructure.persistence.models.leave_balance import LeaveBalanceModel
    from app.infrastructure.persistence.models.leave_request import LeaveRequestModel
    from app.infrastructure.persistence.models.leave_request_day import LeaveRequestDayModel
    from app.infrastructure.persistence.models.leave_type import LeaveTypeModel
    from app.infrastructure.persistence.models.permission import Permission
    from app.infrastructure.persistence.models.role_permission import RolePermission
    from app.infrastructure.persistence.models.role import Role
    from app.infrastructure.persistence.models.user import User
    from app.infrastructure.persistence.models.user_role import UserRole
    from app.infrastructure.persistence.models.work_calendar_version import WorkCalendarVersionModel
    from app.infrastructure.persistence.models.work_calendar_weekly_rule import WorkCalendarWeeklyRuleModel

    with Session(engine) as session, session.begin():
        request_ids = tuple(
            session.scalars(
                select(LeaveRequestModel.leave_request_id).where(
                    LeaveRequestModel.employee_id.in_(leave_seed.employee_ids)
                )
            ).all()
        )
        allocation_ids = tuple(
            session.scalars(
                select(LeaveRequestDayModel.leave_request_day_id).where(
                    LeaveRequestDayModel.leave_request_id.in_(request_ids)
                )
            ).all()
        ) if request_ids else ()
        balance_ids = tuple(
            session.scalars(
                select(LeaveBalanceModel.leave_balance_id).where(
                    LeaveBalanceModel.employee_id.in_(leave_seed.employee_ids)
                )
            ).all()
        )
        audit_ids = tuple(
            session.scalars(
                select(AuditEventModel.audit_event_id).where(
                    AuditEventModel.actor_user_id.in_(leave_seed.user_ids),
                    AuditEventModel.action_type == "LEAVE_REQUEST_CREATED",
                    AuditEventModel.resource_type == "LEAVE_REQUEST",
                    AuditEventModel.resource_id.in_(request_ids),
                )
            ).all()
        ) if request_ids else ()
        if audit_ids:
            session.execute(
                delete(AuditEventChangeModel).where(
                    AuditEventChangeModel.audit_event_id.in_(audit_ids)
                )
            )
            session.execute(
                delete(AuditEventModel).where(
                    AuditEventModel.audit_event_id.in_(audit_ids)
                )
            )
        if allocation_ids:
            session.execute(
                delete(LeaveRequestDayModel).where(
                    LeaveRequestDayModel.leave_request_day_id.in_(allocation_ids)
                )
            )
        if request_ids:
            session.execute(
                delete(LeaveRequestModel).where(
                    LeaveRequestModel.leave_request_id.in_(request_ids)
                )
            )
        if balance_ids:
            session.execute(
                delete(LeaveBalanceModel).where(
                    LeaveBalanceModel.leave_balance_id.in_(balance_ids)
                )
            )
        session.execute(delete(Employee).where(Employee.employee_id.in_(leave_seed.employee_ids)))
        session.execute(
            delete(LeaveTypeModel).where(
                LeaveTypeModel.leave_type_id.in_(leave_seed.leave_type_ids)
            )
        )
        session.execute(
            delete(WorkCalendarWeeklyRuleModel).where(
                WorkCalendarWeeklyRuleModel.work_calendar_version_id
                == leave_seed.work_calendar_version_id
            )
        )
        session.execute(
            delete(WorkCalendarVersionModel).where(
                WorkCalendarVersionModel.work_calendar_version_id
                == leave_seed.work_calendar_version_id
            )
        )
        for role_id, permission_id in leave_seed.created_role_permission_keys:
            session.execute(
                delete(RolePermission).where(
                    RolePermission.role_id == role_id,
                    RolePermission.permission_id == permission_id,
                )
            )
        session.execute(delete(UserRole).where(UserRole.user_id.in_(leave_seed.user_ids)))
        if leave_seed.created_permission_ids:
            references = session.scalars(
                select(RolePermission.permission_id).where(
                    RolePermission.permission_id.in_(leave_seed.created_permission_ids)
                )
            ).all()
            unused_permissions = set(leave_seed.created_permission_ids) - set(references)
            if unused_permissions:
                session.execute(
                    delete(Permission).where(
                        Permission.permission_id.in_(unused_permissions)
                    )
                )
        if leave_seed.created_role_ids:
            referenced_roles = session.scalars(
                select(UserRole.role_id)
                .where(UserRole.role_id.in_(leave_seed.created_role_ids))
                .union(
                    select(RolePermission.role_id).where(
                        RolePermission.role_id.in_(leave_seed.created_role_ids)
                    )
                )
            ).all()
            unused_roles = set(leave_seed.created_role_ids) - set(referenced_roles)
            if unused_roles:
                session.execute(delete(Role).where(Role.role_id.in_(unused_roles)))
        session.execute(delete(User).where(User.user_id.in_(leave_seed.user_ids)))
        session.execute(delete(Department).where(Department.department_id == leave_seed.department_id))
        session.execute(delete(Designation).where(Designation.designation_id == leave_seed.designation_id))


def _leave_report_headers(user_id: int, username: str) -> dict[str, str]:
    from app.infrastructure.security.jwt import create_access_token

    return {"Authorization": f"Bearer {create_access_token(user_id, username)}"}


def test_leave_writes_enforce_persisted_ownership_and_hr_permissions(
    real_mysql_leave_report,
) -> None:
    engine, leave_seed = real_mysql_leave_report
    from app.infrastructure.persistence.models.permission import Permission
    from app.infrastructure.persistence.models.role_permission import RolePermission
    from app.main import app

    permission_codes = {
        "workforce.leave.request.create_for_others",
        "workforce.leave.balance.manage_for_others",
    }
    with Session(engine) as session:
        permissions = session.scalars(
            select(Permission).where(Permission.permission_code.in_(permission_codes))
        ).all()
        assert {permission.permission_code for permission in permissions} == permission_codes
        for permission in permissions:
            assert session.get(
                RolePermission, (leave_seed.hr_role_id, permission.permission_id)
            ) is not None
            assert session.get(
                RolePermission, (leave_seed.payroll_role_id, permission.permission_id)
            ) is None

    payroll_headers = _leave_report_headers(
        leave_seed.payroll_user_id, leave_seed.payroll_username
    )
    hr_headers = _leave_report_headers(leave_seed.hr_user_id, leave_seed.hr_username)
    other_employee_id = leave_seed.terminated_employee_id
    request_payload = {
        "employee_id": leave_seed.active_employee_id,
        "leave_type_id": leave_seed.leave_type_ids[0],
        "start_date": "2026-03-16",
        "end_date": "2026-03-16",
        "requested_days": "1.00",
        "allocations": [{"leave_date": "2026-03-16", "day_fraction": "1.00"}],
    }
    other_request_payload = {**request_payload, "employee_id": other_employee_id}
    balance_payload = {
        "employee_id": leave_seed.active_employee_id,
        "leave_type_id": leave_seed.leave_type_ids[0],
        "balance_year": 2030,
        "allocated_days": "10.00",
        "used_days": "0.00",
    }
    other_balance_payload = {
        **balance_payload,
        "employee_id": other_employee_id,
        "leave_type_id": leave_seed.leave_type_ids[1],
    }

    with TestClient(app, raise_server_exceptions=False) as client:
        own_request = client.post(
            "/api/v1/leave-requests", json=request_payload, headers=payroll_headers
        )
        assert own_request.status_code == 201, own_request.text
        assert own_request.json()["employee_id"] == leave_seed.active_employee_id

        payroll_cross_request = client.post(
            "/api/v1/leave-requests",
            json=other_request_payload,
            headers=payroll_headers,
        )
        assert payroll_cross_request.status_code == 403, payroll_cross_request.text

        missing_request = client.post(
            "/api/v1/leave-requests",
            json={**request_payload, "employee_id": 4_000_000_000},
            headers=payroll_headers,
        )
        assert missing_request.status_code == 409, missing_request.text
        assert "Employee does not exist" in missing_request.json()["detail"]

        hr_cross_request = client.post(
            "/api/v1/leave-requests", json=other_request_payload, headers=hr_headers
        )
        assert hr_cross_request.status_code == 201, hr_cross_request.text
        assert hr_cross_request.json()["employee_id"] == other_employee_id

        own_balance = client.post(
            "/api/v1/leave-balances", json=balance_payload, headers=payroll_headers
        )
        assert own_balance.status_code == 201, own_balance.text
        assert own_balance.json()["employee_id"] == leave_seed.active_employee_id

        payroll_cross_balance = client.post(
            "/api/v1/leave-balances",
            json=other_balance_payload,
            headers=payroll_headers,
        )
        assert payroll_cross_balance.status_code == 403, payroll_cross_balance.text

        missing_balance = client.post(
            "/api/v1/leave-balances",
            json={**balance_payload, "employee_id": 4_000_000_000},
            headers=payroll_headers,
        )
        assert missing_balance.status_code == 409, missing_balance.text
        assert "Employee does not exist" in missing_balance.json()["detail"]

        hr_cross_balance = client.post(
            "/api/v1/leave-balances",
            json=other_balance_payload,
            headers=hr_headers,
        )
        assert hr_cross_balance.status_code == 201, hr_cross_balance.text
        assert hr_cross_balance.json()["employee_id"] == other_employee_id


def test_leave_reports_use_persisted_hr_permission_and_reject_payroll_role(
    real_mysql_leave_report,
) -> None:
    engine, leave_seed = real_mysql_leave_report
    from app.infrastructure.persistence.models.audit_event import AuditEventModel
    from app.infrastructure.persistence.models.permission import Permission
    from app.infrastructure.persistence.models.role_permission import RolePermission
    from app.main import app

    with Session(engine) as session:
        permission = session.scalar(
            select(Permission).where(Permission.permission_code == "report.leave.read")
        )
        assert permission is not None
        assert session.get(
            RolePermission, (leave_seed.hr_role_id, permission.permission_id)
        ) is not None
        assert session.get(
            RolePermission, (leave_seed.payroll_role_id, permission.permission_id)
        ) is None

    hr_headers = _leave_report_headers(leave_seed.hr_user_id, leave_seed.hr_username)
    payroll_headers = _leave_report_headers(
        leave_seed.payroll_user_id, leave_seed.payroll_username
    )
    paths = (
        "/api/v1/reports/leave/allocations",
        "/api/v1/reports/leave/balances",
    )
    with TestClient(app, raise_server_exceptions=False) as client:
        for path in paths:
            assert client.get(path).status_code == 401
            denied = client.get(path, headers=payroll_headers)
            assert denied.status_code == 403, denied.text
            allowed = client.get(path, headers=hr_headers)
            assert allowed.status_code == 200, allowed.text

    with Session(engine) as session:
        assert session.scalar(
            select(func.count()).select_from(AuditEventModel).where(
                AuditEventModel.actor_user_id == leave_seed.hr_user_id
            )
        ) == 0


def test_leave_allocation_report_filters_paginates_and_preserves_allocations(
    real_mysql_leave_report,
) -> None:
    engine, leave_seed = real_mysql_leave_report
    from app.infrastructure.persistence.models.leave_request_day import LeaveRequestDayModel
    from app.main import app

    headers = _leave_report_headers(leave_seed.hr_user_id, leave_seed.hr_username)
    with Session(engine) as session:
        expected_rows = session.execute(
            select(
                LeaveRequestDayModel.leave_request_day_id,
                LeaveRequestDayModel.leave_request_id,
                LeaveRequestDayModel.leave_date,
            ).where(
                LeaveRequestDayModel.leave_request_day_id.in_(
                    [item[0] for item in leave_seed.allocation_request_pairs]
                )
            ).order_by(
                LeaveRequestDayModel.leave_date,
                LeaveRequestDayModel.leave_request_day_id,
            )
        ).all()
    expected_request_by_allocation = dict(leave_seed.allocation_request_pairs)
    response_fields = {
        "leave_request_id", "leave_request_day_id", "employee_id", "employee_code",
        "first_name", "last_name", "department_id", "department_name", "designation_id",
        "designation_name", "leave_type_id", "leave_type_name", "start_date", "end_date",
        "requested_days", "status", "leave_date", "day_fraction",
    }
    forbidden_fields = {
        "reason", "review_comment", "reviewed_by_employee_id", "password_hash", "email",
        "phone_number", "payroll_treatment", "gross_earnings", "net_salary",
    }
    with TestClient(app, raise_server_exceptions=False) as client:
        all_rows = []
        cursor = None
        while True:
            params = {"limit": 2, "date_from": "2026-03-10", "date_to": "2026-03-11"}
            if cursor:
                params["cursor"] = cursor
            page_response = client.get(
                "/api/v1/reports/leave/allocations", params=params, headers=headers
            )
            assert page_response.status_code == 200, page_response.text
            body = page_response.json()
            assert set(body) == {"allocations", "pagination"}
            for row in body["allocations"]:
                assert set(row) == response_fields
                assert forbidden_fields.isdisjoint(row)
            all_rows.extend(body["allocations"])
            cursor = body["pagination"]["next_cursor"]
            assert body["pagination"]["has_more"] == (cursor is not None)
            if cursor is None:
                break

        assert len(all_rows) == len(expected_rows)
        assert [row["leave_request_day_id"] for row in all_rows] == [row[0] for row in expected_rows]
        assert [row["leave_request_id"] for row in all_rows] == [
            expected_request_by_allocation[row[0]] for row in expected_rows
        ]
        assert {row["status"] for row in all_rows} == {
            "PENDING", "APPROVED", "REJECTED", "CANCELLED"
        }
        assert all(row["requested_days"] == "1.50" for row in all_rows)
        assert all(row["day_fraction"] in {"0.50", "1.00"} for row in all_rows)
        assert any(row["employee_id"] == leave_seed.terminated_employee_id for row in all_rows)
        assert {row["leave_date"] for row in all_rows} == {"2026-03-10", "2026-03-11"}
        assert all(row["department_name"] == leave_seed.department_name for row in all_rows)
        assert all(row["designation_name"] == leave_seed.designation_name for row in all_rows)

        same_date = client.get(
            "/api/v1/reports/leave/allocations",
            params={"date_from": "2026-03-10", "date_to": "2026-03-10", "limit": 100},
            headers=headers,
        )
        assert same_date.status_code == 200, same_date.text
        assert len(same_date.json()["allocations"]) == 5
        assert {row["leave_date"] for row in same_date.json()["allocations"]} == {"2026-03-10"}

        filters_and_counts = (
            ({"employee_id": leave_seed.terminated_employee_id}, 2),
            ({"department_id": leave_seed.department_id}, 10),
            ({"leave_type_id": leave_seed.leave_type_ids[0]}, 8),
            ({"status": "APPROVED"}, 4),
            ({"employee_id": 4_000_000_000}, 0),
        )
        for filters, expected_count in filters_and_counts:
            filtered = client.get(
                "/api/v1/reports/leave/allocations", params=filters, headers=headers
            )
            assert filtered.status_code == 200, filtered.text
            assert len(filtered.json()["allocations"]) == expected_count


def test_leave_balance_report_filters_paginates_and_returns_persisted_values(
    real_mysql_leave_report,
) -> None:
    engine, leave_seed = real_mysql_leave_report
    from app.infrastructure.persistence.models.leave_balance import LeaveBalanceModel
    from app.main import app

    headers = _leave_report_headers(leave_seed.hr_user_id, leave_seed.hr_username)
    with Session(engine) as session:
        expected_keys = session.execute(
            select(
                LeaveBalanceModel.employee_id,
                LeaveBalanceModel.leave_type_id,
                LeaveBalanceModel.balance_year,
                LeaveBalanceModel.allocated_days,
                LeaveBalanceModel.used_days,
            ).where(LeaveBalanceModel.leave_balance_id.in_(leave_seed.balance_ids)).order_by(
                LeaveBalanceModel.employee_id,
                LeaveBalanceModel.leave_type_id,
                LeaveBalanceModel.balance_year,
            )
        ).all()
    fields = {
        "employee_id", "employee_code", "first_name", "last_name", "department_id",
        "department_name", "designation_id", "designation_name", "leave_type_id",
        "leave_type_name", "balance_year", "allocated_days", "used_days",
    }
    with TestClient(app, raise_server_exceptions=False) as client:
        rows = []
        cursor = None
        while True:
            params = {"limit": 1}
            if cursor:
                params["cursor"] = cursor
            response = client.get("/api/v1/reports/leave/balances", params=params, headers=headers)
            assert response.status_code == 200, response.text
            body = response.json()
            assert set(body) == {"balances", "pagination"}
            assert all(set(row) == fields and "remaining_days" not in row for row in body["balances"])
            rows.extend(body["balances"])
            cursor = body["pagination"]["next_cursor"]
            assert body["pagination"]["has_more"] == (cursor is not None)
            if cursor is None:
                break

        assert [
            (row["employee_id"], row["leave_type_id"], row["balance_year"])
            for row in rows
        ] == [(row[0], row[1], row[2]) for row in expected_keys]
        assert [(row["allocated_days"], row["used_days"]) for row in rows] == [
            (str(row[3]), str(row[4])) for row in expected_keys
        ]
        assert rows[-1]["employee_id"] == leave_seed.terminated_employee_id
        assert rows[0]["department_name"] == leave_seed.department_name
        assert rows[0]["designation_name"] == leave_seed.designation_name

        filters_and_counts = (
            ({"employee_id": leave_seed.terminated_employee_id}, 1),
            ({"department_id": leave_seed.department_id}, 4),
            ({"leave_type_id": leave_seed.leave_type_ids[0]}, 2),
            ({"balance_year": 0}, 1),
            ({"employee_id": 4_000_000_000}, 0),
        )
        for filters, expected_count in filters_and_counts:
            filtered = client.get(
                "/api/v1/reports/leave/balances", params=filters, headers=headers
            )
            assert filtered.status_code == 200, filtered.text
            assert len(filtered.json()["balances"]) == expected_count


def test_leave_allocation_report_rejects_invalid_cursors_and_parameters(
    real_mysql_leave_report,
) -> None:
    _engine, leave_seed = real_mysql_leave_report
    from app.main import app

    headers = _leave_report_headers(leave_seed.hr_user_id, leave_seed.hr_username)
    with TestClient(app, raise_server_exceptions=False) as client:
        first = client.get(
            "/api/v1/reports/leave/allocations", params={"limit": 1}, headers=headers
        )
        assert first.status_code == 200, first.text
        cursor = first.json()["pagination"]["next_cursor"]
        assert cursor
        altered = cursor[:-1] + ("A" if cursor[-1] != "A" else "B")
        invalid_queries = (
            {"cursor": "malformed"},
            {"cursor": altered},
            {"cursor": cursor, "employee_id": leave_seed.terminated_employee_id},
            {"date_from": "2026-03-11", "date_to": "2026-03-10"},
            {"status": "UNKNOWN"},
            {"employee_id": 0},
            {"limit": 101},
        )
        for params in invalid_queries:
            response = client.get(
                "/api/v1/reports/leave/allocations", params=params, headers=headers
            )
            assert response.status_code == 422, (params, response.text)
            assert cursor not in response.text
            assert "signature" not in response.text.lower()


def test_leave_balance_report_rejects_invalid_cursors_and_parameters(
    real_mysql_leave_report,
) -> None:
    _engine, leave_seed = real_mysql_leave_report
    from app.main import app

    headers = _leave_report_headers(leave_seed.hr_user_id, leave_seed.hr_username)
    with TestClient(app, raise_server_exceptions=False) as client:
        first = client.get(
            "/api/v1/reports/leave/balances", params={"limit": 1}, headers=headers
        )
        assert first.status_code == 200, first.text
        cursor = first.json()["pagination"]["next_cursor"]
        assert cursor
        altered = cursor[:-1] + ("A" if cursor[-1] != "A" else "B")
        invalid_queries = (
            {"cursor": "malformed"},
            {"cursor": altered},
            {"cursor": cursor, "balance_year": 2026},
            {"cursor": cursor},
            {"balance_year": 65536},
            {"leave_type_id": 0},
            {"limit": 0},
        )
        for params in invalid_queries:
            path = "/api/v1/reports/leave/allocations" if params == {"cursor": cursor} else "/api/v1/reports/leave/balances"
            response = client.get(path, params=params, headers=headers)
            assert response.status_code == 422, (path, params, response.text)
            assert cursor not in response.text
            assert "signature" not in response.text.lower()


def _recover_request(seed: SeededPayroll, *, user_id: int | None = None, username: str | None = None):
    from app.infrastructure.security.jwt import create_access_token
    from app.main import app

    token = create_access_token(
        user_id if user_id is not None else seed.user_id,
        username if username is not None else seed.username,
    )
    with TestClient(app, raise_server_exceptions=False) as client:
        return client.post(
            f"/api/v1/payroll/runs/{seed.payroll_run_id}/recover",
            headers={"Authorization": f"Bearer {token}"},
        )


def _expire_attempt_for_recovery(engine, seed: SeededPayroll, attempt_number: int = 2) -> None:
    from app.infrastructure.persistence.models.payroll_run import PayrollRunModel

    with Session(engine) as session:
        run = session.get(PayrollRunModel, seed.payroll_run_id)
        assert run is not None
        run.status = "PROCESSING"
        run.attempt_number = attempt_number
        run.attempt_lease_expires_at = datetime(2000, 1, 1)
        session.commit()


def test_expired_attempt_recovery_audits_and_retry_starts_next_fenced_attempt(
    real_mysql_payroll,
) -> None:
    engine, seed = real_mysql_payroll
    from app.infrastructure.persistence.models.audit_event import AuditEventModel
    from app.infrastructure.persistence.models.audit_event_change import AuditEventChangeModel
    from app.infrastructure.persistence.models.payroll_run import PayrollRunModel
    from app.infrastructure.persistence.repositories.payroll_run_repository import PayrollRunRepository

    _expire_attempt_for_recovery(engine, seed)
    response = _recover_request(seed)
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "FAILED"
    with Session(engine) as session:
        run = session.get(PayrollRunModel, seed.payroll_run_id)
        event = session.scalar(
            select(AuditEventModel).where(
                AuditEventModel.action_type == "PAYROLL_RUN_ATTEMPT_RECOVERED",
                AuditEventModel.resource_id == seed.payroll_run_id,
            )
        )
        assert run is not None
        assert run.status == "FAILED" and run.attempt_number == 2
        assert run.attempt_lease_expires_at is None
        assert event is not None and event.actor_user_id == seed.user_id
        assert event.correlation_id == response.headers["X-Request-ID"]
        assert event.occurred_at is not None
        changes = session.scalars(
            select(AuditEventChangeModel).where(
                AuditEventChangeModel.audit_event_id == event.audit_event_id
            )
        ).all()
        assert {change.field_name: (change.old_value, change.new_value) for change in changes} == {
            "payroll_run_id": (None, str(seed.payroll_run_id)),
            "attempt_number": (None, "2"),
            "status": ("PROCESSING", "FAILED"),
            "attempt_lease_expires_at": ("2000-01-01T00:00:00", None),
        }
    from app.infrastructure.security.jwt import create_access_token
    from app.main import app

    token = create_access_token(seed.user_id, seed.username)
    with TestClient(app, raise_server_exceptions=False) as client:
        retry = client.post(
            f"/api/v1/payroll/runs/{seed.payroll_run_id}/retry",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert retry.status_code == 200, retry.text
    assert retry.json()["status"] == "PROCESSING"
    with Session(engine) as session:
        run = session.get(PayrollRunModel, seed.payroll_run_id)
        assert run is not None and run.attempt_number == 3
        assert PayrollRunRepository(session).lock_active_attempt(seed.payroll_run_id, 2) is None


def test_recovery_rejects_missing_wrong_state_and_unexpired_attempt(real_mysql_payroll) -> None:
    engine, seed = real_mysql_payroll
    from app.infrastructure.persistence.models.payroll_run import PayrollRunModel

    missing = SeededPayroll(**{**vars(seed), "payroll_run_id": seed.payroll_run_id + 999999})
    assert _recover_request(missing).status_code == 404
    assert _recover_request(seed).status_code == 409
    with Session(engine) as session:
        run = session.get(PayrollRunModel, seed.payroll_run_id)
        assert run is not None
        run.status = "PROCESSING"
        run.attempt_number = 1
        run.attempt_lease_expires_at = datetime(2999, 1, 1)
        session.commit()
    response = _recover_request(seed)
    assert response.status_code == 409
    with Session(engine) as session:
        run = session.get(PayrollRunModel, seed.payroll_run_id)
        assert run is not None
        assert run.status == "PROCESSING" and run.attempt_number == 1
        assert run.attempt_lease_expires_at == datetime(2999, 1, 1)


def test_concurrent_expired_attempt_recovery_has_one_winner(real_mysql_payroll) -> None:
    engine, seed = real_mysql_payroll
    from app.infrastructure.persistence.models.audit_event import AuditEventModel

    _expire_attempt_for_recovery(engine, seed)
    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(lambda _index: _recover_request(seed), range(2)))
    assert sorted(response.status_code for response in responses) == [200, 409]
    with Session(engine) as session:
        assert session.scalar(
            select(func.count(AuditEventModel.audit_event_id)).where(
                AuditEventModel.action_type == "PAYROLL_RUN_ATTEMPT_RECOVERED",
                AuditEventModel.resource_id == seed.payroll_run_id,
            )
        ) == 1


def test_recovery_and_audit_roll_back_together_on_audit_failure(
    real_mysql_payroll, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine, seed = real_mysql_payroll
    from app.infrastructure.persistence.models.audit_event import AuditEventModel
    from app.infrastructure.persistence.models.payroll_run import PayrollRunModel
    from app.infrastructure.persistence.repositories.audit_event_repository import AuditEventRepository

    _expire_attempt_for_recovery(engine, seed)
    original_add = AuditEventRepository.add

    def fail_recovery_audit(repository, event, changes=()):
        if event.action_type == "PAYROLL_RUN_ATTEMPT_RECOVERED":
            raise RuntimeError("controlled recovery audit failure")
        return original_add(repository, event, changes)

    monkeypatch.setattr(AuditEventRepository, "add", fail_recovery_audit)
    response = _recover_request(seed)
    assert response.status_code == 500
    with Session(engine) as session:
        run = session.get(PayrollRunModel, seed.payroll_run_id)
        audit = session.scalar(
            select(AuditEventModel).where(
                AuditEventModel.action_type == "PAYROLL_RUN_ATTEMPT_RECOVERED",
                AuditEventModel.resource_id == seed.payroll_run_id,
            )
        )
        assert run is not None
        assert run.status == "PROCESSING" and run.attempt_number == 2
        assert run.attempt_lease_expires_at is not None
        assert audit is None


def test_recovery_requires_persisted_permission(real_mysql_payroll) -> None:
    engine, seed = real_mysql_payroll
    from app.infrastructure.persistence.models.role import Role
    from app.infrastructure.persistence.models.user import User
    from app.infrastructure.persistence.models.user_role import UserRole
    from app.infrastructure.security.password import hash_password

    _expire_attempt_for_recovery(engine, seed)
    username = f"r6_no_recover_{uuid4().hex[:12]}"
    with Session(engine) as session:
        hr_role = session.scalar(select(Role).where(Role.role_name == "HR Administrator"))
        assert hr_role is not None
        user = User(
            username=username,
            email=f"{username}@example.invalid",
            password_hash=hash_password("synthetic integration-only password"),
            status="ACTIVE",
        )
        session.add(user)
        session.flush()
        session.add(UserRole(user_id=user.user_id, role_id=hr_role.role_id, assigned_by_user_id=seed.user_id))
        session.commit()
        user_id = user.user_id
        seed.extra_users += ((user_id, username),)

    response = _recover_request(seed, user_id=user_id, username=username)
    assert response.status_code == 403


def _login_refresh(engine, seed) -> dict[str, str]:
    from app.main import app

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/api/v1/auth/login",
            json={"username": seed.username, "password": seed.password},
        )
    assert response.status_code == 200, response.text
    return response.json()


def _post_refresh(token: str):
    from app.main import app

    with TestClient(app, raise_server_exceptions=False) as client:
        return client.post("/api/v1/auth/refresh", json={"refresh_token": token})


def test_login_persists_only_hash_and_returns_configured_refresh_credential(
    real_mysql_payroll,
) -> None:
    engine, seed = real_mysql_payroll
    from app.core.config import get_settings
    from app.infrastructure.persistence.models.refresh_token import RefreshToken
    from app.infrastructure.security.refresh_token import hash_refresh_token

    response = _login_refresh(engine, seed)
    with Session(engine) as session:
        row = session.scalar(
            select(RefreshToken).where(RefreshToken.user_id == seed.user_id)
        )
        assert row is not None
        assert row.token_hash == hash_refresh_token(response["refresh_token"])
        assert response["refresh_token"] not in row.token_hash
        lifetime = row.expires_at - row.created_at
        configured_lifetime = timedelta(days=get_settings().refresh_token_expire_days)
        assert configured_lifetime - timedelta(seconds=1) <= lifetime <= configured_lifetime
        assert row.family_id
    assert set(response) == {"access_token", "refresh_token", "token_type"}


def test_refresh_rotation_replay_revokes_only_its_family(real_mysql_payroll) -> None:
    engine, seed = real_mysql_payroll
    from app.infrastructure.persistence.models.refresh_token import RefreshToken
    from app.infrastructure.security.refresh_token import hash_refresh_token

    first_login = _login_refresh(engine, seed)
    other_login = _login_refresh(engine, seed)
    with Session(engine) as session:
        first_row = session.scalar(select(RefreshToken).where(
            RefreshToken.token_hash == hash_refresh_token(first_login["refresh_token"])
        ))
        other_row = session.scalar(select(RefreshToken).where(
            RefreshToken.token_hash == hash_refresh_token(other_login["refresh_token"])
        ))
        assert first_row is not None and other_row is not None
        first_family, other_family = first_row.family_id, other_row.family_id
    rotated = _post_refresh(first_login["refresh_token"])
    assert rotated.status_code == 200, rotated.text
    replay = _post_refresh(first_login["refresh_token"])
    assert replay.status_code == 401
    assert replay.json() == {"detail": "Invalid or expired refresh token."}
    other_session_rotation = _post_refresh(other_login["refresh_token"])
    assert other_session_rotation.status_code == 200, other_session_rotation.text

    with Session(engine) as session:
        rows = list(session.scalars(select(RefreshToken).where(RefreshToken.user_id == seed.user_id)))
        first_family_rows = [row for row in rows if row.family_id == first_family]
        other_family_rows = [row for row in rows if row.family_id == other_family]
        assert len(first_family_rows) == 2
        assert all(row.revoked_at is not None for row in first_family_rows)
        assert len(other_family_rows) == 2
        assert sum(row.revoked_at is None for row in other_family_rows) == 1


def test_refresh_invalid_expired_and_revoked_credentials_share_401(
    real_mysql_payroll,
) -> None:
    engine, seed = real_mysql_payroll
    from app.infrastructure.persistence.models.refresh_token import RefreshToken
    from app.infrastructure.security.refresh_token import hash_refresh_token

    expired_login = _login_refresh(engine, seed)
    revoked_login = _login_refresh(engine, seed)
    with Session(engine) as session:
        expired = session.scalar(select(RefreshToken).where(
            RefreshToken.token_hash == hash_refresh_token(expired_login["refresh_token"])
        ))
        assert expired is not None
        revoked = session.scalar(
            select(RefreshToken).where(RefreshToken.user_id == seed.user_id)
            .where(RefreshToken.family_id != expired.family_id)
        )
        assert revoked is not None
        expired.expires_at = datetime(2000, 1, 1)
        revoked.revoked_at = datetime.now()
        session.commit()

    responses = [
        _post_refresh("unknown-invalid-token"),
        _post_refresh(expired_login["refresh_token"]),
        _post_refresh(revoked_login["refresh_token"]),
    ]
    assert [response.status_code for response in responses] == [401, 401, 401]
    assert {response.text for response in responses} == {
        '{"detail":"Invalid or expired refresh token."}'
    }


def test_concurrent_refresh_use_has_at_most_one_success(real_mysql_payroll) -> None:
    engine, seed = real_mysql_payroll
    credential = _login_refresh(engine, seed)["refresh_token"]
    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(lambda _index: _post_refresh(credential), range(2)))
    assert sorted(response.status_code for response in responses) == [200, 401]


def test_logout_is_idempotent_and_session_scoped(real_mysql_payroll) -> None:
    from app.main import app

    engine, seed = real_mysql_payroll
    first = _login_refresh(engine, seed)["refresh_token"]
    other = _login_refresh(engine, seed)["refresh_token"]
    with TestClient(app, raise_server_exceptions=False) as client:
        logged_out = client.post("/api/v1/auth/logout", json={"refresh_token": first})
        repeated = client.post("/api/v1/auth/logout", json={"refresh_token": first})
    assert logged_out.status_code == repeated.status_code == 204
    assert _post_refresh(first).status_code == 401
    assert _post_refresh(other).status_code == 200


def test_refresh_rejects_inactive_user_and_revokes_family(real_mysql_payroll) -> None:
    engine, seed = real_mysql_payroll
    credential = _login_refresh(engine, seed)["refresh_token"]
    from app.infrastructure.persistence.models.refresh_token import RefreshToken
    from app.infrastructure.persistence.models.user import User
    from app.infrastructure.security.refresh_token import hash_refresh_token

    with Session(engine) as session:
        user = session.get(User, seed.user_id)
        row = session.scalar(select(RefreshToken).where(
            RefreshToken.token_hash == hash_refresh_token(credential)
        ))
        assert user is not None and row is not None
        family_id = row.family_id
        user.status = "DISABLED"
        session.commit()

    response = _post_refresh(credential)
    assert response.status_code == 401
    with Session(engine) as session:
        family_rows = list(session.scalars(select(RefreshToken).where(
            RefreshToken.family_id == family_id
        )))
        assert family_rows and all(row.revoked_at is not None for row in family_rows)


def test_refresh_rotation_rolls_back_if_replacement_insert_fails(
    real_mysql_payroll, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine, seed = real_mysql_payroll
    credential = _login_refresh(engine, seed)["refresh_token"]
    from app.infrastructure.persistence.models.refresh_token import RefreshToken
    from app.infrastructure.persistence.repositories.refresh_token_repository import (
        RefreshTokenRepository,
    )
    from app.infrastructure.security.refresh_token import hash_refresh_token

    original_add = RefreshTokenRepository.add

    def fail_replacement(repository, row):
        raise RuntimeError("controlled replacement persistence failure")

    monkeypatch.setattr(RefreshTokenRepository, "add", fail_replacement)
    response = _post_refresh(credential)
    assert response.status_code == 500
    monkeypatch.setattr(RefreshTokenRepository, "add", original_add)
    with Session(engine) as session:
        row = session.scalar(select(RefreshToken).where(
            RefreshToken.token_hash == hash_refresh_token(credential)
        ))
        assert row is not None and row.revoked_at is None
        family_rows = list(session.scalars(select(RefreshToken).where(
            RefreshToken.family_id == row.family_id
        )))
        assert len(family_rows) == 1


def test_logout_family_revocation_rolls_back_on_commit_failure(
    real_mysql_payroll, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine, seed = real_mysql_payroll
    credential = _login_refresh(engine, seed)["refresh_token"]
    from app.infrastructure.persistence.models.refresh_token import RefreshToken
    from app.infrastructure.security.refresh_token import hash_refresh_token
    from app.infrastructure.database.unit_of_work import SQLAlchemyUnitOfWork
    from app.main import app

    with Session(engine) as session:
        row = session.scalar(select(RefreshToken).where(
            RefreshToken.token_hash == hash_refresh_token(credential)
        ))
        assert row is not None
        family_id = row.family_id

    original_commit = SQLAlchemyUnitOfWork.commit

    def fail_commit(uow):
        raise RuntimeError("controlled logout commit failure")

    monkeypatch.setattr(SQLAlchemyUnitOfWork, "commit", fail_commit)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/api/v1/auth/logout", json={"refresh_token": credential})
    assert response.status_code == 500
    monkeypatch.setattr(SQLAlchemyUnitOfWork, "commit", original_commit)

    with Session(engine) as session:
        family_rows = list(session.scalars(select(RefreshToken).where(
            RefreshToken.family_id == family_id
        )))
        assert len(family_rows) == 1
        assert family_rows[0].revoked_at is None
