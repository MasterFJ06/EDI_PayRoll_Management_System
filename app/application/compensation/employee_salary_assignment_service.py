from app.application.common.unit_of_work import UnitOfWork
from app.application.compensation.schemas import (
    EmployeeSalaryAssignmentCreateRequest,
    EmployeeSalaryAssignmentResponse,
)
from app.domain.compensation.employee_salary_assignment import EmployeeSalaryAssignment
from app.domain.shared.exceptions import BusinessRuleViolation
from app.infrastructure.persistence.models.employee_salary_assignment import (
    EmployeeSalaryAssignmentModel,
)


class EmployeeSalaryAssignmentService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def create(
        self, request: EmployeeSalaryAssignmentCreateRequest
    ) -> EmployeeSalaryAssignmentResponse:
        if self.uow.employees.get_by_id(request.employee_id) is None:
            raise BusinessRuleViolation("Employee does not exist.")
        if self.uow.salary_revisions.get_by_id(request.salary_revision_id) is None:
            raise BusinessRuleViolation("Salary revision does not exist.")
        assignment = EmployeeSalaryAssignment(
            salary_assignment_id=None,
            employee_id=request.employee_id,
            salary_revision_id=request.salary_revision_id,
            effective_from=request.effective_from,
            effective_to=request.effective_to,
        )
        model = EmployeeSalaryAssignmentModel(
            employee_id=assignment.employee_id,
            salary_revision_id=assignment.salary_revision_id,
            effective_from=assignment.effective_from,
            effective_to=assignment.effective_to,
        )
        self.uow.employee_salary_assignments.add(model)
        self.uow.commit()
        return EmployeeSalaryAssignmentResponse(
            salary_assignment_id=model.salary_assignment_id,
            employee_id=model.employee_id,
            salary_revision_id=model.salary_revision_id,
            effective_from=model.effective_from,
            effective_to=model.effective_to,
        )
