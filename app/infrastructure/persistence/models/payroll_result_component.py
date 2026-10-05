from decimal import Decimal

from sqlalchemy import (
    DECIMAL,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    PrimaryKeyConstraint,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.models.base import Base


_UNSIGNED_BIGINT = Integer().with_variant(mysql.BIGINT(unsigned=True), "mysql")


class PayrollResultComponentModel(Base):
    __tablename__ = "payroll_result_components"
    __table_args__ = (
        PrimaryKeyConstraint(
            "payroll_result_component_id", name="pk_payroll_result_components"
        ),
        UniqueConstraint(
            "payroll_result_id",
            "salary_component_id",
            name="uq_payroll_result_component",
        ),
        CheckConstraint(
            "component_type IN ('EARNING', 'DEDUCTION')",
            name="chk_payroll_result_component_type",
        ),
        CheckConstraint("amount >= 0", name="chk_payroll_component_amount"),
        Index("idx_payroll_result_components_component", "salary_component_id"),
        {"mysql_engine": "InnoDB"},
    )

    payroll_result_component_id: Mapped[int] = mapped_column(
        _UNSIGNED_BIGINT, autoincrement=True
    )
    payroll_result_id: Mapped[int] = mapped_column(
        _UNSIGNED_BIGINT,
        ForeignKey(
            "payroll_results.payroll_result_id",
            name="fk_payroll_component_result",
            ondelete="CASCADE",
            onupdate="RESTRICT",
        ),
        nullable=False,
    )
    salary_component_id: Mapped[int] = mapped_column(
        _UNSIGNED_BIGINT,
        ForeignKey(
            "salary_components.salary_component_id",
            name="fk_payroll_component_definition",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        nullable=False,
    )
    component_type: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[Decimal] = mapped_column(DECIMAL(15, 2), nullable=False)
    calculation_order: Mapped[int] = mapped_column(
        Integer().with_variant(mysql.INTEGER(unsigned=True), "mysql"), nullable=False
    )
