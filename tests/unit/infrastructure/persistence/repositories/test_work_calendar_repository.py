from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.infrastructure.persistence.models.work_calendar_version import (
    WorkCalendarVersionModel,
)
from app.infrastructure.persistence.repositories.work_calendar_repository import (
    SQLAlchemyWorkCalendarRepository,
)


def repository_with_version(effective_from: date, effective_to: date | None):
    engine = create_engine("sqlite://")
    WorkCalendarVersionModel.__table__.create(engine)
    session = Session(engine)
    session.add(
        WorkCalendarVersionModel(
            version_number=1,
            effective_from=effective_from,
            effective_to=effective_to,
            time_zone="UTC",
            created_by_user_id=1,
        )
    )
    session.commit()
    return engine, session, SQLAlchemyWorkCalendarRepository(session)


def test_effective_periods_allow_adjacent_dates() -> None:
    engine, session, repository = repository_with_version(
        date(2026, 1, 1), date(2026, 6, 30)
    )
    try:
        assert not repository.has_effective_date_overlap(
            date(2026, 7, 1), date(2026, 12, 31)
        )
    finally:
        session.close()
        engine.dispose()


def test_effective_periods_reject_inclusive_overlap() -> None:
    engine, session, repository = repository_with_version(
        date(2026, 1, 1), date(2026, 6, 30)
    )
    try:
        assert repository.has_effective_date_overlap(
            date(2026, 6, 15), date(2026, 12, 31)
        )
    finally:
        session.close()
        engine.dispose()


def test_open_ended_existing_period_blocks_later_version() -> None:
    engine, session, repository = repository_with_version(date(2026, 1, 1), None)
    try:
        assert repository.has_effective_date_overlap(
            date(2026, 7, 1), date(2026, 12, 31)
        )
        assert repository.has_effective_date_overlap(date(2027, 1, 1), None)
    finally:
        session.close()
        engine.dispose()
