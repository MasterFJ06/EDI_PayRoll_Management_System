from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DECIMAL,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.models.base import Base


_UNSIGNED_BIGINT = Integer().with_variant(mysql.BIGINT(unsigned=True), "mysql")
_UNSIGNED_SMALLINT = Integer().with_variant(mysql.SMALLINT(unsigned=True), "mysql")


class LeaveBalanceModel(Base):
    __tablename__ = "leave_balances"
    __table_args__ = (
        UniqueConstraint(
            "employee_id", "leave_type_id", "balance_year", name="uq_leave_balance"
        ),
        CheckConstraint("allocated_days >= 0", name="chk_leave_balance_allocated"),
        CheckConstraint("used_days >= 0", name="chk_leave_balance_used"),
        CheckConstraint("used_days <= allocated_days", name="chk_leave_balance_limit"),
        Index("idx_leave_balances_type", "leave_type_id"),
    )

    leave_balance_id: Mapped[int] = mapped_column(
        _UNSIGNED_BIGINT, primary_key=True, autoincrement=True
    )
    employee_id: Mapped[int] = mapped_column(
        _UNSIGNED_BIGINT,
        ForeignKey("employees.employee_id", ondelete="RESTRICT", onupdate="RESTRICT"),
        nullable=False,
    )
    leave_type_id: Mapped[int] = mapped_column(
        _UNSIGNED_BIGINT,
        ForeignKey("leave_types.leave_type_id", ondelete="RESTRICT", onupdate="RESTRICT"),
        nullable=False,
    )
    balance_year: Mapped[int] = mapped_column(_UNSIGNED_SMALLINT, nullable=False)
    allocated_days: Mapped[Decimal] = mapped_column(
        DECIMAL(6, 2), nullable=False, server_default=text("0.00")
    )
    used_days: Mapped[Decimal] = mapped_column(
        DECIMAL(6, 2), nullable=False, server_default=text("0.00")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
    )
