from datetime import datetime
from types import TracebackType
from typing import Self

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.application.common.unit_of_work import UnitOfWork
from app.infrastructure.database.session import SessionLocal
from app.infrastructure.persistence.repositories.refresh_token_repository import (
    RefreshTokenRepository,
)
from app.infrastructure.persistence.repositories.user_repository import (
    UserRepository,
)
from app.infrastructure.persistence.repositories.authorization_repository import (
    AuthorizationRepository,
)
from app.infrastructure.persistence.repositories.audit_event_repository import (
    AuditEventRepository,
)
from app.infrastructure.persistence.repositories.department_repository import (
    SQLAlchemyDepartmentRepository,
)
from app.infrastructure.persistence.repositories.designation_repository import (
    SQLAlchemyDesignationRepository,
)
from app.infrastructure.persistence.repositories.employee_repository import (
    EmployeeRepository,
)
from app.infrastructure.persistence.repositories.attendance_repository import (
    AttendanceRepository,
)
from app.infrastructure.persistence.repositories.leave_type_repository import (
    LeaveTypeRepository,
)
from app.infrastructure.persistence.repositories.leave_balance_repository import (
    LeaveBalanceRepository,
)
from app.infrastructure.persistence.repositories.leave_request_repository import (
    LeaveRequestRepository,
)
from app.infrastructure.persistence.repositories.leave_report_repository import (
    LeaveReportRepository,
)
from app.infrastructure.persistence.repositories.salary_structure_repository import (
    SalaryStructureRepository,
)
from app.infrastructure.persistence.repositories.salary_component_repository import (
    SalaryComponentRepository,
)
from app.infrastructure.persistence.repositories.salary_revision_repository import (
    SalaryRevisionRepository,
)
from app.infrastructure.persistence.repositories.salary_revision_component_repository import (
    SalaryRevisionComponentRepository,
)
from app.infrastructure.persistence.repositories.employee_salary_assignment_repository import (
    EmployeeSalaryAssignmentRepository,
)
from app.infrastructure.persistence.repositories.payroll_run_repository import (
    PayrollRunRepository,
)
from app.infrastructure.persistence.repositories.payroll_run_workforce_snapshot_repository import (
    PayrollRunWorkforceSnapshotRepository,
)
from app.infrastructure.persistence.repositories.payroll_result_repository import (
    PayrollResultRepository,
)
from app.infrastructure.persistence.repositories.payroll_result_component_repository import (
    PayrollResultComponentRepository,
)
from app.infrastructure.persistence.repositories.payroll_processing_issue_repository import (
    PayrollProcessingIssueRepository,
)
from app.infrastructure.persistence.repositories.payslip_repository import PayslipRepository
from app.infrastructure.persistence.repositories.work_calendar_repository import (
    SQLAlchemyWorkCalendarRepository,
)
from app.infrastructure.persistence.repositories.overtime_policy_repository import (
    OvertimePolicyRepository,
)


