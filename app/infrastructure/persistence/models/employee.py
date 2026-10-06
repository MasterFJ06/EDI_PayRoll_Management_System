from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.models.base import Base


class Employee(Base):
    __tablename__ = "employees"

    employee_id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    employee_code: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        unique=True,
    )

    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.user_id"),
        nullable=True,
        unique=True,
    )

    first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    last_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    department_id: Mapped[int] = mapped_column(
        ForeignKey("departments.department_id"),
        nullable=False,
    )

    designation_id: Mapped[int] = mapped_column(
        ForeignKey("designations.designation_id"),
        nullable=False,
    )

    manager_employee_id: Mapped[int | None] = mapped_column(
        ForeignKey("employees.employee_id"),
        nullable=True,
    )

    joining_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    employment_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'ACTIVE'"),
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