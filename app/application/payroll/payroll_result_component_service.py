from app.application.common.unit_of_work import UnitOfWork
from app.application.payroll.schemas import (
    PayrollResultComponentCreateRequest,
    PayrollResultComponentResponse,
)
from app.domain.payroll.payroll_result_component import PayrollResultComponent
from app.domain.shared.exceptions import BusinessRuleViolation
from app.infrastructure.persistence.models.payroll_result_component import (
    PayrollResultComponentModel,
)


class PayrollResultComponentService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def create(
        self, request: PayrollResultComponentCreateRequest
    ) -> PayrollResultComponentResponse:
        if self.uow.payroll_results.get_by_id(request.payroll_result_id) is None:
            raise BusinessRuleViolation("Payroll result does not exist.")
        if self.uow.salary_components.get_by_id(request.salary_component_id) is None:
            raise BusinessRuleViolation("Salary component does not exist.")
        if self.uow.payroll_result_components.get_by_result_and_component(
            request.payroll_result_id, request.salary_component_id
        ) is not None:
            raise BusinessRuleViolation("This salary component is already recorded for the result.")
        component = PayrollResultComponent(
            payroll_result_component_id=None,
            payroll_result_id=request.payroll_result_id,
            salary_component_id=request.salary_component_id,
            component_type=request.component_type,
            amount=request.amount,
            calculation_order=request.calculation_order,
        )
        model = PayrollResultComponentModel(
            payroll_result_id=component.payroll_result_id,
            salary_component_id=component.salary_component_id,
            component_type=component.component_type,
            amount=component.amount,
            calculation_order=component.calculation_order,
        )
        self.uow.payroll_result_components.add(model)
        self.uow.commit()
        return PayrollResultComponentResponse(
            payroll_result_component_id=model.payroll_result_component_id,
            payroll_result_id=model.payroll_result_id,
            salary_component_id=model.salary_component_id,
            component_type=model.component_type,
            amount=model.amount,
            calculation_order=model.calculation_order,
        )
