from app.application.common.unit_of_work import UnitOfWork
from app.application.compensation.schemas import (
    SalaryComponentCreateRequest,
    SalaryComponentResponse,
)
from app.domain.compensation.salary_component import SalaryComponent
from app.domain.shared.exceptions import BusinessRuleViolation
from app.infrastructure.persistence.models.salary_component import SalaryComponentModel


class SalaryComponentService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def create(self, request: SalaryComponentCreateRequest) -> SalaryComponentResponse:
        component = SalaryComponent(
            salary_component_id=None,
            component_code=request.component_code,
            component_name=request.component_name,
            component_type=request.component_type,
            status=request.status,
        )
        if self.uow.salary_components.get_by_code(component.component_code) is not None:
            raise BusinessRuleViolation("Salary component code is already registered.")
        model = SalaryComponentModel(
            component_code=component.component_code,
            component_name=component.component_name,
            component_type=component.component_type,
            status=component.status,
        )
        self.uow.salary_components.add(model)
        self.uow.commit()
        return SalaryComponentResponse(
            salary_component_id=model.salary_component_id,
            component_code=model.component_code,
            component_name=model.component_name,
            component_type=model.component_type,
            status=model.status,
        )
