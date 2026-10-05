from datetime import datetime

from app.domain.shared.entity import Entity
from app.domain.shared.exceptions import BusinessRuleViolation


class PayrollProcessingIssue(Entity[int | None]):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"
    VALID_STATUSES = {OPEN, RESOLVED}

    def __init__(
        self,
        payroll_issue_id: int | None,
        payroll_run_id: int,
        issue_code: str,
        issue_message: str,
        employee_id: int | None = None,
        status: str = OPEN,
        resolved_at: datetime | None = None,
    ) -> None:
        if payroll_run_id <= 0 or (employee_id is not None and employee_id <= 0):
            raise BusinessRuleViolation("Payroll run and employee IDs must be positive.")
        normalized_status = status.strip().upper()
        if normalized_status not in self.VALID_STATUSES:
            raise BusinessRuleViolation("Payroll issue status must be OPEN or RESOLVED.")
        if (normalized_status == self.OPEN) != (resolved_at is None):
            raise BusinessRuleViolation("Payroll issue status and resolution time are inconsistent.")
        super().__init__(payroll_issue_id)
        self.payroll_run_id = payroll_run_id
        self.employee_id = employee_id
        self.issue_code = issue_code
        self.issue_message = issue_message
        self.status = normalized_status
        self.resolved_at = resolved_at
