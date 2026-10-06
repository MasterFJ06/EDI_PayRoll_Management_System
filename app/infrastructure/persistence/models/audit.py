from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.models.base import Base


class AuditEvent(Base):
    """SQLAlchemy model for recorded system audit events."""

    __tablename__ = "audit_events"

    audit_event_id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    actor_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.user_id"),
        nullable=True,
    )

    action_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    resource_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    resource_id: Mapped[int | None] = mapped_column(
        nullable=True,
    )

    correlation_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    source_ip: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
    )

    user_agent: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class AuditEventChange(Base):
    """SQLAlchemy model for field changes associated with an audit event."""

    __tablename__ = "audit_event_changes"

    audit_event_change_id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    audit_event_id: Mapped[int] = mapped_column(
        ForeignKey("audit_events.audit_event_id", ondelete="CASCADE"),
        nullable=False,
    )

    field_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    old_value: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    new_value: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
