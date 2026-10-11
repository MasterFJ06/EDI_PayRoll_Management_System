from datetime import date

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.domain.leave.leave_report import (
    LeaveAllocationReportRecord,
    LeaveBalanceReportRecord,
)
from app.infrastructure.persistence.models.department import Department
from app.infrastructure.persistence.models.designation import Designation
from app.infrastructure.persistence.models.employee import Employee
from app.infrastructure.persistence.models.leave_balance import LeaveBalanceModel
from app.infrastructure.persistence.models.leave_request import LeaveRequestModel
from app.infrastructure.persistence.models.leave_request_day import LeaveRequestDayModel
from app.infrastructure.persistence.models.leave_type import LeaveTypeModel


class LeaveReportRepository:
    """Read-only SQL projections for the organization-wide Leave reports."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_allocation_report_page(
        self,
        date_from: date | None,
        date_to: date | None,
        employee_id: int | None,
        department_id: int | None,
        leave_type_id: int | None,
        status: str | None,
        after_leave_date: date | None,
        after_leave_request_day_id: int | None,
        limit: int,
    ) -> list[LeaveAllocationReportRecord]:
        statement = (
            select(
                LeaveRequestModel.leave_request_id,
                LeaveRequestDayModel.leave_request_day_id,
                Employee.employee_id,
                Employee.employee_code,
                Employee.first_name,
                Employee.last_name,
                Employee.department_id,
                Department.department_name,
                Employee.designation_id,
                Designation.designation_name,
                LeaveTypeModel.leave_type_id,
                LeaveTypeModel.leave_type_name,
                LeaveRequestModel.start_date,
                LeaveRequestModel.end_date,
                LeaveRequestModel.requested_days,
                LeaveRequestModel.status,
                LeaveRequestDayModel.leave_date,
                LeaveRequestDayModel.day_fraction,
            )
            .select_from(LeaveRequestDayModel)
            .join(
                LeaveRequestModel,
                LeaveRequestModel.leave_request_id
                == LeaveRequestDayModel.leave_request_id,
            )
            .join(Employee, Employee.employee_id == LeaveRequestModel.employee_id)
            .join(
                LeaveTypeModel,
                LeaveTypeModel.leave_type_id == LeaveRequestModel.leave_type_id,
            )
            .join(Department, Department.department_id == Employee.department_id)
            .join(Designation, Designation.designation_id == Employee.designation_id)
        )
        if date_from is not None:
            statement = statement.where(LeaveRequestDayModel.leave_date >= date_from)
        if date_to is not None:
            statement = statement.where(LeaveRequestDayModel.leave_date <= date_to)
        if employee_id is not None:
            statement = statement.where(LeaveRequestModel.employee_id == employee_id)
        if department_id is not None:
            statement = statement.where(Employee.department_id == department_id)
        if leave_type_id is not None:
            statement = statement.where(LeaveRequestModel.leave_type_id == leave_type_id)
        if status is not None:
            statement = statement.where(LeaveRequestModel.status == status)
        if after_leave_date is not None and after_leave_request_day_id is not None:
            statement = statement.where(
                or_(
                    LeaveRequestDayModel.leave_date > after_leave_date,
                    and_(
                        LeaveRequestDayModel.leave_date == after_leave_date,
                        LeaveRequestDayModel.leave_request_day_id
                        > after_leave_request_day_id,
                    ),
                )
            )

        statement = statement.order_by(
            LeaveRequestDayModel.leave_date.asc(),
            LeaveRequestDayModel.leave_request_day_id.asc(),
        ).limit(limit)

        return [
            LeaveAllocationReportRecord(
                leave_request_id=row.leave_request_id,
                leave_request_day_id=row.leave_request_day_id,
                employee_id=row.employee_id,
                employee_code=row.employee_code,
                first_name=row.first_name,
                last_name=row.last_name,
                department_id=row.department_id,
                department_name=row.department_name,
                designation_id=row.designation_id,
                designation_name=row.designation_name,
                leave_type_id=row.leave_type_id,
                leave_type_name=row.leave_type_name,
                start_date=row.start_date,
                end_date=row.end_date,
                requested_days=row.requested_days,
                status=row.status,
                leave_date=row.leave_date,
                day_fraction=row.day_fraction,
            )
            for row in self.session.execute(statement)
        ]

    def list_balance_report_page(
        self,
        employee_id: int | None,
        department_id: int | None,
        leave_type_id: int | None,
        balance_year: int | None,
        after_employee_id: int | None,
        after_leave_type_id: int | None,
        after_balance_year: int | None,
        limit: int,
    ) -> list[LeaveBalanceReportRecord]:
        statement = (
            select(
                Employee.employee_id,
                Employee.employee_code,
                Employee.first_name,
                Employee.last_name,
                Employee.department_id,
                Department.department_name,
                Employee.designation_id,
                Designation.designation_name,
                LeaveTypeModel.leave_type_id,
                LeaveTypeModel.leave_type_name,
                LeaveBalanceModel.balance_year,
                LeaveBalanceModel.allocated_days,
                LeaveBalanceModel.used_days,
            )
            .select_from(LeaveBalanceModel)
            .join(Employee, Employee.employee_id == LeaveBalanceModel.employee_id)
            .join(
                LeaveTypeModel,
                LeaveTypeModel.leave_type_id == LeaveBalanceModel.leave_type_id,
            )
            .join(Department, Department.department_id == Employee.department_id)
            .join(Designation, Designation.designation_id == Employee.designation_id)
        )
        if employee_id is not None:
            statement = statement.where(LeaveBalanceModel.employee_id == employee_id)
        if department_id is not None:
            statement = statement.where(Employee.department_id == department_id)
        if leave_type_id is not None:
            statement = statement.where(LeaveBalanceModel.leave_type_id == leave_type_id)
        if balance_year is not None:
            statement = statement.where(LeaveBalanceModel.balance_year == balance_year)
        if (
            after_employee_id is not None
            and after_leave_type_id is not None
            and after_balance_year is not None
        ):
            statement = statement.where(
                or_(
                    LeaveBalanceModel.employee_id > after_employee_id,
                    and_(
                        LeaveBalanceModel.employee_id == after_employee_id,
                        LeaveBalanceModel.leave_type_id > after_leave_type_id,
                    ),
                    and_(
                        LeaveBalanceModel.employee_id == after_employee_id,
                        LeaveBalanceModel.leave_type_id == after_leave_type_id,
                        LeaveBalanceModel.balance_year > after_balance_year,
                    ),
                )
            )

        statement = statement.order_by(
            LeaveBalanceModel.employee_id.asc(),
            LeaveBalanceModel.leave_type_id.asc(),
            LeaveBalanceModel.balance_year.asc(),
        ).limit(limit)

        return [
            LeaveBalanceReportRecord(
                employee_id=row.employee_id,
                employee_code=row.employee_code,
                first_name=row.first_name,
                last_name=row.last_name,
                department_id=row.department_id,
                department_name=row.department_name,
                designation_id=row.designation_id,
                designation_name=row.designation_name,
                leave_type_id=row.leave_type_id,
                leave_type_name=row.leave_type_name,
                balance_year=row.balance_year,
                allocated_days=row.allocated_days,
                used_days=row.used_days,
            )
            for row in self.session.execute(statement)
        ]
