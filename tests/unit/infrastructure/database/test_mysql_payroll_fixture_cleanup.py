from __future__ import annotations

from pathlib import Path

from sqlalchemy.dialects import mysql

from app.infrastructure.persistence.models.audit_event import AuditEventModel
from app.infrastructure.persistence.models.audit_event_change import AuditEventChangeModel
from tests.integration.test_mysql_payroll_processing import _delete_owned_audit_events


def test_runtime_workflow_leaves_rbac_seeding_to_the_integration_fixture() -> None:
    repository_root = Path(__file__).resolve().parents[4]
    workflow = (repository_root / ".github/workflows/mysql-payroll-runtime.yml").read_text(
        encoding="utf-8"
    )
    fixture = (repository_root / "tests/integration/test_mysql_payroll_processing.py").read_text(
        encoding="utf-8"
    )
    schema_guard = (repository_root / "tests/integration/mysql_support.py").read_text(
        encoding="utf-8"
    )
    production_seed = (repository_root / "database/seed.sql").read_text(
        encoding="utf-8"
    )

    assert "< \"$EPMS_PREPARED_SCHEMA\"" in workflow
    assert "database/seed.sql" not in workflow
    assert "_get_or_create_permission(" in fixture
    assert "_verify_schema_state(connection, prepared_schema)" in (
        repository_root / "tests/integration/conftest.py"
    ).read_text(encoding="utf-8")
    assert "is not empty before seeding" in schema_guard
    assert "VALUES ('HR Administrator', 'Administration of employee reporting.')" in production_seed
    assert "p.permission_code = 'report.employee.read'" in production_seed
    assert "p.permission_code = 'report.attendance.read'" in production_seed


def test_employee_report_fixture_seeds_and_cleans_only_hr_employee_read_access() -> None:
    repository_root = Path(__file__).resolve().parents[4]
    fixture = (repository_root / "tests/integration/test_mysql_payroll_processing.py").read_text(
        encoding="utf-8"
    )
    seed_body = fixture.split("def _seed_valid_payroll", maxsplit=1)[1].split(
        "def _cleanup_seed", maxsplit=1
    )[0]
    cleanup_body = fixture.split("def _cleanup_seed", maxsplit=1)[1].split(
        "def _delete_owned_audit_events", maxsplit=1
    )[0]

    assert 'select(Role).where(Role.role_name == "HR Administrator")' in seed_body
    assert '_get_or_create_permission(\n            session, "report.employee.read", "Employee report read"' in seed_body
    assert "role_id=hr_role.role_id" in seed_body
    assert "permission_id=hr_permission.permission_id" in seed_body
    assert 'role_id=role.role_id, permission_id=item.permission_id' in seed_body
    assert "created_hr_role_permission" in cleanup_body
    assert "seed.created_hr_role" in cleanup_body
    assert "session.execute(delete(UserRole).where(UserRole.user_id.in_(owned_user_ids)))" in cleanup_body
    assert "(hr_permission, created_hr_permission)" in seed_body
    assert "created_hr_attendance_role_permission" in seed_body
    assert "seed.created_hr_attendance_role_permission" in cleanup_body
    assert "seed.created_permission_ids" in cleanup_body


def test_recovery_permission_is_separate_and_seeded_for_payroll_administrator() -> None:
    repository_root = Path(__file__).resolve().parents[4]
    production_seed = (repository_root / "database/seed.sql").read_text(
        encoding="utf-8"
    )
    fixture = (repository_root / "tests/integration/test_mysql_payroll_processing.py").read_text(
        encoding="utf-8"
    )
    payroll_grant = production_seed.split(
        "WHERE r.role_name = 'Payroll Administrator';", maxsplit=1
    )[0]
    assert "('payroll.run.recover'" in production_seed
    assert "'payroll.run.recover'" in payroll_grant
    hr_grant = production_seed.split(
        "WHERE r.role_name = 'HR Administrator';", maxsplit=1
    )[0].rsplit("INSERT IGNORE INTO role_permissions", maxsplit=1)[1]
    assert "payroll.run.recover" not in hr_grant
    seed_body = fixture.split("def _seed_valid_payroll", maxsplit=1)[1].split(
        "def _cleanup_seed", maxsplit=1
    )[0]
    assert '"payroll.run.recover"' in seed_body
    assert '"payroll.run.retry"' in seed_body
    assert "seed.created_role_permission_ids" in fixture


