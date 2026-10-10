from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.compensation.repository import SalaryComponentRepository as SalaryComponentRepositoryContract
from app.infrastructure.persistence.models.salary_component import SalaryComponentModel


class SalaryComponentRepository(SalaryComponentRepositoryContract):
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, salary_component_id: int) -> SalaryComponentModel | None:
        return self.session.scalar(
            select(SalaryComponentModel).where(
                SalaryComponentModel.salary_component_id == salary_component_id
            )
        )

    def get_by_code(self, component_code: str) -> SalaryComponentModel | None:
        return self.session.scalar(
            select(SalaryComponentModel).where(
                SalaryComponentModel.component_code == component_code
            )
        )

    def get_by_ids(self, salary_component_ids: set[int]) -> list[SalaryComponentModel]:
        if not salary_component_ids:
            return []
        statement = (
            select(SalaryComponentModel)
            .where(SalaryComponentModel.salary_component_id.in_(salary_component_ids))
            .order_by(SalaryComponentModel.salary_component_id)
        )
        return list(self.session.scalars(statement).all())

    def add(self, component: SalaryComponentModel) -> SalaryComponentModel:
        self.session.add(component)
        self.session.flush()
        return component
