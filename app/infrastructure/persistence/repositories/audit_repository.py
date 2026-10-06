from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.persistence.models.audit import (
    AuditEvent,
    AuditEventChange,
)


class AuditRepository:
    """Repository for audit event persistence operations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_all(self, limit: int = 200) -> list[AuditEvent]:
        statement = (
            select(AuditEvent)
            .order_by(AuditEvent.occurred_at.desc(), AuditEvent.audit_event_id.desc())
            .limit(limit)
        )
        return list(self.session.scalars(statement).all())

    def get_by_id(self, audit_event_id: int) -> AuditEvent | None:
        statement = select(AuditEvent).where(
            AuditEvent.audit_event_id == audit_event_id
        )
        return self.session.scalar(statement)

    def add(self, event: AuditEvent) -> AuditEvent:
        self.session.add(event)
        self.session.flush()
        return event

    def add_change(self, change: AuditEventChange) -> AuditEventChange:
        self.session.add(change)
        self.session.flush()
        return change

    def get_changes(self, audit_event_id: int) -> list[AuditEventChange]:
        statement = select(AuditEventChange).where(
            AuditEventChange.audit_event_id == audit_event_id
        )
        return list(self.session.scalars(statement).all())
