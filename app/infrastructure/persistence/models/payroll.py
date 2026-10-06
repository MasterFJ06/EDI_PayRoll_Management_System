from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.models.base import Base


class PayrollRun(Base):
    """SQLAlchemy model for payroll processing runs."""

    __tablename__ = "payroll_runs"

    __table_args__ = (
        UniqueConstraint(
            "payroll_year",
            "payroll_month",
            name="uq_payroll_runs_year_month",
        ),
    )

    payroll_run_id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    payroll_year: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
    )

    payroll_month: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="CREATED",
    )

    initiated_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id"),
        nullable=False,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    finalized_at: Mapped[datetime | None] = mapped_column(
        DateTime,
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


class PayrollResult(Base):
    """SQLAlchemy model for an employee's computed payroll result in a run."""

    __tablename__ = "payroll_results"

    __table_args__ = (
        UniqueConstraint(
            "payroll_run_id",
            "employee_id",
            name="uq_payroll_results_run_employee",
        ),
    )

    payroll_result_id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    payroll_run_id: Mapped[int] = mapped_column(
        ForeignKey("payroll_runs.payroll_run_id"),
        nullable=False,
    )

    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.employee_id"),
        nullable=False,
    )

    salary_assignment_id: Mapped[int] = mapped_column(
        ForeignKey("employee_salary_assignments.salary_assignment_id"),
        nullable=False,
    )

    gross_earnings: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
    )

    total_deductions: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
    )

    net_salary: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
    )

    processed_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class PayrollResultComponent(Base):
    """SQLAlchemy model for component breakdown of an employee's payroll result."""

    __tablename__ = "payroll_result_components"

    __table_args__ = (
        UniqueConstraint(
            "payroll_result_id",
            "salary_component_id",
            name="uq_payroll_result_components_result_comp",
        ),
    )

    payroll_result_component_id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    payroll_result_id: Mapped[int] = mapped_column(
        ForeignKey("payroll_results.payroll_result_id", ondelete="CASCADE"),
        nullable=False,
    )

    salary_component_id: Mapped[int] = mapped_column(
        ForeignKey("salary_components.salary_component_id"),
        nullable=False,
    )

    component_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
    )

    calculation_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )


class PayrollProcessingIssue(Base):
    """SQLAlchemy model for issues detected during payroll validation or run."""

    __tablename__ = "payroll_processing_issues"

    payroll_issue_id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    payroll_run_id: Mapped[int] = mapped_column(
        ForeignKey("payroll_runs.payroll_run_id"),
        nullable=False,
    )

    employee_id: Mapped[int | None] = mapped_column(
        ForeignKey("employees.employee_id"),
        nullable=True,
    )

    issue_code: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    issue_message: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="OPEN",
    )

    detected_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )
