from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.payroll.repository import (
    PayrollResultComponentRepository as PayrollResultComponentRepositoryContract,
)
from app.infrastructure.persistence.models.payroll_result_component import (
    PayrollResultComponentModel,
)


class PayrollResultComponentRepository(PayrollResultComponentRepositoryContract):
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_result_and_component(
        self, payroll_result_id: int, salary_component_id: int
    ) -> PayrollResultComponentModel | None:
        return self.session.scalar(
            select(PayrollResultComponentModel).where(
                PayrollResultComponentModel.payroll_result_id == payroll_result_id,
                PayrollResultComponentModel.salary_component_id == salary_component_id,
            )
        )

    def add(
        self, component: PayrollResultComponentModel
    ) -> PayrollResultComponentModel:
        self.session.add(component)
        self.session.flush()
        return component
