from sqlalchemy import (
    ForeignKey,
    Index,
    Integer,
    PrimaryKeyConstraint,
    String,
    Text,
)
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.models.base import Base


_UNSIGNED_BIGINT = Integer().with_variant(mysql.BIGINT(unsigned=True), "mysql")


class AuditEventChangeModel(Base):
    __tablename__ = "audit_event_changes"
    __table_args__ = (
        PrimaryKeyConstraint(
            "audit_event_change_id", name="pk_audit_event_changes"
        ),
        Index("idx_audit_changes_event", "audit_event_id"),
    )

    audit_event_change_id: Mapped[int] = mapped_column(
        _UNSIGNED_BIGINT, autoincrement=True
    )
    audit_event_id: Mapped[int] = mapped_column(
        _UNSIGNED_BIGINT,
        ForeignKey(
            "audit_events.audit_event_id",
            name="fk_audit_change_event",
            ondelete="CASCADE",
            onupdate="RESTRICT",
        ),
        nullable=False,
    )
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
