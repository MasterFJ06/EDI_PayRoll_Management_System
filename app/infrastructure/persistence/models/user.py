from datetime import datetime

from sqlalchemy import DateTime, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.models.base import Base


class User(Base):
    """SQLAlchemy model for system user accounts."""

    __tablename__ = "users"

    __table_args__ = (
        UniqueConstraint(
            "username",
            name="uq_users_username",
        ),
        UniqueConstraint(
            "email",
            name="uq_users_email",
        ),
    )

    user_id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    username: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="ACTIVE",
    )

    created_at: Mapped[datetime] = mapped_column(
    DateTime,
    nullable=False,
    server_default=text("CURRENT_TIMESTAMP"),
    )

    updated_at: Mapped[datetime] = mapped_column(
    DateTime,
    nullable=False,
    server_default=text("CURRENT_TIMESTAMP"),
    server_onupdate=text("CURRENT_TIMESTAMP"),
    )

    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )