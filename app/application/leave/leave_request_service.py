from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.exc import IntegrityError

from app.application.common.unit_of_work import UnitOfWork
from app.application.leave.schemas import (
    LeaveRequestCreateRequest,
    LeaveRequestDayResponse,
    LeaveRequestResponse,
)
from app.application.organization.work_calendar_service import WorkCalendarService
from app.domain.leave.leave_request import LeaveRequest
from app.domain.leave.leave_request_day import LeaveRequestDay
from app.domain.shared.exceptions import BusinessRuleViolation
from app.infrastructure.persistence.models.audit_event import AuditEventModel
from app.infrastructure.persistence.models.audit_event_change import AuditEventChangeModel
from app.infrastructure.persistence.models.leave_request import LeaveRequestModel


class LeaveRequestService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def create(
        self,
        request: LeaveRequestCreateRequest,
        actor_user_id: int,
        correlation_id: str | None,
    ) -> LeaveRequestResponse:
        if self.uow.employees.get_by_id(request.employee_id) is None:
            raise BusinessRuleViolation("Employee does not exist.")
        if self.uow.leave_types.get_by_id(request.leave_type_id) is None:
            raise BusinessRuleViolation("Leave type does not exist.")

        leave_request = LeaveRequest(
            leave_request_id=None,
            employee_id=request.employee_id,
            leave_type_id=request.leave_type_id,
            start_date=request.start_date,
            end_date=request.end_date,
            requested_days=request.requested_days,
            reason=request.reason,
            status=LeaveRequest.PENDING,
        )
        allocations = self._validate_allocations(
            request.allocations,
            leave_request.start_date,
            leave_request.end_date,
            leave_request.requested_days,
        )
        model = LeaveRequestModel(
            employee_id=leave_request.employee_id,
            leave_type_id=leave_request.leave_type_id,
            start_date=leave_request.start_date,
            end_date=leave_request.end_date,
            requested_days=leave_request.requested_days,
            reason=leave_request.reason,
            status=LeaveRequest.PENDING,
        )
        try:
            self.uow.leave_requests.add(model)
            self.uow.leave_requests.add_days(model.leave_request_id, allocations)
            self.uow.audit_events.add(
                AuditEventModel(
                    actor_user_id=actor_user_id,
                    action_type="LEAVE_REQUEST_CREATED",
                    resource_type="LEAVE_REQUEST",
                    resource_id=model.leave_request_id,
                    correlation_id=correlation_id,
                ),
                [
                    AuditEventChangeModel(
                        field_name="status", old_value=None, new_value=LeaveRequest.PENDING
                    ),
                    AuditEventChangeModel(
                        field_name="requested_days",
                        old_value=None,
                        new_value=str(leave_request.requested_days),
                    ),
                    AuditEventChangeModel(
                        field_name="allocation_count",
                        old_value=None,
                        new_value=str(len(allocations)),
                    ),
                ],
            )
            self.uow.commit()
        except IntegrityError as exc:
            self.uow.rollback()
            raise BusinessRuleViolation(
                "Leave request or date allocation conflicts with existing data."
            ) from exc
        model.status = LeaveRequest.PENDING
        return self._response(model, allocations)

    def approve(
        self,
        leave_request_id: int,
        actor_user_id: int,
        correlation_id: str | None,
        review_comment: str | None = None,
    ) -> LeaveRequestResponse | None:
        model = self._get_request(leave_request_id)
        if model is None:
            return None
        LeaveRequest.ensure_transition(model.status, LeaveRequest.APPROVED)

        reviewer = self.uow.employees.get_by_user_id(actor_user_id)
        if reviewer is None:
            raise BusinessRuleViolation("Approving user is not linked to an employee.")
        employee = self.uow.employees.get_by_id_for_update(model.employee_id)
        if employee is None:
            raise BusinessRuleViolation("Employee does not exist.")

        leave_type = self.uow.leave_types.get_by_id(model.leave_type_id)
        if leave_type is None:
            raise BusinessRuleViolation("Leave type does not exist.")
        if getattr(leave_type, "payroll_treatment", None) not in {"PAID", "UNPAID"}:
            raise BusinessRuleViolation(
                "Leave type payroll treatment is unresolved; approval is blocked."
            )

        persisted_days = self.uow.leave_requests.get_days(leave_request_id)
        allocations = [
            LeaveRequestDay(day.leave_date, Decimal(day.day_fraction))
            for day in persisted_days
        ]
        if not allocations:
            raise BusinessRuleViolation("Leave request requires date allocations before approval.")
        self._validate_domain_allocations(
            allocations, model.start_date, model.end_date, Decimal(model.requested_days)
        )
        conflicts = self.uow.leave_requests.find_approved_conflicts(
            model.employee_id,
            [item.leave_date for item in allocations],
            leave_request_id,
        )
        if conflicts:
            dates = ", ".join(sorted({item.isoformat() for item in conflicts}))
            raise BusinessRuleViolation(f"Approved leave already exists for date(s): {dates}.")

        now = datetime.now()
        comment = review_comment.strip() if review_comment else None
        previous_status = model.status
        try:
            if not self.uow.leave_requests.transition_status(
                leave_request_id,
                LeaveRequest.PENDING,
                LeaveRequest.APPROVED,
                reviewer.employee_id,
                now,
                comment,
            ):
                raise BusinessRuleViolation("Leave request changed concurrently; retry approval.")
            self._audit_transition(
                model,
                actor_user_id,
                correlation_id,
                "LEAVE_REQUEST_APPROVED",
                LeaveRequest.APPROVED,
                previous_status,
            )
            self.uow.commit()
        except IntegrityError as exc:
            self.uow.rollback()
            raise BusinessRuleViolation("Leave request approval conflicts with another request.") from exc
        model.status = LeaveRequest.APPROVED
        model.reviewed_by_employee_id = reviewer.employee_id
        model.reviewed_at = now
        model.review_comment = comment
        return self._response(model, allocations)

    def reject(
        self,
        leave_request_id: int,
        actor_user_id: int,
        correlation_id: str | None,
        review_comment: str | None = None,
    ) -> LeaveRequestResponse | None:
        model = self._get_request(leave_request_id)
        if model is None:
            return None
        LeaveRequest.ensure_transition(model.status, LeaveRequest.REJECTED)
        reviewer = self.uow.employees.get_by_user_id(actor_user_id)
        if reviewer is None:
            raise BusinessRuleViolation("Rejecting user is not linked to an employee.")
        now = datetime.now()
        comment = review_comment.strip() if review_comment else None
        return self._transition(
            model,
            LeaveRequest.PENDING,
            LeaveRequest.REJECTED,
            actor_user_id,
            correlation_id,
            "LEAVE_REQUEST_REJECTED",
            reviewer.employee_id,
            now,
            comment,
        )

    def cancel(
        self,
        leave_request_id: int,
        actor_user_id: int,
        correlation_id: str | None,
    ) -> LeaveRequestResponse | None:
        model = self._get_request(leave_request_id)
        if model is None:
            return None
        LeaveRequest.ensure_transition(model.status, LeaveRequest.CANCELLED)
        return self._transition(
            model,
            model.status,
            LeaveRequest.CANCELLED,
            actor_user_id,
            correlation_id,
            "LEAVE_REQUEST_CANCELLED",
        )

    def _transition(
        self,
        model: LeaveRequestModel,
        expected_status: str,
        target_status: str,
        actor_user_id: int,
        correlation_id: str | None,
        action: str,
        reviewer_employee_id: int | None = None,
        reviewed_at: datetime | None = None,
        review_comment: str | None = None,
    ) -> LeaveRequestResponse:
        try:
            previous_status = model.status
            if not self.uow.leave_requests.transition_status(
                model.leave_request_id,
                expected_status,
                target_status,
                reviewer_employee_id,
                reviewed_at,
                review_comment,
            ):
                raise BusinessRuleViolation("Leave request changed concurrently; retry the operation.")
            self._audit_transition(
                model, actor_user_id, correlation_id, action, target_status, previous_status
            )
            self.uow.commit()
        except IntegrityError as exc:
            self.uow.rollback()
            raise BusinessRuleViolation("Leave request transition conflicts with its current state.") from exc
        model.status = target_status
        if target_status in {LeaveRequest.APPROVED, LeaveRequest.REJECTED}:
            model.reviewed_by_employee_id = reviewer_employee_id
            model.reviewed_at = reviewed_at
            model.review_comment = review_comment
        return self._response(model, self.uow.leave_requests.get_days(model.leave_request_id))

    def _get_request(self, leave_request_id: int) -> LeaveRequestModel | None:
        return self.uow.leave_requests.get_by_id(leave_request_id)

    def _audit_transition(
        self,
        model: LeaveRequestModel,
        actor_user_id: int,
        correlation_id: str | None,
        action: str,
        new_status: str,
        old_status: str,
    ) -> None:
        self.uow.audit_events.add(
            AuditEventModel(
                actor_user_id=actor_user_id,
                action_type=action,
                resource_type="LEAVE_REQUEST",
                resource_id=model.leave_request_id,
                correlation_id=correlation_id,
            ),
            [
                AuditEventChangeModel(
                    field_name="status", old_value=old_status, new_value=new_status
                )
            ],
        )

    def _validate_allocations(
        self, inputs: list[object], start_date: date, end_date: date, requested_days: Decimal
    ) -> list[LeaveRequestDay]:
        allocations = [
            LeaveRequestDay(item.leave_date, item.day_fraction) for item in inputs
        ]
        self._validate_domain_allocations(allocations, start_date, end_date, requested_days)
        return allocations

    def _validate_domain_allocations(
        self,
        allocations: list[LeaveRequestDay],
        start_date: date,
        end_date: date,
        requested_days: Decimal,
    ) -> None:
        total = Decimal("0.00")
        seen_dates: set[date] = set()
        calendar = WorkCalendarService(self.uow)
        for allocation in allocations:
            if allocation.leave_date < start_date or allocation.leave_date > end_date:
                raise BusinessRuleViolation(
                    "Leave allocation dates must be within the request's start and end dates."
                )
            if allocation.leave_date in seen_dates:
                raise BusinessRuleViolation("A leave request may contain one allocation per date.")
            seen_dates.add(allocation.leave_date)
            day = calendar.classify_date(allocation.leave_date)
            if day.classification != "WORKING_DAY":
                raise BusinessRuleViolation(
                    f"Leave allocation date {allocation.leave_date.isoformat()} is not a WORKING_DAY."
                )
            total += allocation.day_fraction
        if total != requested_days:
            raise BusinessRuleViolation(
                f"Leave allocation total {total:.2f} must equal requested_days {requested_days:.2f}."
            )

    @staticmethod
    def _response(model: LeaveRequestModel, allocations: list[object]) -> LeaveRequestResponse:
        return LeaveRequestResponse(
            leave_request_id=model.leave_request_id,
            employee_id=model.employee_id,
            leave_type_id=model.leave_type_id,
            start_date=model.start_date,
            end_date=model.end_date,
            requested_days=model.requested_days,
            reason=model.reason,
            status=model.status,
            reviewed_by_employee_id=model.reviewed_by_employee_id,
            reviewed_at=model.reviewed_at,
            review_comment=model.review_comment,
            allocations=[
                LeaveRequestDayResponse(
                    leave_date=item.leave_date,
                    day_fraction=item.day_fraction,
                )
                for item in allocations
            ],
        )
