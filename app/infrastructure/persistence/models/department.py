from datetime import datetime

from sqlalchemy import DateTime, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.models.base import Base


class Department(Base):
    """SQLAlchemy model for organizational departments."""

    __tablename__ = "departments"

    __table_args__ = (
        UniqueConstraint("department_code", name="uq_departments_code"),
        UniqueConstraint("department_name", name="uq_departments_name"),
    )

    department_id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    department_code: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    department_name: Mapped[str] = mapped_column(
        String(100),
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