from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    PrimaryKeyConstraint,
    SmallInteger,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.models.base import Base


_UNSIGNED_BIGINT = Integer().with_variant(mysql.BIGINT(unsigned=True), "mysql")


class PayrollRunModel(Base):
    __tablename__ = "payroll_runs"
    __table_args__ = (
        PrimaryKeyConstraint("payroll_run_id", name="pk_payroll_runs"),
        UniqueConstraint("payroll_year", "payroll_month", name="uq_payroll_period"),
        CheckConstraint("payroll_month BETWEEN 1 AND 12", name="chk_payroll_month"),
        CheckConstraint(
            "status IN ('CREATED', 'PROCESSING', 'FAILED', 'PROCESSED', 'FINALIZED')",
            name="chk_payroll_run_status",
        ),
        {"mysql_engine": "InnoDB"},
    )

    payroll_run_id: Mapped[int] = mapped_column(_UNSIGNED_BIGINT, autoincrement=True)
    payroll_year: Mapped[int] = mapped_column(
        SmallInteger().with_variant(mysql.SMALLINT(unsigned=True), "mysql"), nullable=False
    )
    payroll_month: Mapped[int] = mapped_column(
        SmallInteger().with_variant(mysql.TINYINT(unsigned=True), "mysql"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'CREATED'")
    )
    initiated_by_user_id: Mapped[int] = mapped_column(
        _UNSIGNED_BIGINT,
        ForeignKey(
            "users.user_id",
            name="fk_payroll_run_initiator",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
    )
