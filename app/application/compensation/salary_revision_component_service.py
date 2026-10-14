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
        salary_component = self.uow.salary_components.get_by_id(request.salary_component_id)
        if salary_component is None:
            raise BusinessRuleViolation("Salary component does not exist.")
        if request.base_component_id is not None and self.uow.salary_components.get_by_id(
            request.base_component_id
        ) is None:
            raise BusinessRuleViolation("Base salary component does not exist.")
        if self.uow.salary_revision_components.get_by_revision_and_component(
            request.salary_revision_id, request.salary_component_id
        ) is not None:
            raise BusinessRuleViolation("Salary component is already included in this revision.")
        revision_components = self.uow.salary_revision_components.get_by_revision(
            request.salary_revision_id
        )
        if request.is_overtime_base and any(
            item.is_overtime_base
            for item in revision_components
        ):
            raise BusinessRuleViolation("A salary revision can designate only one overtime base component.")
        component = SalaryRevisionComponent(
            salary_revision_id=request.salary_revision_id,
            salary_component_id=request.salary_component_id,
            calculation_type=request.calculation_type,
            fixed_amount=request.fixed_amount,
            percentage_value=request.percentage_value,
            base_component_id=request.base_component_id,
            is_overtime_base=request.is_overtime_base,
            component_type=salary_component.component_type,
        )
        dependencies = {
            item.salary_component_id: item.base_component_id
            for item in revision_components
        }
        dependencies[component.salary_component_id] = component.base_component_id
        if _contains_dependency_cycle(dependencies):
            raise BusinessRuleViolation(
                "Salary component dependencies contain a cycle."
            )
        model = SalaryRevisionComponentModel(
            salary_revision_id=component.salary_revision_id,
            salary_component_id=component.salary_component_id,
            calculation_type=component.calculation_type,
            fixed_amount=component.fixed_amount,
            percentage_value=component.percentage_value,
            base_component_id=component.base_component_id,
            is_overtime_base=component.is_overtime_base,
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
            is_overtime_base=model.is_overtime_base,
        )


def _contains_dependency_cycle(dependencies: dict[int, int | None]) -> bool:
    """Return whether revision component base references contain a cycle."""
    visiting: set[int] = set()
    visited: set[int] = set()

    def visit(component_id: int) -> bool:
        if component_id in visiting:
            return True
        if component_id in visited:
            return False
        visiting.add(component_id)
        base_component_id = dependencies.get(component_id)
        if base_component_id in dependencies and visit(base_component_id):
            return True
        visiting.remove(component_id)
        visited.add(component_id)
        return False

    return any(visit(component_id) for component_id in dependencies)
