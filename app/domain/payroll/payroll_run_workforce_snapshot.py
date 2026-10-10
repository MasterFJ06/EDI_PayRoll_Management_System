from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Mapping


def _freeze_json(value: object) -> object:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze_json(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(item) for item in value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError("Snapshot values must be JSON-compatible.")


@dataclass(frozen=True)
class PayrollRunWorkforceSnapshot:
    payroll_run_id: int
    employee_id: int
    attempt_number: int
    snapshot_at: datetime
    snapshot: Mapping[str, object]

    def __post_init__(self) -> None:
        frozen = _freeze_json(self.snapshot)
        if not isinstance(frozen, Mapping):
            raise TypeError("Snapshot root must be a JSON object.")
        object.__setattr__(self, "snapshot", frozen)
