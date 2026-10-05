from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.payroll.repository import PayrollRunRepository as PayrollRunRepositoryContract
from app.infrastructure.persistence.models.payroll_run import PayrollRunModel


class PayrollRunRepository(PayrollRunRepositoryContract):
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, payroll_run_id: int) -> PayrollRunModel | None:
        return self.session.scalar(
            select(PayrollRunModel).where(PayrollRunModel.payroll_run_id == payroll_run_id)
        )

    def get_by_period(self, payroll_year: int, payroll_month: int) -> PayrollRunModel | None:
        return self.session.scalar(
            select(PayrollRunModel).where(
                PayrollRunModel.payroll_year == payroll_year,
                PayrollRunModel.payroll_month == payroll_month,
            )
        )

    def add(self, payroll_run: PayrollRunModel) -> PayrollRunModel:
        self.session.add(payroll_run)
        self.session.flush()
        return payroll_run
