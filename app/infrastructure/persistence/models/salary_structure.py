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


class SalaryStructureModel(Base):
    __tablename__ = "salary_structures"
    __table_args__ = (
        PrimaryKeyConstraint("salary_structure_id", name="pk_salary_structures"),
        UniqueConstraint("structure_code", name="uq_salary_structures_code"),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')", name="chk_salary_structures_status"
        ),
        {"mysql_engine": "InnoDB"},
    )

    salary_structure_id: Mapped[int] = mapped_column(
        Integer().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
        autoincrement=True,
    )
    structure_code: Mapped[str] = mapped_column(String(30), nullable=False)
    structure_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
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
