from datetime import date

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.domain.compensation.repository import (
    EmployeeSalaryAssignmentRepository as EmployeeSalaryAssignmentRepositoryContract,
)
from app.infrastructure.persistence.models.employee_salary_assignment import (
    EmployeeSalaryAssignmentModel,
)


class EmployeeSalaryAssignmentRepository(EmployeeSalaryAssignmentRepositoryContract):
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, salary_assignment_id: int) -> EmployeeSalaryAssignmentModel | None:
        return self.session.scalar(
            select(EmployeeSalaryAssignmentModel).where(
                EmployeeSalaryAssignmentModel.salary_assignment_id == salary_assignment_id
            )
        )

    def get_applicable_for_employee(
        self, employee_id: int, snapshot_date: date
    ) -> list[EmployeeSalaryAssignmentModel]:
        statement = (
            select(EmployeeSalaryAssignmentModel)
            .where(
                EmployeeSalaryAssignmentModel.employee_id == employee_id,
                EmployeeSalaryAssignmentModel.effective_from <= snapshot_date,
                or_(
                    EmployeeSalaryAssignmentModel.effective_to.is_(None),
                    EmployeeSalaryAssignmentModel.effective_to >= snapshot_date,
                ),
            )
            .order_by(EmployeeSalaryAssignmentModel.salary_assignment_id)
        )
        return list(self.session.scalars(statement).all())

    def get_intersecting_for_employee(
        self, employee_id: int, period_start: date, period_end: date
    ) -> list[EmployeeSalaryAssignmentModel]:
        statement = (
            select(EmployeeSalaryAssignmentModel)
            .where(
                EmployeeSalaryAssignmentModel.employee_id == employee_id,
                EmployeeSalaryAssignmentModel.effective_from <= period_end,
                or_(
                    EmployeeSalaryAssignmentModel.effective_to.is_(None),
                    EmployeeSalaryAssignmentModel.effective_to >= period_start,
                ),
            )
            .order_by(
                EmployeeSalaryAssignmentModel.effective_from,
                EmployeeSalaryAssignmentModel.salary_assignment_id,
            )
        )
        return list(self.session.scalars(statement).all())

    def add(
        self, assignment: EmployeeSalaryAssignmentModel
    ) -> EmployeeSalaryAssignmentModel:
        self.session.add(assignment)
        self.session.flush()
        return assignment
