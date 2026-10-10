from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.domain.shared.exceptions import InvalidDomainState
from app.infrastructure.persistence.models.workforce_overtime_policy_version import WorkforceOvertimePolicyVersionModel
from app.infrastructure.persistence.repositories.overtime_policy_repository import OvertimePolicyRepository


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    WorkforceOvertimePolicyVersionModel.__table__.create(engine)
    with Session(engine) as db:
        yield db
    engine.dispose()


def add_policy(session: Session, version: int, start: date, end: date | None):
    model = WorkforceOvertimePolicyVersionModel(
        version_number=version, effective_from=start, effective_to=end,
        non_working_multiplier=Decimal("1.5000"), created_by_user_id=7,
    )
    session.add(model)
    session.flush()
    return model


def test_repository_persists_policy_and_resolves_inclusive_dates(session: Session):
    repo = OvertimePolicyRepository(session)
    first = add_policy(session, 1, date(2026, 1, 1), date(2026, 6, 30))
    second = add_policy(session, 2, date(2026, 7, 1), None)
    assert repo.get_by_id(first.workforce_overtime_policy_version_id).non_working_multiplier == Decimal("1.5000")
    assert repo.get_applicable(date(2026, 6, 30)).version_number == 1
    assert repo.get_applicable(date(2026, 7, 1)).version_number == 2
    assert repo.get_applicable(date(2025, 12, 31)) is None
    assert not repo.has_effective_date_overlap(date(2025, 1, 1), date(2025, 12, 31))
    assert repo.has_effective_date_overlap(date(2026, 6, 30), date(2026, 7, 2))


def test_repository_detects_persisted_overlapping_policy_conflict(session: Session):
    add_policy(session, 1, date(2026, 1, 1), date(2026, 12, 31))
    add_policy(session, 2, date(2026, 6, 1), None)
    with pytest.raises(InvalidDomainState, match="Overlapping"):
        OvertimePolicyRepository(session).get_applicable(date(2026, 7, 1))
