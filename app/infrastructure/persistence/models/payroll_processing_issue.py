from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    PrimaryKeyConstraint,
    String,
    text,
)
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.models.base import Base


_UNSIGNED_BIGINT = Integer().with_variant(mysql.BIGINT(unsigned=True), "mysql")


class PayrollProcessingIssueModel(Base):
    __tablename__ = "payroll_processing_issues"
    __table_args__ = (
        PrimaryKeyConstraint("payroll_issue_id", name="pk_payroll_processing_issues"),
        CheckConstraint("status IN ('OPEN', 'RESOLVED')", name="chk_payroll_issue_status"),
        CheckConstraint(
            "((status = 'OPEN' AND resolved_at IS NULL) OR "
            "(status = 'RESOLVED' AND resolved_at IS NOT NULL))",
            name="chk_payroll_issue_resolution",
        ),
        Index("idx_payroll_issues_run_status", "payroll_run_id", "status"),
        Index("idx_payroll_issues_employee", "employee_id"),
        {"mysql_engine": "InnoDB"},
    )

    payroll_issue_id: Mapped[int] = mapped_column(_UNSIGNED_BIGINT, autoincrement=True)
    payroll_run_id: Mapped[int] = mapped_column(
        _UNSIGNED_BIGINT,
        ForeignKey(
            "payroll_runs.payroll_run_id",
            name="fk_payroll_issue_run",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        nullable=False,
    )
    employee_id: Mapped[int | None] = mapped_column(
        _UNSIGNED_BIGINT,
        ForeignKey(
            "employees.employee_id",
            name="fk_payroll_issue_employee",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        nullable=True,
    )
    issue_code: Mapped[str] = mapped_column(String(100), nullable=False)
    issue_message: Mapped[str] = mapped_column(String(1000), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'OPEN'")
    )
    detected_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
