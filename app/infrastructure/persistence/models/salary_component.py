from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Integer,
    PrimaryKeyConstraint,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.models.base import Base


class SalaryComponentModel(Base):
    __tablename__ = "salary_components"
    __table_args__ = (
        PrimaryKeyConstraint("salary_component_id", name="pk_salary_components"),
        UniqueConstraint("component_code", name="uq_salary_components_code"),
        CheckConstraint(
            "component_type IN ('EARNING', 'DEDUCTION')",
            name="chk_salary_component_type",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')", name="chk_salary_component_status"
        ),
        {"mysql_engine": "InnoDB"},
    )

    salary_component_id: Mapped[int] = mapped_column(
        Integer().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
        autoincrement=True,
    )
    component_code: Mapped[str] = mapped_column(String(30), nullable=False)
    component_name: Mapped[str] = mapped_column(String(100), nullable=False)
    component_type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'ACTIVE'")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
    )
