from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.infrastructure.persistence.models.audit_event import AuditEventModel
from app.infrastructure.persistence.models.audit_event_change import (
    AuditEventChangeModel,
)


class AuditEventRepository:
    """Persists audit events and their field changes through the shared session."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(
        self,
        event: AuditEventModel,
        changes: Sequence[AuditEventChangeModel] = (),
    ) -> AuditEventModel:
        self.session.add(event)
        self.session.flush()
        for change in changes:
            change.audit_event_id = event.audit_event_id
        self.session.add_all(changes)
        self.session.flush()
        return event
