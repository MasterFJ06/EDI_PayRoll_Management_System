from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    PrimaryKeyConstraint,
    text,
)
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.models.base import Base


_UNSIGNED_BIGINT = Integer().with_variant(mysql.BIGINT(unsigned=True), "mysql")


class EmployeeSalaryAssignmentModel(Base):
    __tablename__ = "employee_salary_assignments"
    __table_args__ = (
        PrimaryKeyConstraint(
            "salary_assignment_id", name="pk_employee_salary_assignments"
        ),
        CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="chk_salary_assignment_dates",
        ),
        Index(
            "idx_salary_assignments_employee_effective",
            "employee_id",
            "effective_from",
            "effective_to",
        ),
        Index("idx_salary_assignments_revision", "salary_revision_id"),
        {"mysql_engine": "InnoDB"},
    )

    salary_assignment_id: Mapped[int] = mapped_column(
        _UNSIGNED_BIGINT, autoincrement=True
    )
    employee_id: Mapped[int] = mapped_column(
        _UNSIGNED_BIGINT,
        ForeignKey(
            "employees.employee_id",
            name="fk_salary_assignment_employee",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        nullable=False,
    )
    salary_revision_id: Mapped[int] = mapped_column(
        _UNSIGNED_BIGINT,
        ForeignKey(
            "salary_revisions.salary_revision_id",
            name="fk_salary_assignment_revision",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        nullable=False,
    )
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
