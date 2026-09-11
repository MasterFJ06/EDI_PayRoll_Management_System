from app.application.common.unit_of_work import UnitOfWork
from app.application.organization.schemas import (
    DepartmentCreateRequest,
    DepartmentResponse,
)
from app.domain.organization.department import Department
from app.domain.shared.exceptions import BusinessRuleViolation
from app.infrastructure.persistence.models.department import Department as DepartmentModel


class DepartmentService:
    """Application service for department operations."""

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def create(
        self,
        request: DepartmentCreateRequest,
    ) -> DepartmentResponse:
        """Create a new department."""

        if self.uow.departments is None:
            raise RuntimeError("Unit of Work has not been started.")

        existing_code = self.uow.departments.get_by_code(
            request.department_code.strip()
        )

        if existing_code is not None:
            raise BusinessRuleViolation(
                "Department code is already registered."
            )

        existing_name = self.uow.departments.get_by_name(
            request.department_name.strip()
        )

        if existing_name is not None:
            raise BusinessRuleViolation(
                "Department name is already registered."
            )

        department = Department(
            department_id=None,
            department_code=request.department_code,
            department_name=request.department_name,
        )

        department_model = DepartmentModel(
            department_code=department.department_code,
            department_name=department.department_name,
            status=department.status,
        )

        self.uow.departments.add(department_model)
        self.uow.commit()

        return DepartmentResponse(
            department_id=department_model.department_id,
            department_code=department_model.department_code,
            department_name=department_model.department_name,
            status=department_model.status,
        )