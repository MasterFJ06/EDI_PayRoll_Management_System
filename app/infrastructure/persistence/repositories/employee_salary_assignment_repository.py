from sqlalchemy import select
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

    def add(
        self, assignment: EmployeeSalaryAssignmentModel
    ) -> EmployeeSalaryAssignmentModel:
        self.session.add(assignment)
        self.session.flush()
        return assignment
