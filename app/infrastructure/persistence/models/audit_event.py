from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, PrimaryKeyConstraint, String, text
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.models.base import Base


_UNSIGNED_BIGINT = Integer().with_variant(mysql.BIGINT(unsigned=True), "mysql")


class AuditEventModel(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        PrimaryKeyConstraint("audit_event_id", name="pk_audit_events"),
        Index("idx_audit_resource_time", "resource_type", "resource_id", "occurred_at"),
        Index("idx_audit_actor_time", "actor_user_id", "occurred_at"),
        Index("idx_audit_occurred", "occurred_at"),
        Index("idx_audit_correlation", "correlation_id"),
    )

    audit_event_id: Mapped[int] = mapped_column(
        _UNSIGNED_BIGINT, autoincrement=True
    )
    actor_user_id: Mapped[int | None] = mapped_column(
        _UNSIGNED_BIGINT,
        ForeignKey(
            "users.user_id",
            name="fk_audit_actor",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        nullable=True,
    )
    action_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[int | None] = mapped_column(_UNSIGNED_BIGINT, nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
