from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.domain.payroll.repository import (
    PayrollResultComponentRepository as PayrollResultComponentRepositoryContract,
)
from app.infrastructure.persistence.models.payroll_result_component import (
    PayrollResultComponentModel,
)
from app.infrastructure.persistence.models.payroll_result import PayrollResultModel


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

    def list_by_run(self, payroll_run_id: int) -> list[PayrollResultComponentModel]:
        statement = (
            select(PayrollResultComponentModel)
            .join(
                PayrollResultModel,
                PayrollResultModel.payroll_result_id
                == PayrollResultComponentModel.payroll_result_id,
            )
            .where(PayrollResultModel.payroll_run_id == payroll_run_id)
            .order_by(
                PayrollResultComponentModel.payroll_result_id,
                PayrollResultComponentModel.salary_component_id,
            )
        )
        return list(self.session.scalars(statement).all())

    def add(
        self, component: PayrollResultComponentModel
    ) -> PayrollResultComponentModel:
        self.session.add(component)
        self.session.flush()
        return component

    def delete_by_run(self, payroll_run_id: int) -> int:
        result_ids = select(PayrollResultModel.payroll_result_id).where(
            PayrollResultModel.payroll_run_id == payroll_run_id
        )
        result = self.session.execute(
            delete(PayrollResultComponentModel).where(
                PayrollResultComponentModel.payroll_result_id.in_(result_ids)
            )
        )
        return result.rowcount or 0