def test_compensation_write_permission_is_granted_only_to_payroll_administrator() -> None:
    repository_root = Path(__file__).resolve().parents[4]
    production_seed = (repository_root / "database/seed.sql").read_text(
        encoding="utf-8"
    )
    fixture = (repository_root / "tests/integration/test_mysql_payroll_processing.py").read_text(
        encoding="utf-8"
    )

    assert "('compensation.write'," in production_seed
    payroll_assignment = production_seed.split(
        "WHERE r.role_name = 'Payroll Administrator';", maxsplit=1
    )[0].rsplit("INSERT IGNORE INTO role_permissions", maxsplit=1)[1]
    assert "'compensation.write'" in payroll_assignment

    role_assignments = production_seed.split("INSERT IGNORE INTO role_permissions")[1:]
    assert len(role_assignments) == 5
    hr_assignments = role_assignments[1:]
    assert all("compensation.write" not in assignment for assignment in hr_assignments)

    seed_body = fixture.split("def _seed_valid_payroll", maxsplit=1)[1].split(
        "def _cleanup_seed", maxsplit=1
    )[0]
    assert '"compensation.write"' in seed_body
    assert "seed.created_role_permission_ids" in fixture
    assert "created_permission_ids=tuple(" in seed_body


def test_leave_write_permissions_are_hr_only_and_fixture_owned() -> None:
    repository_root = Path(__file__).resolve().parents[4]
    production_seed = (repository_root / "database/seed.sql").read_text(
        encoding="utf-8"
    )
    fixture = (repository_root / "tests/integration/test_mysql_payroll_processing.py").read_text(
        encoding="utf-8"
    )
    permission_codes = (
        "workforce.leave.request.create_for_others",
        "workforce.leave.balance.manage_for_others",
    )
    assert all(f"'{code}'" in production_seed for code in permission_codes)
    grant = production_seed.rsplit(
        "WHERE r.role_name = 'HR Administrator';", maxsplit=1
    )[0].rsplit("INSERT IGNORE INTO role_permissions", maxsplit=1)[1]
    assert all(code in grant for code in permission_codes)
    payroll_grant = production_seed.split(
        "WHERE r.role_name = 'Payroll Administrator';", maxsplit=1
    )[0].rsplit("INSERT IGNORE INTO role_permissions", maxsplit=1)[1]
    assert all(code not in payroll_grant for code in permission_codes)

    seed_body = fixture.split("def _seed_leave_report_data", maxsplit=1)[1].split(
        "def _cleanup_leave_report_data", maxsplit=1
    )[0]
    cleanup_body = fixture.split("def _cleanup_leave_report_data", maxsplit=1)[1].split(
        "def _leave_report_headers", maxsplit=1
    )[0]
    assert all(f'"{code}"' in seed_body for code in permission_codes)
    assert "created_permission_ids.append" in seed_body
    assert "created_role_permission_keys.append" in seed_body
    assert "with Session(engine) as session, session.begin():" in cleanup_body
    assert "session.scalars(" in cleanup_body
    assert "AuditEventChangeModel" in cleanup_body
    assert cleanup_body.index("delete(AuditEventChangeModel)") < cleanup_body.index(
        "delete(AuditEventModel)"
    )
    assert cleanup_body.index("delete(LeaveRequestDayModel)") < cleanup_body.index(
        "delete(LeaveRequestModel)"
    )


class _ScalarResult:
    def __init__(self, values: list[int]) -> None:
        self.values = values

    def all(self) -> list[int]:
        return self.values


class _RecordingSession:
    def __init__(self, audit_ids: list[int]) -> None:
        self.audit_ids = audit_ids
        self.selects = []
        self.deletes = []

    def scalars(self, statement):
        self.selects.append(statement)
        return _ScalarResult(self.audit_ids)

    def execute(self, statement):
        self.deletes.append(statement)


def test_audit_cleanup_selects_owned_ids_before_delete_and_uses_concrete_ids() -> None:
    session = _RecordingSession([12, 31])

    result = _delete_owned_audit_events(
        session,
        AuditEventModel,
        AuditEventChangeModel,
        payroll_run_id=44,
    )

    assert result == [12, 31]
    assert len(session.selects) == 1
    select_statement = session.selects[0].compile(dialect=mysql.dialect())
    assert "FROM audit_events" in str(select_statement)
    assert select_statement.params == {
        "resource_type_1": "PAYROLL_RUN",
        "resource_id_1": 44,
    }

    assert len(session.deletes) == 2
    for statement in session.deletes:
        compiled = statement.compile(dialect=mysql.dialect())
        assert "DELETE FROM" in str(compiled)
        assert "SELECT" not in str(compiled)
        assert list(compiled.params.values()) == [[12, 31]]


def test_audit_cleanup_does_not_delete_when_run_has_no_owned_events() -> None:
    session = _RecordingSession([])

    result = _delete_owned_audit_events(
        session,
        AuditEventModel,
        AuditEventChangeModel,
        payroll_run_id=44,
    )

    assert result == []
    assert len(session.selects) == 1
    assert session.deletes == []
