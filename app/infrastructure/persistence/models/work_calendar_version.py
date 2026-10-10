from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Index,
    String,
    UniqueConstraint,
    CheckConstraint,
    text,
)
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.models.base import Base


_UNSIGNED_BIGINT = Integer().with_variant(mysql.BIGINT(unsigned=True), "mysql")
_UNSIGNED_INT = Integer().with_variant(mysql.INTEGER(unsigned=True), "mysql")


class WorkCalendarVersionModel(Base):
    __tablename__ = "work_calendar_versions"
    __table_args__ = (
        UniqueConstraint("version_number", name="uq_work_calendar_version_number"),
        CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="chk_work_calendar_version_dates",
        ),
        Index("idx_work_calendar_version_dates", "effective_from", "effective_to"),
        Index("idx_work_calendar_version_replacement", "replaces_version_id"),
        {"mysql_engine": "InnoDB"},
    )

    work_calendar_version_id: Mapped[int] = mapped_column(
        _UNSIGNED_BIGINT, primary_key=True, autoincrement=True
    )
    version_number: Mapped[int] = mapped_column(_UNSIGNED_INT, nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    time_zone: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by_user_id: Mapped[int] = mapped_column(
        _UNSIGNED_BIGINT,
        ForeignKey(
            "users.user_id",
            name="fk_work_calendar_version_creator",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        nullable=False,
    )
    replaces_version_id: Mapped[int | None] = mapped_column(
        _UNSIGNED_BIGINT,
        ForeignKey(
            "work_calendar_versions.work_calendar_version_id",
            name="fk_work_calendar_version_replacement",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
