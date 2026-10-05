from app.application.common.unit_of_work import UnitOfWork
from app.application.compensation.schemas import (
    SalaryRevisionComponentCreateRequest,
    SalaryRevisionComponentResponse,
)
from app.domain.compensation.salary_revision_component import SalaryRevisionComponent
from app.domain.shared.exceptions import BusinessRuleViolation
from app.infrastructure.persistence.models.salary_revision_component import (
    SalaryRevisionComponentModel,
)


class SalaryRevisionComponentService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def create(
        self, request: SalaryRevisionComponentCreateRequest
    ) -> SalaryRevisionComponentResponse:
        if self.uow.salary_revisions.get_by_id(request.salary_revision_id) is None:
            raise BusinessRuleViolation("Salary revision does not exist.")
        if self.uow.salary_components.get_by_id(request.salary_component_id) is None:
            raise BusinessRuleViolation("Salary component does not exist.")
        if request.base_component_id is not None and self.uow.salary_components.get_by_id(
            request.base_component_id
        ) is None:
            raise BusinessRuleViolation("Base salary component does not exist.")
        if self.uow.salary_revision_components.get_by_revision_and_component(
            request.salary_revision_id, request.salary_component_id
        ) is not None:
            raise BusinessRuleViolation("Salary component is already included in this revision.")
        component = SalaryRevisionComponent(
            salary_revision_id=request.salary_revision_id,
            salary_component_id=request.salary_component_id,
            calculation_type=request.calculation_type,
            fixed_amount=request.fixed_amount,
            percentage_value=request.percentage_value,
            base_component_id=request.base_component_id,
        )
        model = SalaryRevisionComponentModel(
            salary_revision_id=component.salary_revision_id,
            salary_component_id=component.salary_component_id,
            calculation_type=component.calculation_type,
            fixed_amount=component.fixed_amount,
            percentage_value=component.percentage_value,
            base_component_id=component.base_component_id,
        )
        self.uow.salary_revision_components.add(model)
        self.uow.commit()
        return SalaryRevisionComponentResponse(
            salary_revision_id=model.salary_revision_id,
            salary_component_id=model.salary_component_id,
            calculation_type=model.calculation_type,
            fixed_amount=model.fixed_amount,
            percentage_value=model.percentage_value,
            base_component_id=model.base_component_id,
        )
