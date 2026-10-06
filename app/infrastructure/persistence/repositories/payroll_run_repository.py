from sqlalchemy import func, select, update
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

    def claim_for_processing(self, payroll_run_id: int) -> bool:
        result = self.session.execute(
            update(PayrollRunModel)
            .where(
                PayrollRunModel.payroll_run_id == payroll_run_id,
                PayrollRunModel.status == "CREATED",
            )
            .values(status="PROCESSING", started_at=func.now())
            .execution_options(synchronize_session=False)
        )
        return result.rowcount == 1

    def mark_failed_if_processing(self, payroll_run_id: int) -> bool:
        result = self.session.execute(
            update(PayrollRunModel)
            .where(
                PayrollRunModel.payroll_run_id == payroll_run_id,
                PayrollRunModel.status == "PROCESSING",
            )
            .values(status="FAILED")
            .execution_options(synchronize_session=False)
        )
        return result.rowcount == 1
