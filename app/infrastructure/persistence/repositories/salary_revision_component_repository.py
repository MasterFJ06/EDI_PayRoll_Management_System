from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.compensation.repository import (
    SalaryRevisionComponentRepository as SalaryRevisionComponentRepositoryContract,
)
from app.infrastructure.persistence.models.salary_revision_component import (
    SalaryRevisionComponentModel,
)


class SalaryRevisionComponentRepository(SalaryRevisionComponentRepositoryContract):
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_revision_and_component(
        self, salary_revision_id: int, salary_component_id: int
    ) -> SalaryRevisionComponentModel | None:
        statement = select(SalaryRevisionComponentModel).where(
            SalaryRevisionComponentModel.salary_revision_id == salary_revision_id,
            SalaryRevisionComponentModel.salary_component_id == salary_component_id,
        )
        return self.session.scalar(statement)

    def get_by_revision(
        self, salary_revision_id: int
    ) -> list[SalaryRevisionComponentModel]:
        statement = (
            select(SalaryRevisionComponentModel)
            .where(
                SalaryRevisionComponentModel.salary_revision_id == salary_revision_id
            )
            .order_by(SalaryRevisionComponentModel.salary_component_id)
        )
        return list(self.session.scalars(statement).all())

    def add(
        self, component: SalaryRevisionComponentModel
    ) -> SalaryRevisionComponentModel:
        self.session.add(component)
        self.session.flush()
        return component
