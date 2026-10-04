from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    DECIMAL,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    text,
)
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.models.base import Base


_UNSIGNED_BIGINT = Integer().with_variant(mysql.BIGINT(unsigned=True), "mysql")


class LeaveRequestModel(Base):
    __tablename__ = "leave_requests"
    __table_args__ = (
        CheckConstraint("end_date >= start_date", name="chk_leave_request_dates"),
        CheckConstraint("requested_days > 0", name="chk_leave_requested_days"),
        CheckConstraint(
            "status IN ('PENDING', 'APPROVED', 'REJECTED', 'CANCELLED')",
            name="chk_leave_request_status",
        ),
        CheckConstraint(
            "((status = 'PENDING' AND reviewed_by_employee_id IS NULL AND reviewed_at IS NULL) "
            "OR (status IN ('APPROVED', 'REJECTED') AND reviewed_by_employee_id IS NOT NULL "
            "AND reviewed_at IS NOT NULL) OR status = 'CANCELLED')",
            name="chk_leave_review_consistency",
        ),
        Index("idx_leave_requests_employee_date", "employee_id", "start_date"),
        Index("idx_leave_requests_status_created", "status", "created_at"),
        Index("idx_leave_requests_type", "leave_type_id"),
        Index("idx_leave_requests_reviewer", "reviewed_by_employee_id"),
    )

    leave_request_id: Mapped[int] = mapped_column(
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
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    requested_days: Mapped[Decimal] = mapped_column(DECIMAL(6, 2), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'PENDING'")
    )
    reviewed_by_employee_id: Mapped[int | None] = mapped_column(
        _UNSIGNED_BIGINT,
        ForeignKey("employees.employee_id", ondelete="RESTRICT", onupdate="RESTRICT"),
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    review_comment: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
    )
