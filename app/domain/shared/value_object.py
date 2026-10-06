from dataclasses import dataclass


@dataclass(frozen=True)
class ValueObject:
    """Base class for immutable domain value objects."""

    pass