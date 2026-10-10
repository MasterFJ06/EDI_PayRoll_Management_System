from datetime import date

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.domain.shared.exceptions import InvalidDomainState
from app.domain.workforce.overtime import OvertimePolicyVersion
from app.domain.workforce.repository import OvertimePolicyRepository as OvertimePolicyRepositoryContract
from app.infrastructure.persistence.models.workforce_overtime_policy_version import WorkforceOvertimePolicyVersionModel


class OvertimePolicyRepository(OvertimePolicyRepositoryContract):
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, policy_id: int) -> OvertimePolicyVersion | None:
        model = self.session.get(WorkforceOvertimePolicyVersionModel, policy_id)
        return self._to_domain(model) if model is not None else None

    def get_applicable(self, day: date) -> OvertimePolicyVersion | None:
        statement = select(WorkforceOvertimePolicyVersionModel).where(
            WorkforceOvertimePolicyVersionModel.effective_from <= day,
            or_(WorkforceOvertimePolicyVersionModel.effective_to.is_(None),
                WorkforceOvertimePolicyVersionModel.effective_to >= day),
        )
        models = list(self.session.scalars(statement))
        if len(models) > 1:
            raise InvalidDomainState("Overlapping overtime policy versions are persisted.")
        return self._to_domain(models[0]) if models else None

    def has_effective_date_overlap(self, start: date, end: date | None) -> bool:
        conditions = [or_(WorkforceOvertimePolicyVersionModel.effective_to.is_(None),
                          WorkforceOvertimePolicyVersionModel.effective_to >= start)]
        if end is not None:
            conditions.append(WorkforceOvertimePolicyVersionModel.effective_from <= end)
        return self.session.scalar(
            select(WorkforceOvertimePolicyVersionModel.workforce_overtime_policy_version_id)
            .where(and_(*conditions)).limit(1)
        ) is not None

    def add(self, policy: OvertimePolicyVersion) -> OvertimePolicyVersion:
        model = WorkforceOvertimePolicyVersionModel(
            version_number=policy.version_number,
            effective_from=policy.effective_from,
            effective_to=policy.effective_to,
            non_working_multiplier=policy.non_working_multiplier,
            created_by_user_id=policy.created_by_user_id,
        )
        self.session.add(model)
        self.session.flush()
        return self._to_domain(model)

    @staticmethod
    def _to_domain(model: WorkforceOvertimePolicyVersionModel) -> OvertimePolicyVersion:
        return OvertimePolicyVersion(
            policy_id=model.workforce_overtime_policy_version_id,
            version_number=model.version_number,
            effective_from=model.effective_from,
            effective_to=model.effective_to,
            non_working_multiplier=model.non_working_multiplier,
            created_by_user_id=model.created_by_user_id,
        )
