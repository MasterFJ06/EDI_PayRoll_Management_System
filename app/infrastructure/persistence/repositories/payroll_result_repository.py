from sqlalchemy import select
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

    def get_by_run_and_employee(
        self, payroll_run_id: int, employee_id: int
    ) -> PayrollResultModel | None:
        return self.session.scalar(
            select(PayrollResultModel).where(
                PayrollResultModel.payroll_run_id == payroll_run_id,
                PayrollResultModel.employee_id == employee_id,
            )
        )

    def add(self, payroll_result: PayrollResultModel) -> PayrollResultModel:
        self.session.add(payroll_result)
        self.session.flush()
        return payroll_result
