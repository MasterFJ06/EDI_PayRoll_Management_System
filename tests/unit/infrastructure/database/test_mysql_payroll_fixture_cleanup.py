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
