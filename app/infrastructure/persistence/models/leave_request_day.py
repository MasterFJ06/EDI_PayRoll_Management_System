from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DECIMAL, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.models.base import Base


_UNSIGNED_BIGINT = Integer().with_variant(mysql.BIGINT(unsigned=True), "mysql")


class LeaveRequestDayModel(Base):
    __tablename__ = "leave_request_days"
    __table_args__ = (
        UniqueConstraint(
            "leave_request_id", "leave_date", name="uq_leave_request_day"
        ),
        CheckConstraint(
            "day_fraction >= 0.01 AND day_fraction <= 1.00",
            name="chk_leave_request_day_fraction",
        ),
        {"mysql_engine": "InnoDB"},
    )

    leave_request_day_id: Mapped[int] = mapped_column(
        _UNSIGNED_BIGINT, primary_key=True, autoincrement=True
    )
    leave_request_id: Mapped[int] = mapped_column(
        _UNSIGNED_BIGINT,
        ForeignKey(
            "leave_requests.leave_request_id",
            name="fk_leave_request_day_request",
            ondelete="CASCADE",
            onupdate="RESTRICT",
        ),
        nullable=False,
    )
    leave_date: Mapped[date] = mapped_column(Date, nullable=False)
    day_fraction: Mapped[Decimal] = mapped_column(DECIMAL(4, 2), nullable=False)
