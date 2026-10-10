from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    DECIMAL,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.models.base import Base


_UNSIGNED_BIGINT = Integer().with_variant(mysql.BIGINT(unsigned=True), "mysql")
_UNSIGNED_INT = Integer().with_variant(mysql.INTEGER(unsigned=True), "mysql")


class WorkforceOvertimePolicyVersionModel(Base):
    __tablename__ = "workforce_overtime_policy_versions"
    __table_args__ = (
        UniqueConstraint(
            "version_number", name="uq_workforce_overtime_policy_version"
        ),
        CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="chk_workforce_overtime_policy_dates",
        ),
        CheckConstraint(
            "non_working_multiplier >= 0",
            name="chk_workforce_overtime_non_working_multiplier",
        ),
        Index(
            "idx_workforce_overtime_policy_dates", "effective_from", "effective_to"
        ),
        {"mysql_engine": "InnoDB"},
    )

    workforce_overtime_policy_version_id: Mapped[int] = mapped_column(
        _UNSIGNED_BIGINT, primary_key=True, autoincrement=True
    )
    version_number: Mapped[int] = mapped_column(_UNSIGNED_INT, nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    non_working_multiplier: Mapped[Decimal] = mapped_column(DECIMAL(8, 4), nullable=False)
    created_by_user_id: Mapped[int] = mapped_column(
        _UNSIGNED_BIGINT,
        ForeignKey(
            "users.user_id",
            name="fk_workforce_overtime_policy_creator",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
