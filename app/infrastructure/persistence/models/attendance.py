from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, text
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.models.base import Base


_UNSIGNED_BIGINT = Integer().with_variant(mysql.BIGINT(unsigned=True), "mysql")


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    attendance_id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    employee_id: Mapped[int] = mapped_column(
        _UNSIGNED_BIGINT,
        ForeignKey(
            "employees.employee_id",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        nullable=False,
    )

    attendance_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    check_in_time: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    check_out_time: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    attendance_status: Mapped[str] = mapped_column(
        String(20),
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
        server_default=text(
            "CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"
        ),
    )
