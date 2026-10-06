from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.models.base import Base


class SalaryStructure(Base):
    """SQLAlchemy model for salary structures."""

    __tablename__ = "salary_structures"

    salary_structure_id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    structure_code: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        unique=True,
    )

    structure_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
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
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
    )


class SalaryComponent(Base):
    """SQLAlchemy model for salary components (allowances and deductions)."""

    __tablename__ = "salary_components"

    salary_component_id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    component_code: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        unique=True,
    )

    component_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    component_type: Mapped[str] = mapped_column(
        String(20),
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
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
    )


class SalaryRevision(Base):
    """SQLAlchemy model for revision history of salary structures."""

    __tablename__ = "salary_revisions"

    __table_args__ = (
        UniqueConstraint(
            "salary_structure_id",
            "revision_number",
            name="uq_salary_revisions_structure_rev",
        ),
    )

    salary_revision_id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    salary_structure_id: Mapped[int] = mapped_column(
        ForeignKey("salary_structures.salary_structure_id"),
        nullable=False,
    )

    revision_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    effective_from: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    effective_to: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class SalaryRevisionComponent(Base):
    """SQLAlchemy model for items linked to a salary revision."""

    __tablename__ = "salary_revision_components"

    salary_revision_id: Mapped[int] = mapped_column(
        ForeignKey("salary_revisions.salary_revision_id", ondelete="CASCADE"),
        primary_key=True,
    )

    salary_component_id: Mapped[int] = mapped_column(
        ForeignKey("salary_components.salary_component_id"),
        primary_key=True,
    )

    calculation_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    fixed_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
    )

    percentage_value: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 4),
        nullable=True,
    )

    base_component_id: Mapped[int | None] = mapped_column(
        ForeignKey("salary_components.salary_component_id"),
        nullable=True,
    )


class EmployeeSalaryAssignment(Base):
    """SQLAlchemy model assigning a salary structure revision to an employee."""

    __tablename__ = "employee_salary_assignments"

    salary_assignment_id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.employee_id"),
        nullable=False,
    )

    salary_revision_id: Mapped[int] = mapped_column(
        ForeignKey("salary_revisions.salary_revision_id"),
        nullable=False,
    )

    effective_from: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    effective_to: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
