from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Index,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.models.base import Base


_UNSIGNED_BIGINT = Integer().with_variant(mysql.BIGINT(unsigned=True), "mysql")


class WorkCalendarDateOverrideModel(Base):
    __tablename__ = "work_calendar_date_overrides"
    __table_args__ = (
        UniqueConstraint(
            "work_calendar_version_id", "override_date", name="uq_work_calendar_date_override"
        ),
        CheckConstraint(
            "classification IN ('WORKING_DAY', 'NON_WORKING_DAY', 'HOLIDAY')",
            name="chk_work_calendar_override_classification",
        ),
        CheckConstraint(
            "classification <> 'HOLIDAY' OR "
            "(label IS NOT NULL AND CHAR_LENGTH(TRIM(label)) > 0)",
            name="chk_work_calendar_holiday_label",
        ),
        Index("idx_work_calendar_override_date", "override_date"),
        {"mysql_engine": "InnoDB"},
    )

    work_calendar_date_override_id: Mapped[int] = mapped_column(
        _UNSIGNED_BIGINT, primary_key=True, autoincrement=True
    )
    work_calendar_version_id: Mapped[int] = mapped_column(
        _UNSIGNED_BIGINT,
        ForeignKey(
            "work_calendar_versions.work_calendar_version_id",
            name="fk_work_calendar_override_version",
            ondelete="CASCADE",
            onupdate="RESTRICT",
        ),
        nullable=False,
    )
    override_date: Mapped[date] = mapped_column(Date, nullable=False)
    classification: Mapped[str] = mapped_column(String(20), nullable=False)
    label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
