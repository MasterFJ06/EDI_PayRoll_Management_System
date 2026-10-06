from app.application.common.unit_of_work import UnitOfWork
from app.application.organization.schemas import (
    DepartmentCreateRequest,
    DepartmentResponse,
    DepartmentUpdateRequest,
)
from app.domain.organization.department import Department
from app.domain.shared.exceptions import BusinessRuleViolation
from app.infrastructure.persistence.models.department import Department as DepartmentModel


class DepartmentService:
    """Application service for department operations."""

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def _to_response(self, model: DepartmentModel) -> DepartmentResponse:
        code = model.department_code
        name = model.department_name
        status_str = "Active" if model.status.upper() == "ACTIVE" else "Inactive"
        created_str = model.created_at.strftime("%Y-%m-%d") if getattr(model, "created_at", None) else ""
        updated_str = model.updated_at.strftime("%Y-%m-%d") if getattr(model, "updated_at", None) else ""

        emp_count = 0
        
        return DepartmentResponse(
            department_id=model.department_id,
            department_code=code,
            department_name=name,
            status=model.status,
            id=f"D{model.department_id:02d}",
            code=code,
            name=name,
            description=f"{name} department.",
            headEmployeeId=None,
            headName=None,
            employeeCount=emp_count,
            createdDate=created_str,
            updatedDate=updated_str,
        )

    def create(
        self,
        request: DepartmentCreateRequest,
    ) -> DepartmentResponse:
        """Create a new department."""
        if self.uow.departments is None:
            raise RuntimeError("Unit of Work has not been started.")

        code = request.get_code().strip()
        name = request.get_name().strip()

        if not code:
            raise BusinessRuleViolation("Department code cannot be blank.")
        if not name:
            raise BusinessRuleViolation("Department name cannot be blank.")

        existing_code = self.uow.departments.get_by_code(code)
        if existing_code is not None:
            raise BusinessRuleViolation("Department code is already registered.")

        existing_name = self.uow.departments.get_by_name(name)
        if existing_name is not None:
            raise BusinessRuleViolation("Department name is already registered.")

        department = Department(
            department_id=None,
            department_code=code,
            department_name=name,
        )

        department_model = DepartmentModel(
            department_code=department.department_code,
            department_name=department.department_name,
            status=department.status,
        )

        self.uow.departments.add(department_model)
        self.uow.commit()

        return self._to_response(department_model)

    def list_all(self) -> list[DepartmentResponse]:
        if self.uow.departments is None:
            raise RuntimeError("Unit of Work has not been started.")

        depts = self.uow.departments.get_all()
        return [self._to_response(d) for d in depts]

    def get_by_id(self, dept_id: int) -> DepartmentResponse | None:
        if self.uow.departments is None:
            raise RuntimeError("Unit of Work has not been started.")

        dept = self.uow.departments.get_by_id(dept_id)
        if dept is None:
            return None
        return self._to_response(dept)

    def update(self, dept_id: int, request: DepartmentUpdateRequest) -> DepartmentResponse | None:
        if self.uow.departments is None:
            raise RuntimeError("Unit of Work has not been started.")

        dept = self.uow.departments.get_by_id(dept_id)
        if dept is None:
            return None

        new_code = request.department_code or request.code
        new_name = request.department_name or request.name
        new_status = request.status

        if new_code:
            dept.department_code = new_code.strip()
        if new_name:
            dept.department_name = new_name.strip()
        if new_status:
            dept.status = "ACTIVE" if new_status.upper() in {"ACTIVE"} else "INACTIVE"

        self.uow.departments.update(dept)
        self.uow.commit()
        return self._to_response(dept)

    def delete(self, dept_id: int) -> None:
        if self.uow.departments is None:
            raise RuntimeError("Unit of Work has not been started.")

        self.uow.departments.delete(dept_id)
        self.uow.commit()