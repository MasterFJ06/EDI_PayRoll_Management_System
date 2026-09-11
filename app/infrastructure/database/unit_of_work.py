from types import TracebackType
from typing import Self

from sqlalchemy.orm import Session

from app.application.common.unit_of_work import UnitOfWork
from app.infrastructure.database.session import SessionLocal
from app.infrastructure.persistence.repositories.refresh_token_repository import (
    RefreshTokenRepository,
)
from app.infrastructure.persistence.repositories.user_repository import (
    UserRepository,
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

class SQLAlchemyUnitOfWork(UnitOfWork):
    """SQLAlchemy implementation of the Unit of Work pattern."""

    def __init__(self) -> None:
        self.session: Session | None = None
        self.users: UserRepository | None = None
        self.refresh_tokens: RefreshTokenRepository | None = None
        self.departments: SQLAlchemyDepartmentRepository | None = None
        self.designations: SQLAlchemyDesignationRepository | None = None
        self.employees: EmployeeRepository | None = None

    def __enter__(self) -> Self:
        self.session = SessionLocal()
        self.users = UserRepository(self.session)
        self.refresh_tokens = RefreshTokenRepository(self.session)
        self.departments = SQLAlchemyDepartmentRepository(self.session)
        self.designations = SQLAlchemyDesignationRepository(self.session)
        self.employees = EmployeeRepository(self.session)
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
                self.refresh_tokens = None
                self.departments = None
                self.designations = None
                self.employees = None

    def commit(self) -> None:
        if self.session is None:
            raise RuntimeError("Unit of Work has not been started.")

        self.session.commit()

    def rollback(self) -> None:
        if self.session is None:
            raise RuntimeError("Unit of Work has not been started.")

        self.session.rollback()