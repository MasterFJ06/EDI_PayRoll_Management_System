from sqlalchemy import CheckConstraint, ForeignKey, Integer, SmallInteger, String, UniqueConstraint
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.models.base import Base


_UNSIGNED_BIGINT = Integer().with_variant(mysql.BIGINT(unsigned=True), "mysql")
_UNSIGNED_TINYINT = SmallInteger().with_variant(mysql.TINYINT(unsigned=True), "mysql")
_UNSIGNED_SMALLINT = SmallInteger().with_variant(mysql.SMALLINT(unsigned=True), "mysql")


class WorkCalendarWeeklyRuleModel(Base):
    __tablename__ = "work_calendar_weekly_rules"
    __table_args__ = (
        UniqueConstraint(
            "work_calendar_version_id", "iso_weekday", name="uq_work_calendar_weekday"
        ),
        CheckConstraint("iso_weekday BETWEEN 1 AND 7", name="chk_work_calendar_iso_weekday"),
        CheckConstraint(
            "classification IN ('WORKING_DAY', 'NON_WORKING_DAY')",
            name="chk_work_calendar_weekly_classification",
        ),
        CheckConstraint(
            "(classification = 'WORKING_DAY' AND scheduled_minutes = 480) "
            "OR (classification = 'NON_WORKING_DAY' AND scheduled_minutes = 0)",
            name="chk_work_calendar_weekly_minutes",
        ),
        {"mysql_engine": "InnoDB"},
    )

    work_calendar_weekly_rule_id: Mapped[int] = mapped_column(
        _UNSIGNED_BIGINT, primary_key=True, autoincrement=True
    )
    work_calendar_version_id: Mapped[int] = mapped_column(
        _UNSIGNED_BIGINT,
        ForeignKey(
            "work_calendar_versions.work_calendar_version_id",
            name="fk_work_calendar_weekly_version",
            ondelete="CASCADE",
            onupdate="RESTRICT",
        ),
        nullable=False,
    )
    iso_weekday: Mapped[int] = mapped_column(_UNSIGNED_TINYINT, nullable=False)
    classification: Mapped[str] = mapped_column(String(20), nullable=False)
    scheduled_minutes: Mapped[int] = mapped_column(_UNSIGNED_SMALLINT, nullable=False)
