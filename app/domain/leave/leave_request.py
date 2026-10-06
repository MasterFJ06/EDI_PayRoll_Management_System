from datetime import date
from decimal import Decimal

from app.domain.shared.entity import Entity
from app.domain.shared.exceptions import BusinessRuleViolation


class LeaveRequest(Entity[int]):
    """Domain entity representing an employee leave request."""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"

    VALID_STATUSES = {PENDING, APPROVED, REJECTED, CANCELLED}

    def __init__(
        self,
        leave_request_id: int | None,
        employee_id: int,
        leave_type_id: int,
        start_date: date,
        end_date: date,
        requested_days: Decimal | float,
        reason: str | None = None,
        status: str = PENDING,
    ) -> None:
        if end_date < start_date:
            raise BusinessRuleViolation("Leave end date cannot be earlier than start date.")

        if Decimal(str(requested_days)) <= 0:
            raise BusinessRuleViolation("Requested days must be greater than zero.")

        normalized_status = status.strip().upper()
        if normalized_status not in self.VALID_STATUSES:
            raise BusinessRuleViolation(f"Invalid leave request status: {status}")

        super().__init__(leave_request_id)

        self.employee_id = employee_id
        self.leave_type_id = leave_type_id
        self.start_date = start_date
        self.end_date = end_date
        self.requested_days = Decimal(str(requested_days))
        self.reason = reason
        self.status = normalized_status
        self.reviewed_by_employee_id: int | None = None
        self.review_comment: str | None = None

    def approve(self, reviewer_employee_id: int, comment: str | None = None) -> None:
        if self.status != self.PENDING:
            raise BusinessRuleViolation("Only PENDING leave requests can be approved.")
        self.status = self.APPROVED
        self.reviewed_by_employee_id = reviewer_employee_id
        self.review_comment = comment

    def reject(self, reviewer_employee_id: int, comment: str | None = None) -> None:
        if self.status != self.PENDING:
            raise BusinessRuleViolation("Only PENDING leave requests can be rejected.")
        self.status = self.REJECTED
        self.reviewed_by_employee_id = reviewer_employee_id
        self.review_comment = comment

    def cancel(self) -> None:
        if self.status in {self.REJECTED, self.CANCELLED}:
            raise BusinessRuleViolation(f"Cannot cancel a request that is already {self.status}.")
        self.status = self.CANCELLED
