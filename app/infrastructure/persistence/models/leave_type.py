from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, UniqueConstraint, text
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.models.base import Base


class LeaveTypeModel(Base):
    __tablename__ = "leave_types"
    __table_args__ = (
        UniqueConstraint("leave_type_code", name="uq_leave_types_code"),
        UniqueConstraint("leave_type_name", name="uq_leave_types_name"),
    )

    leave_type_id: Mapped[int] = mapped_column(
        Integer().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
        primary_key=True,
        autoincrement=True,
    )
    leave_type_code: Mapped[str] = mapped_column(String(30), nullable=False)
    leave_type_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("TRUE")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
    )
