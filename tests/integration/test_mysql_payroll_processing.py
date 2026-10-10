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
from sqlalchemy import delete, func, select
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


def _seed_valid_payroll(engine) -> SeededPayroll:
    from app.infrastructure.persistence.models.attendance import AttendanceRecord
    from app.infrastructure.persistence.models.department import Department
    from app.infrastructure.persistence.models.designation import Designation
    from app.infrastructure.persistence.models.employee import Employee
    from app.infrastructure.persistence.models.payroll_run import PayrollRunModel
    from app.infrastructure.persistence.models.permission import Permission
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
        permission = Permission(permission_code="payroll.run.process", description="R6 test")
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
        session.add_all([user, role, permission, department, designation, structure, component])
        session.flush()
        session.add_all([
            UserRole(user_id=user.user_id, role_id=role.role_id, assigned_by_user_id=user.user_id),
            RolePermission(role_id=role.role_id, permission_id=permission.permission_id),
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
        _delete_owned_audit_events(
            session,
            AuditEventModel,
            AuditEventChangeModel,
            seed.payroll_run_id,
        )
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
        session.execute(delete(Permission).where(Permission.permission_id == seed.permission_id))
        session.execute(delete(Role).where(Role.role_id == seed.role_id))
        session.execute(delete(User).where(User.user_id == seed.user_id))


def _delete_owned_audit_events(
    session: Session,
    audit_event_model,
    audit_event_change_model,
    payroll_run_id: int,
) -> list[int]:
    """Delete this fixture run's audit rows without a MySQL self-select DELETE."""
    audit_ids = list(
        session.scalars(
            select(audit_event_model.audit_event_id).where(
                audit_event_model.resource_type == "PAYROLL_RUN",
                audit_event_model.resource_id == payroll_run_id,
            )
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
