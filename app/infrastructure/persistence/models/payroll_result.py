from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DECIMAL,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    PrimaryKeyConstraint,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.models.base import Base


_UNSIGNED_BIGINT = Integer().with_variant(mysql.BIGINT(unsigned=True), "mysql")


class PayrollResultModel(Base):
    __tablename__ = "payroll_results"
    __table_args__ = (
        PrimaryKeyConstraint("payroll_result_id", name="pk_payroll_results"),
        UniqueConstraint(
            "payroll_run_id", "employee_id", name="uq_payroll_result_employee"
        ),
        CheckConstraint("gross_earnings >= 0", name="chk_payroll_gross_earnings"),
        CheckConstraint("total_deductions >= 0", name="chk_payroll_total_deductions"),
        CheckConstraint(
            "net_salary = gross_earnings - total_deductions",
            name="chk_payroll_net_salary",
        ),
        Index("idx_payroll_results_employee", "employee_id"),
        Index("idx_payroll_results_assignment", "salary_assignment_id"),
        {"mysql_engine": "InnoDB"},
    )

    payroll_result_id: Mapped[int] = mapped_column(_UNSIGNED_BIGINT, autoincrement=True)
    payroll_run_id: Mapped[int] = mapped_column(
        _UNSIGNED_BIGINT,
        ForeignKey(
            "payroll_runs.payroll_run_id",
            name="fk_payroll_result_run",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        nullable=False,
    )
    employee_id: Mapped[int] = mapped_column(
        _UNSIGNED_BIGINT,
        ForeignKey(
            "employees.employee_id",
            name="fk_payroll_result_employee",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        nullable=False,
    )
    salary_assignment_id: Mapped[int] = mapped_column(
        _UNSIGNED_BIGINT,
        ForeignKey(
            "employee_salary_assignments.salary_assignment_id",
            name="fk_payroll_result_assignment",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        nullable=False,
    )
    gross_earnings: Mapped[Decimal] = mapped_column(DECIMAL(15, 2), nullable=False)
    total_deductions: Mapped[Decimal] = mapped_column(DECIMAL(15, 2), nullable=False)
    net_salary: Mapped[Decimal] = mapped_column(DECIMAL(15, 2), nullable=False)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
