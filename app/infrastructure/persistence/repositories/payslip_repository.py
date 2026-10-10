from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.payroll.repository import PayslipRepository as PayslipRepositoryContract
from app.infrastructure.persistence.models.payslip import PayslipModel
from app.infrastructure.persistence.models.payroll_result import PayrollResultModel


class PayslipRepository(PayslipRepositoryContract):
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, payslip_id: int) -> PayslipModel | None:
        return self.session.scalar(
            select(PayslipModel).where(PayslipModel.payslip_id == payslip_id)
        )

    def get_by_result_id(self, payroll_result_id: int) -> PayslipModel | None:
        return self.session.scalar(
            select(PayslipModel).where(PayslipModel.payroll_result_id == payroll_result_id)
        )

    def get_by_number(self, payslip_number: str) -> PayslipModel | None:
        return self.session.scalar(
            select(PayslipModel).where(PayslipModel.payslip_number == payslip_number)
        )

    def get_by_run_id(self, payroll_run_id: int) -> PayslipModel | None:
        return self.session.scalar(
            select(PayslipModel)
            .join(
                PayrollResultModel,
                PayslipModel.payroll_result_id == PayrollResultModel.payroll_result_id,
            )
            .where(PayrollResultModel.payroll_run_id == payroll_run_id)
            .limit(1)
        )

    def get_by_run_id_for_update(self, payroll_run_id: int) -> PayslipModel | None:
        return self.session.scalar(
            select(PayslipModel)
            .join(
                PayrollResultModel,
                PayslipModel.payroll_result_id == PayrollResultModel.payroll_result_id,
            )
            .where(PayrollResultModel.payroll_run_id == payroll_run_id)
            .limit(1)
            .with_for_update()
        )

    def add(self, payslip: PayslipModel) -> PayslipModel:
        self.session.add(payslip)
        self.session.flush()
        self.session.refresh(payslip)
        return payslip
