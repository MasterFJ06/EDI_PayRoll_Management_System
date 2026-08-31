from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from app.domain.shared.entity import Entity


TEntity = TypeVar("TEntity", bound=Entity)
TId = TypeVar("TId")


class Repository(ABC, Generic[TEntity, TId]):
    """Base abstraction for domain repositories."""

    @abstractmethod
    def get_by_id(self, entity_id: TId) -> TEntity | None:
        raise NotImplementedError

    @abstractmethod
    def add(self, entity: TEntity) -> None:
        raise NotImplementedError