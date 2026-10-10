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
from uuid import uuid4

import pytest
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

@dataclass
class SeededPayroll:
    user_id: int
    username: str
    employee_id: int
    department_id: int
    designation_id: int
    role_id: int
    permission_id: int
    finalize_permission_id: int
    payslip_permission_id: int
    created_permission_ids: tuple[int, ...]
    salary_structure_id: int
    salary_component_id: int
    salary_revision_id: int
    salary_assignment_id: int
    calendar_version_id: int
    policy_version_id: int
    payroll_run_id: int
    correlation_id: str


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
            refresh_token_expire_days=1,
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
        role = Role(role_name=f"R6 Test Payroll {marker}", is_active=True)
        permission, created_permission = _get_or_create_permission(
            session, "payroll.run.process", "R6 test"
        )
        finalize_permission, created_finalize_permission = _get_or_create_permission(
            session, "payroll.run.finalize", "R7 test"
        )
        payslip_permission, created_payslip_permission = _get_or_create_permission(
            session, "payroll.payslip.create", "R8 test"
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
        session.add_all([user, role, department, designation, structure, component])
        session.flush()
        session.add_all([
            UserRole(user_id=user.user_id, role_id=role.role_id, assigned_by_user_id=user.user_id),
            RolePermission(role_id=role.role_id, permission_id=permission.permission_id),
            RolePermission(role_id=role.role_id, permission_id=finalize_permission.permission_id),
            RolePermission(role_id=role.role_id, permission_id=payslip_permission.permission_id),
        ])
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
            employee_id=employee.employee_id,
            department_id=department.department_id,
            designation_id=designation.designation_id,
            role_id=role.role_id,
            permission_id=permission.permission_id,
            finalize_permission_id=finalize_permission.permission_id,
            payslip_permission_id=payslip_permission.permission_id,
            created_permission_ids=tuple(
                item.permission_id
                for item, created in (
                    (permission, created_permission),
                    (finalize_permission, created_finalize_permission),
                    (payslip_permission, created_payslip_permission),
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

    with Session(engine) as session, session.begin():
        result_ids = select(PayrollResultModel.payroll_result_id).where(
            PayrollResultModel.payroll_run_id == seed.payroll_run_id
        )
        owned_payslip_ids = list(session.scalars(
            select(PayslipModel.payslip_id)
            .join(PayrollResultModel, PayslipModel.payroll_result_id == PayrollResultModel.payroll_result_id)
            .where(PayrollResultModel.payroll_run_id == seed.payroll_run_id)
        ).all())
        _delete_owned_audit_events(
            session,
            AuditEventModel,
            AuditEventChangeModel,
            seed.payroll_run_id,
            owned_payslip_ids,
            seed.user_id,
        )
        session.execute(delete(PayslipModel).where(
            PayslipModel.payslip_id.in_(owned_payslip_ids)
        ))
        session.execute(delete(PayrollResultComponentModel).where(PayrollResultComponentModel.payroll_result_id.in_(result_ids)))
        session.execute(delete(PayrollResultModel).where(PayrollResultModel.payroll_run_id == seed.payroll_run_id))
        session.execute(delete(PayrollProcessingIssueModel).where(PayrollProcessingIssueModel.payroll_run_id == seed.payroll_run_id))
        session.execute(delete(PayrollRunWorkforceSnapshotModel).where(PayrollRunWorkforceSnapshotModel.payroll_run_id == seed.payroll_run_id))
        session.execute(delete(AttendanceRecord).where(AttendanceRecord.employee_id == seed.employee_id))
        session.execute(delete(EmployeeSalaryAssignmentModel).where(EmployeeSalaryAssignmentModel.salary_assignment_id == seed.salary_assignment_id))
        session.execute(delete(SalaryRevisionComponentModel).where(SalaryRevisionComponentModel.salary_revision_id == seed.salary_revision_id))
        session.execute(delete(SalaryRevisionModel).where(SalaryRevisionModel.salary_revision_id == seed.salary_revision_id))
        session.execute(delete(SalaryStructureModel).where(SalaryStructureModel.salary_structure_id == seed.salary_structure_id))
        session.execute(delete(SalaryComponentModel).where(SalaryComponentModel.salary_component_id == seed.salary_component_id))
        session.execute(delete(WorkCalendarWeeklyRuleModel).where(WorkCalendarWeeklyRuleModel.work_calendar_version_id == seed.calendar_version_id))
        session.execute(delete(WorkCalendarVersionModel).where(WorkCalendarVersionModel.work_calendar_version_id == seed.calendar_version_id))
        session.execute(delete(WorkforceOvertimePolicyVersionModel).where(WorkforceOvertimePolicyVersionModel.workforce_overtime_policy_version_id == seed.policy_version_id))
        session.execute(delete(PayrollRunModel).where(PayrollRunModel.payroll_run_id == seed.payroll_run_id))
        session.execute(delete(Employee).where(Employee.employee_id == seed.employee_id))
        session.execute(delete(Department).where(Department.department_id == seed.department_id))
        session.execute(delete(Designation).where(Designation.designation_id == seed.designation_id))
        session.execute(delete(RolePermission).where(RolePermission.role_id == seed.role_id))
        session.execute(delete(UserRole).where(UserRole.user_id == seed.user_id))
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
        session.execute(delete(Role).where(Role.role_id == seed.role_id))
        session.execute(delete(User).where(User.user_id == seed.user_id))


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
