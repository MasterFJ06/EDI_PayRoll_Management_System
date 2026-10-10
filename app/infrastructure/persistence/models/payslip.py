from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    PrimaryKeyConstraint,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.models.base import Base


_UNSIGNED_BIGINT = Integer().with_variant(mysql.BIGINT(unsigned=True), "mysql")


class PayslipModel(Base):
    __tablename__ = "payslips"
    __table_args__ = (
        PrimaryKeyConstraint("payslip_id", name="pk_payslips"),
        UniqueConstraint("payroll_result_id", name="uq_payslip_result"),
        UniqueConstraint("payslip_number", name="uq_payslip_number"),
        {"mysql_engine": "InnoDB"},
    )

    payslip_id: Mapped[int] = mapped_column(_UNSIGNED_BIGINT, autoincrement=True)
    payroll_result_id: Mapped[int] = mapped_column(
        _UNSIGNED_BIGINT,
        ForeignKey(
            "payroll_results.payroll_result_id",
            name="fk_payslip_result",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        nullable=False,
    )
    payslip_number: Mapped[str] = mapped_column(String(50), nullable=False)
    generated_by_user_id: Mapped[int] = mapped_column(
        _UNSIGNED_BIGINT,
        ForeignKey(
            "users.user_id",
            name="fk_payslip_generator",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        nullable=False,
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    document_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
