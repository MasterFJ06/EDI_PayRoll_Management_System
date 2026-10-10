from datetime import datetime

from app.domain.shared.entity import Entity
from app.domain.shared.exceptions import BusinessRuleViolation


class PayrollRun(Entity[int | None]):
    CREATED = "CREATED"
    PROCESSING = "PROCESSING"
    FAILED = "FAILED"
    PROCESSED = "PROCESSED"
    FINALIZED = "FINALIZED"
    VALID_STATUSES = {CREATED, PROCESSING, FAILED, PROCESSED, FINALIZED}

    def __init__(
        self,
        payroll_run_id: int | None,
        payroll_year: int,
        payroll_month: int,
        initiated_by_user_id: int,
        status: str = CREATED,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        finalized_at: datetime | None = None,
        attempt_number: int = 0,
        attempt_lease_expires_at: datetime | None = None,
    ) -> None:
        if not 0 <= payroll_year <= 65535:
            raise BusinessRuleViolation("Payroll year must fit SMALLINT UNSIGNED.")
        if not 1 <= payroll_month <= 12:
            raise BusinessRuleViolation("Payroll month must be between 1 and 12.")
        if initiated_by_user_id <= 0:
            raise BusinessRuleViolation("Initiating user ID must be positive.")
        normalized_status = status.strip().upper()
        if normalized_status not in self.VALID_STATUSES:
            raise BusinessRuleViolation("Payroll run status is invalid.")
        super().__init__(payroll_run_id)
        self.payroll_year = payroll_year
        self.payroll_month = payroll_month
        self.initiated_by_user_id = initiated_by_user_id
        self.status = normalized_status
        self.started_at = started_at
        self.completed_at = completed_at
        self.finalized_at = finalized_at
        self.attempt_number = attempt_number
        self.attempt_lease_expires_at = attempt_lease_expires_at
