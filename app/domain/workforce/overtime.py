from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from app.domain.shared.exceptions import BusinessRuleViolation


@dataclass(frozen=True)
class OvertimePolicyVersion:
    version_number: int
    effective_from: date
    effective_to: date | None
    non_working_multiplier: Decimal
    created_by_user_id: int
    policy_id: int | None = None

    def __post_init__(self) -> None:
        if self.version_number <= 0 or self.created_by_user_id <= 0:
            raise BusinessRuleViolation("Policy version and creator IDs must be positive.")
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise BusinessRuleViolation("Policy effective_to cannot precede effective_from.")
        multiplier = Decimal(self.non_working_multiplier)
        if (not multiplier.is_finite() or multiplier < 0 or multiplier >= Decimal("10000")
                or multiplier.as_tuple().exponent < -4):
            raise BusinessRuleViolation("Multiplier must be a finite nonnegative Decimal with at most four places.")
        if len(multiplier.as_tuple().digits) > 8:
            raise BusinessRuleViolation("Multiplier exceeds DECIMAL(8,4).")
        object.__setattr__(self, "non_working_multiplier", multiplier)

    def applies_on(self, day: date) -> bool:
        return self.effective_from <= day and (self.effective_to is None or day <= self.effective_to)


@dataclass(frozen=True)
class OvertimeAnomaly:
    code: str
    message: str
    attendance_id: int | None = None
    affected_date: date | None = None


@dataclass(frozen=True)
class OvertimeCalculation:
    employee_id: int
    attendance_id: int
    attendance_date: date
    time_zone: str
    interval_start: datetime
    interval_end: datetime
    calendar_version_id: int
    classification: str
    scheduled_minutes: int
    actual_worked_minutes: Decimal
    overtime_minutes: Decimal
    overtime_hours: Decimal
    policy_version_id: int
    policy_version_number: int
    multiplier: Decimal
    compensation_segment_start: date
    compensation_segment_end: date | None
    salary_revision_id: int
    overtime_base_component_id: int
    overtime_base_amount: Decimal
    working_day_denominator: int
    hourly_rate: Decimal
    amount: Decimal


def overtime_base_component(components: list[object]) -> object:
    selected = [component for component in components if component.is_overtime_base]
    if len(selected) != 1:
        raise BusinessRuleViolation("A salary revision must have exactly one designated overtime base.")
    component = selected[0]
    if component.component_type != "EARNING":
        raise BusinessRuleViolation("The overtime base component must be an EARNING.")
    if component.calculation_type != "FIXED" or component.fixed_amount is None:
        raise BusinessRuleViolation("The overtime base component must use FIXED calculation.")
    return component
