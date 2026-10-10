from unittest.mock import Mock

from sqlalchemy.dialects import mysql

from app.infrastructure.persistence.models.audit_event import AuditEventModel
from app.infrastructure.persistence.models.audit_event_change import AuditEventChangeModel
from app.infrastructure.persistence.models.permission import Permission
from tests.integration.test_mysql_payroll_processing import (
    _delete_owned_audit_events,
    _get_or_create_permission,
)


def test_owned_audit_cleanup_selects_fixture_rows_and_deletes_children_first() -> None:
    session = Mock()
    session.scalars.return_value.all.return_value = [71, 72, 73]

    audit_ids = _delete_owned_audit_events(
        session,
        AuditEventModel,
        AuditEventChangeModel,
        payroll_run_id=20,
        payslip_ids=[30],
        actor_user_id=12,
    )

    assert audit_ids == [71, 72, 73]
    selection = session.scalars.call_args.args[0]
    sql = str(selection.compile(dialect=mysql.dialect(), compile_kwargs={"literal_binds": True}))
    assert "audit_events.actor_user_id = 12" in sql
    assert "audit_events.resource_type = 'PAYROLL_RUN'" in sql
    assert "audit_events.resource_type = 'PAYSLIP'" in sql
    assert " OR " in sql

    deletes = [str(call.args[0].compile(dialect=mysql.dialect())) for call in session.execute.call_args_list]
    assert "DELETE FROM audit_event_changes" in deletes[0]
    assert "DELETE FROM audit_events" in deletes[1]


def test_permission_seeding_reuses_existing_shared_permission() -> None:
    session = Mock()
    existing = Permission(permission_code="payroll.run.process", description="seeded")
    session.scalar.return_value = existing

    permission, created = _get_or_create_permission(
        session, "payroll.run.process", "integration test"
    )

    assert permission is existing
    assert created is False
    session.add.assert_not_called()
    session.flush.assert_not_called()


def test_permission_seeding_marks_only_new_permission_as_fixture_owned() -> None:
    session = Mock()
    session.scalar.return_value = None

    permission, created = _get_or_create_permission(
        session, "payroll.payslip.create", "integration test"
    )

    assert isinstance(permission, Permission)
    assert permission.permission_code == "payroll.payslip.create"
    assert created is True
    session.add.assert_called_once_with(permission)
    session.flush.assert_called_once_with()
