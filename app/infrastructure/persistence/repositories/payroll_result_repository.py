from decimal import Decimal

from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.orm import Session

from app.domain.payroll.payroll_result_report import PayrollResultReportRecord
from app.domain.payroll.repository import (
    PayrollResultRepository as PayrollResultRepositoryContract,
)
from app.infrastructure.persistence.models.employee import Employee
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

    def list_report_page(
        self,
        payroll_run_id: int,
        after_employee_id: int | None,
        after_payroll_result_id: int | None,
        limit: int,
    ) -> list[PayrollResultReportRecord]:
        statement = select(
            PayrollResultModel.payroll_result_id,
            PayrollResultModel.payroll_run_id,
            PayrollResultModel.employee_id,
            PayrollResultModel.salary_assignment_id,
            PayrollResultModel.gross_earnings,
            PayrollResultModel.total_deductions,
            PayrollResultModel.net_salary,
            Employee.employee_code,
            Employee.first_name,
            Employee.last_name,
        ).outerjoin(
            Employee, Employee.employee_id == PayrollResultModel.employee_id
        ).where(
            PayrollResultModel.payroll_run_id == payroll_run_id
        )
        if after_employee_id is not None and after_payroll_result_id is not None:
            statement = statement.where(
                or_(
                    PayrollResultModel.employee_id > after_employee_id,
                    and_(
                        PayrollResultModel.employee_id == after_employee_id,
                        PayrollResultModel.payroll_result_id > after_payroll_result_id,
                    ),
                )
            )
        statement = statement.order_by(
            PayrollResultModel.employee_id.asc(),
            PayrollResultModel.payroll_result_id.asc(),
        ).limit(limit)
        rows = self.session.execute(statement).all()
        return [
            PayrollResultReportRecord(
                payroll_result_id=row.payroll_result_id,
                payroll_run_id=row.payroll_run_id,
                employee_id=row.employee_id,
                salary_assignment_id=row.salary_assignment_id,
                gross_earnings=row.gross_earnings,
                total_deductions=row.total_deductions,
                net_salary=row.net_salary,
                employee_code=row.employee_code,
                employee_name=(
                    f"{row.first_name} {row.last_name}"
                    if row.first_name is not None and row.last_name is not None
                    else None
                ),
            )
            for row in rows
        ]

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
