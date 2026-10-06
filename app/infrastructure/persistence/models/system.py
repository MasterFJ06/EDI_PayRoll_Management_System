from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.models.base import Base


class SystemSetting(Base):
    """SQLAlchemy model for application configuration settings."""

    __tablename__ = "system_settings"

    system_setting_id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    setting_key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
    )

    setting_value: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    value_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="STRING",
    )

    description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    updated_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id"),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
    )


class SecurityEvent(Base):
    """SQLAlchemy model for security audit logs."""

    __tablename__ = "security_events"

    security_event_id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    event_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    severity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.user_id"),
        nullable=True,
    )

    ip_address: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
    )

    details: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
