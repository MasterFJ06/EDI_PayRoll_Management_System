from datetime import date, datetime
from decimal import Decimal

from app.domain.shared.entity import Entity
from app.domain.shared.exceptions import BusinessRuleViolation


class LeaveRequest(Entity[int | None]):
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
        requested_days: Decimal,
        reason: str | None = None,
        status: str = PENDING,
        reviewed_by_employee_id: int | None = None,
        reviewed_at: datetime | None = None,
        review_comment: str | None = None,
    ) -> None:
        if employee_id <= 0 or leave_type_id <= 0:
            raise BusinessRuleViolation("Employee and leave type IDs must be positive.")
        if end_date < start_date:
            raise BusinessRuleViolation("Leave request end date cannot precede start date.")
        days = Decimal(requested_days)
        if days <= 0:
            raise BusinessRuleViolation("Requested leave days must be positive.")
        normalized_status = status.strip().upper()
        if normalized_status not in self.VALID_STATUSES:
            raise BusinessRuleViolation("Leave request status is invalid.")
        if normalized_status == self.PENDING and (
            reviewed_by_employee_id is not None or reviewed_at is not None
        ):
            raise BusinessRuleViolation("Pending leave requests cannot have review details.")
        if normalized_status in {self.APPROVED, self.REJECTED} and (
            reviewed_by_employee_id is None or reviewed_at is None
        ):
            raise BusinessRuleViolation("Approved or rejected requests require reviewer and review time.")
        if reviewed_by_employee_id is not None and reviewed_by_employee_id <= 0:
            raise BusinessRuleViolation("Reviewer employee ID must be positive.")
        normalized_reason = reason.strip() if reason is not None else None
        normalized_comment = review_comment.strip() if review_comment is not None else None
        if normalized_reason is not None and len(normalized_reason) > 1000:
            raise BusinessRuleViolation("Leave request reason cannot exceed 1000 characters.")
        if normalized_comment is not None and len(normalized_comment) > 1000:
            raise BusinessRuleViolation("Review comment cannot exceed 1000 characters.")
        super().__init__(leave_request_id)
        self.employee_id = employee_id
        self.leave_type_id = leave_type_id
        self.start_date = start_date
        self.end_date = end_date
        self.requested_days = days
        self.reason = normalized_reason
        self.status = normalized_status
        self.reviewed_by_employee_id = reviewed_by_employee_id
        self.reviewed_at = reviewed_at
        self.review_comment = normalized_comment
