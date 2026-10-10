from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, PrimaryKeyConstraint
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.models.base import Base


_UNSIGNED_BIGINT = Integer().with_variant(mysql.BIGINT(unsigned=True), "mysql")


class PayrollRunWorkforceSnapshotModel(Base):
    __tablename__ = "payroll_run_workforce_snapshots"
    __table_args__ = (
        PrimaryKeyConstraint(
            "payroll_run_id",
            "employee_id",
            name="pk_payroll_run_workforce_snapshots",
        ),
        Index(
            "idx_payroll_run_workforce_snapshots_attempt",
            "payroll_run_id",
            "attempt_number",
        ),
        {"mysql_engine": "InnoDB"},
    )

    payroll_run_id: Mapped[int] = mapped_column(
        _UNSIGNED_BIGINT,
        ForeignKey(
            "payroll_runs.payroll_run_id",
            name="fk_payroll_workforce_snapshot_run",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        nullable=False,
    )
    employee_id: Mapped[int] = mapped_column(
        _UNSIGNED_BIGINT,
        ForeignKey(
            "employees.employee_id",
            name="fk_payroll_workforce_snapshot_employee",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        nullable=False,
    )
    attempt_number: Mapped[int] = mapped_column(_UNSIGNED_BIGINT, nullable=False)
    snapshot_at: Mapped[datetime] = mapped_column(
        DateTime().with_variant(mysql.DATETIME(fsp=6), "mysql"), nullable=False
    )
    snapshot: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
