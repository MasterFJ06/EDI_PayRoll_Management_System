from types import TracebackType
from typing import Self

from sqlalchemy.orm import Session

from app.application.common.unit_of_work import UnitOfWork
from app.infrastructure.database.session import SessionLocal
from app.infrastructure.persistence.repositories.attendance_repository import (
    AttendanceRepository,
)
from app.infrastructure.persistence.repositories.audit_repository import (
    AuditRepository,
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
from app.infrastructure.persistence.repositories.leave_repository import (
    LeaveRepository,
)
from app.infrastructure.persistence.repositories.payroll_repository import (
    PayrollRepository,
)
from app.infrastructure.persistence.repositories.payslip_repository import (
    PayslipRepository,
)
from app.infrastructure.persistence.repositories.refresh_token_repository import (
    RefreshTokenRepository,
)
from app.infrastructure.persistence.repositories.role_repository import (
    RoleRepository,
)
from app.infrastructure.persistence.repositories.salary_repository import (
    SalaryRepository,
)
from app.infrastructure.persistence.repositories.user_repository import (
    UserRepository,
)


class SQLAlchemyUnitOfWork(UnitOfWork):
    """SQLAlchemy implementation of the Unit of Work pattern."""

    def __init__(self) -> None:
        self.session: Session | None = None
        self.users: UserRepository | None = None
        self.roles: RoleRepository | None = None
        self.refresh_tokens: RefreshTokenRepository | None = None
        self.departments: SQLAlchemyDepartmentRepository | None = None
        self.designations: SQLAlchemyDesignationRepository | None = None
        self.employees: EmployeeRepository | None = None
        self.attendance: AttendanceRepository | None = None
        self.leaves: LeaveRepository | None = None
        self.salaries: SalaryRepository | None = None
        self.payroll: PayrollRepository | None = None
        self.payslips: PayslipRepository | None = None
        self.audits: AuditRepository | None = None

    def __enter__(self) -> Self:
        self.session = SessionLocal()
        self.users = UserRepository(self.session)
        self.roles = RoleRepository(self.session)
        self.refresh_tokens = RefreshTokenRepository(self.session)
        self.departments = SQLAlchemyDepartmentRepository(self.session)
        self.designations = SQLAlchemyDesignationRepository(self.session)
        self.employees = EmployeeRepository(self.session)
        self.attendance = AttendanceRepository(self.session)
        self.leaves = LeaveRepository(self.session)
        self.salaries = SalaryRepository(self.session)
        self.payroll = PayrollRepository(self.session)
        self.payslips = PayslipRepository(self.session)
        self.audits = AuditRepository(self.session)
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
                self.roles = None
                self.refresh_tokens = None
                self.departments = None
                self.designations = None
                self.employees = None
                self.attendance = None
                self.leaves = None
                self.salaries = None
                self.payroll = None
                self.payslips = None
                self.audits = None

    def commit(self) -> None:
        if self.session is None:
            raise RuntimeError("Unit of Work has not been started.")

        self.session.commit()

    def rollback(self) -> None:
        if self.session is None:
            raise RuntimeError("Unit of Work has not been started.")

        self.session.rollback()