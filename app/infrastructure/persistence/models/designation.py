from datetime import datetime

from sqlalchemy import DateTime, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.models.base import Base


class Designation(Base):
    """SQLAlchemy model for employee designations."""

    __tablename__ = "designations"

    __table_args__ = (
        UniqueConstraint("designation_code", name="uq_designations_code"),
        UniqueConstraint("designation_name", name="uq_designations_name"),
    )

    designation_id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    designation_code: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    designation_name: Mapped[str] = mapped_column(
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