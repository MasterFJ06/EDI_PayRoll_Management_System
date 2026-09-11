from app.application.common.unit_of_work import UnitOfWork
from app.application.organization.schemas import (
    DesignationCreateRequest,
    DesignationResponse,
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

    def create(
        self,
        request: DesignationCreateRequest,
    ) -> DesignationResponse:
        """Create a new designation."""

        if self.uow.designations is None:
            raise RuntimeError("Unit of Work has not been started.")

        existing_code = self.uow.designations.get_by_code(
            request.designation_code.strip()
        )

        if existing_code is not None:
            raise BusinessRuleViolation(
                "Designation code is already registered."
            )

        existing_name = self.uow.designations.get_by_name(
            request.designation_name.strip()
        )

        if existing_name is not None:
            raise BusinessRuleViolation(
                "Designation name is already registered."
            )

        designation = Designation(
            designation_id=None,
            designation_code=request.designation_code,
            designation_name=request.designation_name,
        )

        designation_model = DesignationModel(
            designation_code=designation.designation_code,
            designation_name=designation.designation_name,
            status=designation.status,
        )

        self.uow.designations.add(designation_model)
        self.uow.commit()

        return DesignationResponse(
            designation_id=designation_model.designation_id,
            designation_code=designation_model.designation_code,
            designation_name=designation_model.designation_name,
            status=designation_model.status,
        )