class SQLAlchemyUnitOfWork(UnitOfWork):
    """SQLAlchemy implementation of the Unit of Work pattern."""

    def __init__(self) -> None:
        self.session: Session | None = None
        self.users: UserRepository | None = None
        self.authorization: AuthorizationRepository | None = None
        self.audit_events: AuditEventRepository | None = None
        self.refresh_tokens: RefreshTokenRepository | None = None
        self.departments: SQLAlchemyDepartmentRepository | None = None
        self.designations: SQLAlchemyDesignationRepository | None = None
        self.employees: EmployeeRepository | None = None
        self.leave_types: LeaveTypeRepository | None = None
        self.leave_balances: LeaveBalanceRepository | None = None
        self.leave_requests: LeaveRequestRepository | None = None
        self.leave_reports: LeaveReportRepository | None = None
        self.salary_structures: SalaryStructureRepository | None = None
        self.salary_components: SalaryComponentRepository | None = None
        self.salary_revisions: SalaryRevisionRepository | None = None
        self.salary_revision_components: SalaryRevisionComponentRepository | None = None
        self.employee_salary_assignments: EmployeeSalaryAssignmentRepository | None = None
        self.payroll_runs: PayrollRunRepository | None = None
        self.payroll_run_workforce_snapshots: (
            PayrollRunWorkforceSnapshotRepository | None
        ) = None
        self.payroll_results: PayrollResultRepository | None = None
        self.payroll_result_components: PayrollResultComponentRepository | None = None
        self.payroll_processing_issues: PayrollProcessingIssueRepository | None = None
        self.payslips: PayslipRepository | None = None
        self.work_calendars: SQLAlchemyWorkCalendarRepository | None = None
        self.overtime_policies: OvertimePolicyRepository | None = None

    def __enter__(self) -> Self:
        self.session = SessionLocal()
        self.users = UserRepository(self.session)
        self.authorization = AuthorizationRepository(self.session)
        self.audit_events = AuditEventRepository(self.session)
        self.refresh_tokens = RefreshTokenRepository(self.session)
        self.departments = SQLAlchemyDepartmentRepository(self.session)
        self.designations = SQLAlchemyDesignationRepository(self.session)
        self.employees = EmployeeRepository(self.session)
        self.attendance = AttendanceRepository(self.session)
        self.leave_types = LeaveTypeRepository(self.session)
        self.leave_balances = LeaveBalanceRepository(self.session)
        self.leave_requests = LeaveRequestRepository(self.session)
        self.leave_reports = LeaveReportRepository(self.session)
        self.salary_structures = SalaryStructureRepository(self.session)
        self.salary_components = SalaryComponentRepository(self.session)
        self.salary_revisions = SalaryRevisionRepository(self.session)
        self.salary_revision_components = SalaryRevisionComponentRepository(self.session)
        self.employee_salary_assignments = EmployeeSalaryAssignmentRepository(self.session)
        self.payroll_runs = PayrollRunRepository(self.session)
        self.payroll_run_workforce_snapshots = PayrollRunWorkforceSnapshotRepository(
            self.session, self.payroll_runs
        )
        self.payroll_results = PayrollResultRepository(self.session)
        self.payroll_result_components = PayrollResultComponentRepository(self.session)
        self.payroll_processing_issues = PayrollProcessingIssueRepository(self.session)
        self.payslips = PayslipRepository(self.session)
        self.work_calendars = SQLAlchemyWorkCalendarRepository(self.session)
        self.overtime_policies = OvertimePolicyRepository(self.session)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        try:
            if exc_type is not None:
                self.rollback()
        finally:
            if self.session is not None:
                self.session.close()
                self.session = None
                self.users = None
                self.authorization = None
                self.audit_events = None
                self.refresh_tokens = None
                self.departments = None
                self.designations = None
                self.employees = None
                self.attendance = None
                self.leave_types = None
                self.leave_balances = None
                self.leave_requests = None
                self.leave_reports = None
                self.salary_structures = None
                self.salary_components = None
                self.salary_revisions = None
                self.salary_revision_components = None
                self.employee_salary_assignments = None
                self.payroll_runs = None
                self.payroll_run_workforce_snapshots = None
                self.payroll_results = None
                self.payroll_result_components = None
                self.payroll_processing_issues = None
                self.payslips = None
                self.work_calendars = None
                self.overtime_policies = None

    def commit(self) -> None:
        if self.session is None:
            raise RuntimeError("Unit of Work has not been started.")

        self.session.commit()

    def rollback(self) -> None:
        if self.session is None:
            raise RuntimeError("Unit of Work has not been started.")

        self.session.rollback()

    def begin_workforce_consistent_read(self) -> datetime:
        if self.session is None:
            raise RuntimeError("Unit of Work has not been started.")
        if self.session.in_transaction():
            raise RuntimeError(
                "Workforce consistent read must start after the prior transaction ends."
            )

        # Expire objects loaded during the claim so ORM identity-map values cannot
        # bypass the new InnoDB read view.
        self.session.expire_all()
        connection = self.session.connection(
            execution_options={"isolation_level": "REPEATABLE READ"}
        )
        if connection.dialect.name != "mysql":
            raise RuntimeError(
                "Workforce consistent snapshots require MySQL/InnoDB."
            )
        connection.exec_driver_sql("START TRANSACTION WITH CONSISTENT SNAPSHOT")
        timestamp = connection.scalar(text("SELECT CURRENT_TIMESTAMP(6)"))
        if not isinstance(timestamp, datetime):
            raise RuntimeError("Database did not return the Workforce snapshot timestamp.")
        return timestamp
