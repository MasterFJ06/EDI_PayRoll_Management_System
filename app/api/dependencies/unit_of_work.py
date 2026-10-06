from collections.abc import Generator

from app.application.common.unit_of_work import UnitOfWork
from app.infrastructure.database.unit_of_work import SQLAlchemyUnitOfWork


def get_unit_of_work() -> Generator[UnitOfWork, None, None]:
    with SQLAlchemyUnitOfWork() as uow:
        yield uow