from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DECIMAL,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    PrimaryKeyConstraint,
    String,
    text,
)
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.models.base import Base


_UNSIGNED_BIGINT = Integer().with_variant(mysql.BIGINT(unsigned=True), "mysql")


class SalaryRevisionComponentModel(Base):
    __tablename__ = "salary_revision_components"
    __table_args__ = (
        PrimaryKeyConstraint(
            "salary_revision_id",
            "salary_component_id",
            name="pk_salary_revision_components",
        ),
        CheckConstraint(
            "calculation_type IN ('FIXED', 'PERCENTAGE')",
            name="chk_salary_calculation_type",
        ),
        CheckConstraint(
            "((calculation_type = 'FIXED' AND fixed_amount IS NOT NULL "
            "AND fixed_amount >= 0 AND percentage_value IS NULL AND base_component_id IS NULL) "
            "OR (calculation_type = 'PERCENTAGE' AND fixed_amount IS NULL "
            "AND percentage_value IS NOT NULL AND percentage_value >= 0 "
            "AND base_component_id IS NOT NULL))",
            name="chk_salary_component_calculation",
        ),
        CheckConstraint(
            "base_component_id IS NULL OR base_component_id <> salary_component_id",
            name="chk_salary_component_not_self_base",
        ),
        CheckConstraint(
            "is_overtime_base IN (0, 1)", name="chk_salary_overtime_base_boolean"
        ),
        Index("idx_revision_components_component", "salary_component_id"),
        Index("idx_revision_components_base", "base_component_id"),
        {"mysql_engine": "InnoDB"},
    )

    salary_revision_id: Mapped[int] = mapped_column(
        _UNSIGNED_BIGINT,
        ForeignKey(
            "salary_revisions.salary_revision_id",
            name="fk_revision_component_revision",
            ondelete="CASCADE",
            onupdate="RESTRICT",
        ),
    )
    salary_component_id: Mapped[int] = mapped_column(
        _UNSIGNED_BIGINT,
        ForeignKey(
            "salary_components.salary_component_id",
            name="fk_revision_component_component",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
    )
    calculation_type: Mapped[str] = mapped_column(String(20), nullable=False)
    is_overtime_base: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("FALSE")
    )
    fixed_amount: Mapped[Decimal | None] = mapped_column(DECIMAL(15, 2), nullable=True)
    percentage_value: Mapped[Decimal | None] = mapped_column(DECIMAL(8, 4), nullable=True)
    base_component_id: Mapped[int | None] = mapped_column(
        _UNSIGNED_BIGINT,
        ForeignKey(
            "salary_components.salary_component_id",
            name="fk_revision_component_base",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        nullable=True,
    )
