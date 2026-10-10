from decimal import Decimal

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.domain.payroll.repository import PayrollResultRepository as PayrollResultRepositoryContract
from app.infrastructure.persistence.models.payroll_result import PayrollResultModel


class PayrollResultRepository(PayrollResultRepositoryContract):
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, payroll_result_id: int) -> PayrollResultModel | None:
        return self.session.scalar(
            select(PayrollResultModel).where(
                PayrollResultModel.payroll_result_id == payroll_result_id
            )
        )

    def get_by_id_for_update(
        self, payroll_result_id: int
    ) -> PayrollResultModel | None:
        return self.session.scalar(
            select(PayrollResultModel)
            .where(PayrollResultModel.payroll_result_id == payroll_result_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )

    def get_by_run_and_employee(
        self, payroll_run_id: int, employee_id: int
    ) -> PayrollResultModel | None:
        return self.session.scalar(
            select(PayrollResultModel).where(
                PayrollResultModel.payroll_run_id == payroll_run_id,
                PayrollResultModel.employee_id == employee_id,
            )
        )

    def list_by_run(self, payroll_run_id: int) -> list[PayrollResultModel]:
        statement = (
            select(PayrollResultModel)
            .where(PayrollResultModel.payroll_run_id == payroll_run_id)
            .order_by(PayrollResultModel.employee_id, PayrollResultModel.payroll_result_id)
        )
        return list(self.session.scalars(statement).all())

    def aggregate_by_run(
        self, payroll_run_id: int
    ) -> tuple[int, Decimal | None, Decimal | None, Decimal | None]:
        statement = select(
            func.count(PayrollResultModel.payroll_result_id),
            func.sum(PayrollResultModel.gross_earnings),
            func.sum(PayrollResultModel.total_deductions),
            func.sum(PayrollResultModel.net_salary),
        ).where(PayrollResultModel.payroll_run_id == payroll_run_id)
        count, gross, deductions, net = self.session.execute(statement).one()
        return int(count), gross, deductions, net

    def add(self, payroll_result: PayrollResultModel) -> PayrollResultModel:
        self.session.add(payroll_result)
        self.session.flush()
        return payroll_result

    def delete_by_run(self, payroll_run_id: int) -> int:
        result = self.session.execute(
            delete(PayrollResultModel).where(
                PayrollResultModel.payroll_run_id == payroll_run_id
            )
        )
        return result.rowcount or 0
