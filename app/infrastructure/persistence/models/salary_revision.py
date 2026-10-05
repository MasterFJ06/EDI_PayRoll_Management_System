from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
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


class SalaryRevisionModel(Base):
    __tablename__ = "salary_revisions"
    __table_args__ = (
        PrimaryKeyConstraint("salary_revision_id", name="pk_salary_revisions"),
        UniqueConstraint(
            "salary_structure_id", "revision_number", name="uq_salary_revision_number"
        ),
        CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="chk_salary_revision_dates",
        ),
        Index(
            "idx_salary_revisions_structure_effective",
            "salary_structure_id",
            "effective_from",
            "effective_to",
        ),
        {"mysql_engine": "InnoDB"},
    )

    salary_revision_id: Mapped[int] = mapped_column(
        _UNSIGNED_BIGINT, autoincrement=True
    )
    salary_structure_id: Mapped[int] = mapped_column(
        _UNSIGNED_BIGINT,
        ForeignKey(
            "salary_structures.salary_structure_id",
            name="fk_salary_revision_structure",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        nullable=False,
    )
    revision_number: Mapped[int] = mapped_column(
        Integer().with_variant(mysql.INTEGER(unsigned=True), "mysql"), nullable=False
    )
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
