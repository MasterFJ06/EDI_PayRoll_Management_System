from app.application.common.unit_of_work import UnitOfWork
from app.application.payroll.schemas import PayrollResultCreateRequest, PayrollResultResponse
from app.domain.payroll.payroll_result import PayrollResult
from app.domain.shared.exceptions import BusinessRuleViolation
from app.infrastructure.persistence.models.payroll_result import PayrollResultModel


class PayrollResultService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def create(self, request: PayrollResultCreateRequest) -> PayrollResultResponse:
        if self.uow.payroll_runs.get_by_id(request.payroll_run_id) is None:
            raise BusinessRuleViolation("Payroll run does not exist.")
        if self.uow.employees.get_by_id(request.employee_id) is None:
            raise BusinessRuleViolation("Employee does not exist.")
        if self.uow.employee_salary_assignments.get_by_id(request.salary_assignment_id) is None:
            raise BusinessRuleViolation("Salary assignment does not exist.")
        if self.uow.payroll_results.get_by_run_and_employee(
            request.payroll_run_id, request.employee_id
        ) is not None:
            raise BusinessRuleViolation("A result already exists for this employee and payroll run.")
        result = PayrollResult(
            payroll_result_id=None,
            payroll_run_id=request.payroll_run_id,
            employee_id=request.employee_id,
            salary_assignment_id=request.salary_assignment_id,
            gross_earnings=request.gross_earnings,
            total_deductions=request.total_deductions,
            net_salary=request.net_salary,
        )
        model = PayrollResultModel(
            payroll_run_id=result.payroll_run_id,
            employee_id=result.employee_id,
            salary_assignment_id=result.salary_assignment_id,
            gross_earnings=result.gross_earnings,
            total_deductions=result.total_deductions,
            net_salary=result.net_salary,
        )
        self.uow.payroll_results.add(model)
        self.uow.commit()
        return PayrollResultResponse(
            payroll_result_id=model.payroll_result_id,
            payroll_run_id=model.payroll_run_id,
            employee_id=model.employee_id,
            salary_assignment_id=model.salary_assignment_id,
            gross_earnings=model.gross_earnings,
            total_deductions=model.total_deductions,
            net_salary=model.net_salary,
        )
