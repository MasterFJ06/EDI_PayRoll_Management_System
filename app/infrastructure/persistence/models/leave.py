from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    SmallInteger,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.models.base import Base


class LeaveType(Base):
    """SQLAlchemy model for types of leave."""

    __tablename__ = "leave_types"

    leave_type_id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    leave_type_code: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        unique=True,
    )

    leave_type_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
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


class LeaveBalance(Base):
    """SQLAlchemy model for employee leave entitlements and balances."""

    __tablename__ = "leave_balances"

    __table_args__ = (
        UniqueConstraint(
            "employee_id",
            "leave_type_id",
            "balance_year",
            name="uq_leave_balances_emp_type_year",
        ),
    )

    leave_balance_id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.employee_id"),
        nullable=False,
    )

    leave_type_id: Mapped[int] = mapped_column(
        ForeignKey("leave_types.leave_type_id"),
        nullable=False,
    )

    balance_year: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
    )

    allocated_days: Mapped[Decimal] = mapped_column(
        Numeric(6, 2),
        nullable=False,
        default=Decimal("0.00"),
    )

    used_days: Mapped[Decimal] = mapped_column(
        Numeric(6, 2),
        nullable=False,
        default=Decimal("0.00"),
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


class LeaveRequest(Base):
    """SQLAlchemy model for employee leave requests."""

    __tablename__ = "leave_requests"

    leave_request_id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.employee_id"),
        nullable=False,
    )

    leave_type_id: Mapped[int] = mapped_column(
        ForeignKey("leave_types.leave_type_id"),
        nullable=False,
    )

    start_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    end_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    requested_days: Mapped[Decimal] = mapped_column(
        Numeric(6, 2),
        nullable=False,
    )

    reason: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="PENDING",
    )

    reviewed_by_employee_id: Mapped[int | None] = mapped_column(
        ForeignKey("employees.employee_id"),
        nullable=True,
    )

    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    review_comment: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
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
