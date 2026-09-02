from types import TracebackType
from typing import Self

from sqlalchemy.orm import Session

from app.application.common.unit_of_work import UnitOfWork
from app.infrastructure.database.session import SessionLocal
from app.infrastructure.persistence.repositories.user_repository import (
    UserRepository,
)


class SQLAlchemyUnitOfWork(UnitOfWork):
    """SQLAlchemy implementation of the Unit of Work pattern."""

    def __init__(self) -> None:
        self.session: Session | None = None
        self.users: UserRepository | None = None

    def __enter__(self) -> Self:
        self.session = SessionLocal()

        self.users = UserRepository(self.session)

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

    def commit(self) -> None:
        if self.session is None:
            raise RuntimeError("Unit of Work has not been started.")

        self.session.commit()

    def rollback(self) -> None:
        if self.session is None:
            raise RuntimeError("Unit of Work has not been started.")

        self.session.rollback()