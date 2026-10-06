from sqlalchemy.dialects import mysql

from app.infrastructure.persistence.models.audit_event import AuditEventModel
from app.infrastructure.persistence.models.audit_event_change import (
    AuditEventChangeModel,
)


def test_audit_models_match_authoritative_mysql_schema() -> None:
    event = AuditEventModel.__table__
    change = AuditEventChangeModel.__table__

    assert set(event.columns.keys()) == {
        "audit_event_id",
        "actor_user_id",
        "action_type",
        "resource_type",
        "resource_id",
        "correlation_id",
        "source_ip",
        "user_agent",
        "occurred_at",
    }
    assert set(change.columns.keys()) == {
        "audit_event_change_id",
        "audit_event_id",
        "field_name",
        "old_value",
        "new_value",
    }
    for table, id_columns in (
        (event, {"audit_event_id", "actor_user_id", "resource_id"}),
        (change, {"audit_event_change_id", "audit_event_id"}),
    ):
        for column_name in id_columns:
            assert table.c[column_name].type.compile(dialect=mysql.dialect()) == (
                "BIGINT UNSIGNED"
            )
    assert {constraint.name for constraint in event.constraints} >= {
        "pk_audit_events",
        "fk_audit_actor",
    }
    assert {constraint.name for constraint in change.constraints} >= {
        "pk_audit_event_changes",
        "fk_audit_change_event",
    }
    assert {index.name for index in event.indexes} == {
        "idx_audit_resource_time",
        "idx_audit_actor_time",
        "idx_audit_occurred",
        "idx_audit_correlation",
    }
    assert {index.name for index in change.indexes} == {"idx_audit_changes_event"}
