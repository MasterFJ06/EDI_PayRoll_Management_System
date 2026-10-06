from datetime import datetime

from app.domain.shared.entity import Entity
from app.domain.shared.exceptions import BusinessRuleViolation


class PayrollRun(Entity[int]):
    """Domain entity representing a payroll processing batch/run."""

    CREATED = "CREATED"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    FINALIZED = "FINALIZED"

    VALID_STATUSES = {CREATED, PROCESSING, PROCESSED, FINALIZED}

    def __init__(
        self,
        payroll_run_id: int | None,
        payroll_year: int,
        payroll_month: int,
        initiated_by_user_id: int,
        status: str = CREATED,
    ) -> None:
        if not (1 <= payroll_month <= 12):
            raise BusinessRuleViolation(f"Invalid payroll month: {payroll_month}. Must be between 1 and 12.")

        if payroll_year < 2000 or payroll_year > 2100:
            raise BusinessRuleViolation(f"Invalid payroll year: {payroll_year}.")

        normalized_status = status.strip().upper()
        if normalized_status not in self.VALID_STATUSES:
            raise BusinessRuleViolation(f"Invalid payroll status: {status}.")

        super().__init__(payroll_run_id)

        self.payroll_year = payroll_year
        self.payroll_month = payroll_month
        self.initiated_by_user_id = initiated_by_user_id
        self.status = normalized_status
        self.started_at: datetime | None = None
        self.completed_at: datetime | None = None
        self.finalized_at: datetime | None = None

    def start_processing(self) -> None:
        if self.status != self.CREATED:
            raise BusinessRuleViolation("Payroll run can only be started from CREATED status.")
        self.status = self.PROCESSING
        self.started_at = datetime.utcnow()

    def complete_processing(self) -> None:
        if self.status != self.PROCESSING:
            raise BusinessRuleViolation("Payroll run must be in PROCESSING status to complete.")
        self.status = self.PROCESSED
        self.completed_at = datetime.utcnow()

    def finalize(self) -> None:
        if self.status != self.PROCESSED:
            raise BusinessRuleViolation("Only PROCESSED payroll runs can be finalized / approved.")
        self.status = self.FINALIZED
        self.finalized_at = datetime.utcnow()
