from app.application.common.unit_of_work import UnitOfWork
from app.application.payroll.schemas import (
    PayrollProcessingIssueCreateRequest,
    PayrollProcessingIssueResponse,
)
from app.domain.payroll.payroll_processing_issue import PayrollProcessingIssue
from app.domain.shared.exceptions import BusinessRuleViolation
from app.infrastructure.persistence.models.payroll_processing_issue import (
    PayrollProcessingIssueModel,
)


class PayrollProcessingIssueService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def create(
        self,
        request: PayrollProcessingIssueCreateRequest,
        attempt_number: int,
        *,
        commit: bool = True,
    ) -> PayrollProcessingIssueResponse:
        if self.uow.payroll_runs.get_by_id(request.payroll_run_id) is None:
            raise BusinessRuleViolation("Payroll run does not exist.")
        if (
            self.uow.payroll_runs.lock_active_attempt(
                request.payroll_run_id, attempt_number
            )
            is None
        ):
            raise BusinessRuleViolation(
                "Payroll processing attempt is no longer active."
            )
        if request.employee_id is not None and self.uow.employees.get_by_id(
            request.employee_id
        ) is None:
            raise BusinessRuleViolation("Employee does not exist.")
        issue = PayrollProcessingIssue(
            payroll_issue_id=None,
            payroll_run_id=request.payroll_run_id,
            employee_id=request.employee_id,
            issue_code=request.issue_code,
            issue_message=request.issue_message,
            status=request.status,
            resolved_at=request.resolved_at,
        )
        model = PayrollProcessingIssueModel(
            payroll_run_id=issue.payroll_run_id,
            employee_id=issue.employee_id,
            issue_code=issue.issue_code,
            issue_message=issue.issue_message,
            status=issue.status,
            resolved_at=issue.resolved_at,
        )
        self.uow.payroll_processing_issues.add(model)
        if commit:
            self.uow.commit()
        return PayrollProcessingIssueResponse(
            payroll_issue_id=model.payroll_issue_id,
            payroll_run_id=model.payroll_run_id,
            employee_id=model.employee_id,
            issue_code=model.issue_code,
            issue_message=model.issue_message,
            status=model.status,
            resolved_at=model.resolved_at,
        )
