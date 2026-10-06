from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.persistence.models.payslip import Payslip


class PayslipRepository:
    """Repository for payslips persistence operations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_all(self) -> list[Payslip]:
        statement = select(Payslip).order_by(Payslip.payslip_id.desc())
        return list(self.session.scalars(statement).all())

    def get_by_id(self, payslip_id: int) -> Payslip | None:
        statement = select(Payslip).where(Payslip.payslip_id == payslip_id)
        return self.session.scalar(statement)

    def get_by_number(self, payslip_number: str) -> Payslip | None:
        statement = select(Payslip).where(Payslip.payslip_number == payslip_number)
        return self.session.scalar(statement)

    def get_by_payroll_result(self, payroll_result_id: int) -> Payslip | None:
        statement = select(Payslip).where(
            Payslip.payroll_result_id == payroll_result_id
        )
        return self.session.scalar(statement)

    def add(self, payslip: Payslip) -> Payslip:
        self.session.add(payslip)
        self.session.flush()
        return payslip
