from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.domain.shared.exceptions import BusinessRuleViolation


@dataclass(frozen=True)
class LeaveRequestDay:
    leave_date: date
    day_fraction: Decimal

    def __post_init__(self) -> None:
        fraction = self.day_fraction
        if not isinstance(fraction, Decimal) or not fraction.is_finite():
            raise BusinessRuleViolation("Leave allocation must be a finite Decimal.")
        if fraction < Decimal("0.01") or fraction > Decimal("1.00"):
            raise BusinessRuleViolation("Leave allocation must be between 0.01 and 1.00.")
        if fraction.as_tuple().exponent < -2:
            raise BusinessRuleViolation("Leave allocation must use increments of 0.01.")
