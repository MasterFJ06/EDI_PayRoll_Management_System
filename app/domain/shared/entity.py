from abc import ABC
from typing import Generic, TypeVar


EntityId = TypeVar("EntityId")


class Entity(ABC, Generic[EntityId]):
    """Base class for domain entities with identity."""

    def __init__(self, entity_id: EntityId) -> None:
        self._id = entity_id

    @property
    def id(self) -> EntityId:
        return self._id

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Entity):
            return NotImplemented

        return type(self) is type(other) and self.id == other.id

    def __hash__(self) -> int:
        return hash((type(self), self.id))