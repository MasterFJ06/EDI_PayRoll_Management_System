from sqlalchemy import and_, delete, or_, select
from sqlalchemy.orm import Session

from app.domain.payroll.payroll_result_component_report import (
    PayrollResultComponentReportRecord,
)
from app.domain.payroll.repository import (
    PayrollResultComponentRepository as PayrollResultComponentRepositoryContract,
)
from app.infrastructure.persistence.models.payroll_result_component import (
    PayrollResultComponentModel,
)
from app.infrastructure.persistence.models.payroll_result import PayrollResultModel
from app.infrastructure.persistence.models.employee import Employee
from app.infrastructure.persistence.models.payroll_run import PayrollRunModel
from app.infrastructure.persistence.models.salary_component import SalaryComponentModel


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

    def list_report_page(
        self,
        payroll_run_id: int,
        after_payroll_result_id: int | None,
        after_salary_component_id: int | None,
        employee_id: int | None,
        salary_component_id: int | None,
        component_type: str | None,
        limit: int,
    ) -> list[PayrollResultComponentReportRecord]:
        statement = (
            select(
                PayrollResultComponentModel.payroll_result_component_id,
                PayrollRunModel.payroll_run_id,
                PayrollResultModel.payroll_result_id,
                PayrollResultModel.employee_id,
                Employee.employee_code,
                Employee.first_name,
                Employee.last_name,
                PayrollResultComponentModel.salary_component_id,
                SalaryComponentModel.salary_component_id.label(
                    "definition_salary_component_id"
                ),
                SalaryComponentModel.component_code,
                SalaryComponentModel.component_name,
                PayrollResultComponentModel.component_type,
                PayrollResultComponentModel.amount,
                PayrollResultComponentModel.calculation_order,
            )
            .join(
                PayrollResultModel,
                PayrollResultModel.payroll_result_id
                == PayrollResultComponentModel.payroll_result_id,
            )
            .join(
                PayrollRunModel,
                PayrollRunModel.payroll_run_id == PayrollResultModel.payroll_run_id,
            )
            .outerjoin(Employee, Employee.employee_id == PayrollResultModel.employee_id)
            .outerjoin(
                SalaryComponentModel,
                SalaryComponentModel.salary_component_id
                == PayrollResultComponentModel.salary_component_id,
            )
            .where(PayrollRunModel.payroll_run_id == payroll_run_id)
        )
        if employee_id is not None:
            statement = statement.where(PayrollResultModel.employee_id == employee_id)
        if salary_component_id is not None:
            statement = statement.where(
                PayrollResultComponentModel.salary_component_id == salary_component_id
            )
        if component_type is not None:
            statement = statement.where(
                PayrollResultComponentModel.component_type == component_type
            )
        if (
            after_payroll_result_id is not None
            and after_salary_component_id is not None
        ):
            statement = statement.where(
                or_(
                    PayrollResultModel.payroll_result_id
                    > after_payroll_result_id,
                    and_(
                        PayrollResultModel.payroll_result_id
                        == after_payroll_result_id,
                        PayrollResultComponentModel.salary_component_id
                        > after_salary_component_id,
                    ),
                )
            )
        statement = statement.order_by(
            PayrollResultModel.payroll_result_id.asc(),
            PayrollResultComponentModel.salary_component_id.asc(),
        ).limit(limit)
        rows = self.session.execute(statement).all()
        return [
            PayrollResultComponentReportRecord(
                payroll_result_component_id=row.payroll_result_component_id,
                payroll_run_id=row.payroll_run_id,
                payroll_result_id=row.payroll_result_id,
                employee_id=row.employee_id,
                employee_code=row.employee_code,
                employee_name=(
                    f"{row.first_name} {row.last_name}"
                    if row.first_name is not None and row.last_name is not None
                    else None
                ),
                salary_component_id=row.salary_component_id,
                salary_component_definition_exists=(
                    row.definition_salary_component_id is not None
                ),
                component_code=row.component_code,
                component_name=row.component_name,
                component_type=row.component_type,
                amount=row.amount,
                calculation_order=row.calculation_order,
            )
            for row in rows
        ]

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
