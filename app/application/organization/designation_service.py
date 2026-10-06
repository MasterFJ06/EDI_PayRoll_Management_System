from app.application.common.unit_of_work import UnitOfWork
from app.application.organization.schemas import (
    DesignationCreateRequest,
    DesignationResponse,
    DesignationUpdateRequest,
)
from app.domain.organization.designation import Designation
from app.domain.shared.exceptions import BusinessRuleViolation
from app.infrastructure.persistence.models.designation import (
    Designation as DesignationModel,
)


class DesignationService:
    """Application service for designation operations."""

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def _to_response(self, model: DesignationModel) -> DesignationResponse:
        code = model.designation_code
        name = model.designation_name
        status_str = "Active" if model.status.upper() == "ACTIVE" else "Inactive"
        created_str = model.created_at.strftime("%Y-%m-%d") if getattr(model, "created_at", None) else ""
        updated_str = model.updated_at.strftime("%Y-%m-%d") if getattr(model, "updated_at", None) else ""

        return DesignationResponse(
            designation_id=model.designation_id,
            designation_code=code,
            designation_name=name,
            status=model.status,
            id=f"DS{model.designation_id:02d}",
            code=code,
            name=name,
            description=f"{name} role.",
            hierarchyLevel=3,
            departmentId="D01",
            createdDate=created_str,
            updatedDate=updated_str,
        )

    def create(
        self,
        request: DesignationCreateRequest,
    ) -> DesignationResponse:
        """Create a new designation."""
        if self.uow.designations is None:
            raise RuntimeError("Unit of Work has not been started.")

        code = request.get_code().strip()
        name = request.get_name().strip()

        if not code:
            raise BusinessRuleViolation("Designation code cannot be blank.")
        if not name:
            raise BusinessRuleViolation("Designation name cannot be blank.")

        existing_code = self.uow.designations.get_by_code(code)
        if existing_code is not None:
            raise BusinessRuleViolation("Designation code is already registered.")

        existing_name = self.uow.designations.get_by_name(name)
        if existing_name is not None:
            raise BusinessRuleViolation("Designation name is already registered.")

        designation = Designation(
            designation_id=None,
            designation_code=code,
            designation_name=name,
        )

        designation_model = DesignationModel(
            designation_code=designation.designation_code,
            designation_name=designation.designation_name,
            status=designation.status,
        )

        self.uow.designations.add(designation_model)
        self.uow.commit()

        return self._to_response(designation_model)

    def list_all(self) -> list[DesignationResponse]:
        if self.uow.designations is None:
            raise RuntimeError("Unit of Work has not been started.")

        items = self.uow.designations.get_all()
        return [self._to_response(d) for d in items]

    def get_by_id(self, designation_id: int) -> DesignationResponse | None:
        if self.uow.designations is None:
            raise RuntimeError("Unit of Work has not been started.")

        item = self.uow.designations.get_by_id(designation_id)
        if item is None:
            return None
        return self._to_response(item)

    def update(
        self,
        designation_id: int,
        request: DesignationUpdateRequest,
    ) -> DesignationResponse | None:
        if self.uow.designations is None:
            raise RuntimeError("Unit of Work has not been started.")

        item = self.uow.designations.get_by_id(designation_id)
        if item is None:
            return None

        new_code = request.designation_code or request.code
        new_name = request.designation_name or request.name
        new_status = request.status

        if new_code:
            item.designation_code = new_code.strip()
        if new_name:
            item.designation_name = new_name.strip()
        if new_status:
            item.status = "ACTIVE" if new_status.upper() in {"ACTIVE"} else "INACTIVE"

        self.uow.designations.update(item)
        self.uow.commit()
        return self._to_response(item)

    def delete(self, designation_id: int) -> None:
        if self.uow.designations is None:
            raise RuntimeError("Unit of Work has not been started.")

        self.uow.designations.delete(designation_id)
        self.uow.commit()