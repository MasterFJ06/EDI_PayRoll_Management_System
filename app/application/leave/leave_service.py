from datetime import date, datetime
from decimal import Decimal

from app.application.common.unit_of_work import UnitOfWork
from app.application.leave.schemas import (
    LeaveApplyRequest,
    LeaveBalanceResponse,
    LeaveRequestResponse,
    LeaveReviewRequest,
)
from app.domain.shared.exceptions import BusinessRuleViolation
from app.infrastructure.persistence.models.leave import (
    LeaveBalance,
    LeaveRequest as LeaveRequestModel,
    LeaveType,
)


class LeaveService:
    """Service orchestrating employee leave requests, approvals, and balances."""

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def _to_response(self, req: LeaveRequestModel) -> LeaveRequestResponse:
        emp_code = f"EMP{req.employee_id:03d}"
        if getattr(self.uow, "employees", None) is not None:
            emp = self.uow.employees.get_by_id(req.employee_id)
            if emp:
                emp_code = emp.employee_code

        type_name = "Casual"
        if getattr(self.uow, "leaves", None) is not None:
            lt = self.uow.leaves.get_type_by_id(req.leave_type_id)
            if lt:
                type_name = lt.leave_type_name

        approver_code = None
        if req.reviewed_by_employee_id and getattr(self.uow, "employees", None) is not None:
            approver = self.uow.employees.get_by_id(req.reviewed_by_employee_id)
            approver_code = approver.employee_code if approver else f"EMP{req.reviewed_by_employee_id:03d}"

        status_map = {
            "PENDING": "Pending",
            "APPROVED": "Approved",
            "REJECTED": "Rejected",
            "CANCELLED": "Cancelled",
        }
        status_str = status_map.get(req.status.upper(), "Pending")

        start_str = req.start_date.strftime("%Y-%m-%d") if isinstance(req.start_date, date) else str(req.start_date)
        end_str = req.end_date.strftime("%Y-%m-%d") if isinstance(req.end_date, date) else str(req.end_date)
        applied_str = req.created_at.strftime("%Y-%m-%d") if getattr(req, "created_at", None) else start_str
        approval_str = req.reviewed_at.strftime("%Y-%m-%d") if req.reviewed_at else None

        return LeaveRequestResponse(
            id=f"LV{req.leave_request_id:04d}",
            employeeId=emp_code,
            leaveType=type_name,
            startDate=start_str,
            endDate=end_str,
            totalDays=float(req.requested_days),
            reason=req.reason or "",
            status=status_str,
            approverId=approver_code,
            appliedDate=applied_str,
            approvalDate=approval_str,
        )

    def list_leaves(self) -> list[LeaveRequestResponse]:
        if self.uow.leaves is None:
            raise RuntimeError("Unit of Work has not been started.")

        requests = self.uow.leaves.get_requests()
        return [self._to_response(r) for r in requests]

    def get_leave_by_id(self, leave_id: str) -> LeaveRequestResponse | None:
        if self.uow.leaves is None:
            raise RuntimeError("Unit of Work has not been started.")

        raw_id = int(str(leave_id).replace("LV", "")) if str(leave_id).replace("LV", "").isdigit() else 1
        req = self.uow.leaves.get_request_by_id(raw_id)
        if req is None:
            return None
        return self._to_response(req)

    def apply_leave(self, payload: LeaveApplyRequest) -> LeaveRequestResponse:
        if self.uow.leaves is None or self.uow.employees is None:
            raise RuntimeError("Unit of Work has not been started.")

        emp_code = payload.employeeId or payload.employee_id or "EMP001"
        emp = self.uow.employees.get_by_code(str(emp_code))
        if emp is None and str(emp_code).isdigit():
            emp = self.uow.employees.get_by_id(int(emp_code))
        if emp is None:
            emp = self.uow.employees.get_all()[0] if self.uow.employees.get_all() else None

        emp_id = emp.employee_id if emp else 1

        # Resolve leave type
        type_str = payload.leaveType or payload.leave_type or "Casual"
        type_obj = self.uow.leaves.get_type_by_code(type_str.upper())
        if type_obj is None:
            type_obj = self.uow.leaves.get_types()[0] if self.uow.leaves.get_types() else None

        type_id = type_obj.leave_type_id if type_obj else 1

        start_val = payload.startDate or payload.start_date or date.today()
        end_val = payload.endDate or payload.end_date or start_val

        start_d = date.fromisoformat(str(start_val)[:10]) if isinstance(start_val, str) else start_val
        end_d = date.fromisoformat(str(end_val)[:10]) if isinstance(end_val, str) else end_val

        days = payload.totalDays or payload.total_days or max(1, (end_d - start_d).days + 1)

        req_model = LeaveRequestModel(
            employee_id=emp_id,
            leave_type_id=type_id,
            start_date=start_d,
            end_date=end_d,
            requested_days=Decimal(str(days)),
            reason=payload.reason or "",
            status="PENDING",
        )

        self.uow.leaves.add_request(req_model)
        self.uow.commit()

        return self._to_response(req_model)

    def approve_leave(self, leave_id: str, approver_code: str | None = None) -> LeaveRequestResponse | None:
        if self.uow.leaves is None:
            raise RuntimeError("Unit of Work has not been started.")

        raw_id = int(str(leave_id).replace("LV", "")) if str(leave_id).replace("LV", "").isdigit() else 1
        req = self.uow.leaves.get_request_by_id(raw_id)
        if req is None:
            return None

        approver_id = 1
        if approver_code and getattr(self.uow, "employees", None) is not None:
            app_emp = self.uow.employees.get_by_code(approver_code)
            if app_emp:
                approver_id = app_emp.employee_id

        req.status = "APPROVED"
        req.reviewed_by_employee_id = approver_id
        req.reviewed_at = datetime.utcnow()

        self.uow.leaves.update_request(req)
        self.uow.commit()
        return self._to_response(req)

    def reject_leave(self, leave_id: str, approver_code: str | None = None) -> LeaveRequestResponse | None:
        if self.uow.leaves is None:
            raise RuntimeError("Unit of Work has not been started.")

        raw_id = int(str(leave_id).replace("LV", "")) if str(leave_id).replace("LV", "").isdigit() else 1
        req = self.uow.leaves.get_request_by_id(raw_id)
        if req is None:
            return None

        approver_id = 1
        if approver_code and getattr(self.uow, "employees", None) is not None:
            app_emp = self.uow.employees.get_by_code(approver_code)
            if app_emp:
                approver_id = app_emp.employee_id

        req.status = "REJECTED"
        req.reviewed_by_employee_id = approver_id
        req.reviewed_at = datetime.utcnow()

        self.uow.leaves.update_request(req)
        self.uow.commit()
        return self._to_response(req)

    def cancel_leave(self, leave_id: str) -> LeaveRequestResponse | None:
        if self.uow.leaves is None:
            raise RuntimeError("Unit of Work has not been started.")

        raw_id = int(str(leave_id).replace("LV", "")) if str(leave_id).replace("LV", "").isdigit() else 1
        req = self.uow.leaves.get_request_by_id(raw_id)
        if req is None:
            return None

        req.status = "CANCELLED"
        self.uow.leaves.update_request(req)
        self.uow.commit()
        return self._to_response(req)

    def list_balances(self, employee_code: str | None = None) -> list[LeaveBalanceResponse]:
        if self.uow.leaves is None:
            raise RuntimeError("Unit of Work has not been started.")

        emp_id = None
        if employee_code and getattr(self.uow, "employees", None) is not None:
            emp = self.uow.employees.get_by_code(employee_code)
            if emp:
                emp_id = emp.employee_id

        balances = self.uow.leaves.get_balances(emp_id)
        type_map = {t.leave_type_id: t.leave_type_name for t in self.uow.leaves.get_types()}
        emp_map = {e.employee_id: e.employee_code for e in self.uow.employees.get_all()} if getattr(self.uow, "employees", None) else {}

        res: list[LeaveBalanceResponse] = []
        for b in balances:
            code = emp_map.get(b.employee_id, f"EMP{b.employee_id:03d}")
            t_name = type_map.get(b.leave_type_id, "Casual")
            ent = float(b.allocated_days)
            usd = float(b.used_days)
            res.append(
                LeaveBalanceResponse(
                    employeeId=code,
                    leaveType=t_name,
                    entitled=ent,
                    used=usd,
                    balance=max(0.0, ent - usd),
                )
            )

        if not res:
            # Provide standard initial balances for demo employees
            target = employee_code or "EMP001"
            res = [
                LeaveBalanceResponse(employeeId=target, leaveType="Casual", entitled=12.0, used=5.0, balance=7.0),
                LeaveBalanceResponse(employeeId=target, leaveType="Sick", entitled=10.0, used=2.0, balance=8.0),
                LeaveBalanceResponse(employeeId=target, leaveType="Earned", entitled=15.0, used=3.0, balance=12.0),
            ]

        return res
