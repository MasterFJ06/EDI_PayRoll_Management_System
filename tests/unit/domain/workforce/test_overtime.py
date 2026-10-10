from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.domain.shared.exceptions import BusinessRuleViolation
from app.domain.workforce.overtime import OvertimePolicyVersion, overtime_base_component


def test_overtime_policy_accepts_adjacent_range_and_decimal_multiplier() -> None:
    policy = OvertimePolicyVersion(2, date(2026, 7, 1), date(2026, 12, 31), Decimal("1.2500"), 7, 12)
    assert policy.applies_on(date(2026, 12, 31))
    assert not policy.applies_on(date(2027, 1, 1))


@pytest.mark.parametrize("multiplier", [Decimal("-0.1"), Decimal("1.00001"), Decimal("NaN"), Decimal("10000")])
def test_overtime_policy_rejects_invalid_multiplier(multiplier: Decimal) -> None:
    with pytest.raises(BusinessRuleViolation):
        OvertimePolicyVersion(1, date(2026, 1, 1), None, multiplier, 7)


def test_ot_base_requires_exactly_one_fixed_earning() -> None:
    base = SimpleNamespace(is_overtime_base=True, component_type="EARNING", calculation_type="FIXED", fixed_amount=Decimal("1000"))
    assert overtime_base_component([base]) is base


@pytest.mark.parametrize("components", [[], [
    SimpleNamespace(is_overtime_base=True, component_type="EARNING", calculation_type="FIXED", fixed_amount=Decimal("1")),
    SimpleNamespace(is_overtime_base=True, component_type="EARNING", calculation_type="FIXED", fixed_amount=Decimal("2")),
]])
def test_ot_base_rejects_zero_or_multiple_designations(components: list[object]) -> None:
    with pytest.raises(BusinessRuleViolation, match="exactly one"):
        overtime_base_component(components)


@pytest.mark.parametrize("candidate", [
    SimpleNamespace(is_overtime_base=True, component_type="DEDUCTION", calculation_type="FIXED", fixed_amount=Decimal("1")),
    SimpleNamespace(is_overtime_base=True, component_type="EARNING", calculation_type="PERCENTAGE", fixed_amount=None),
])
def test_ot_base_rejects_deduction_or_percentage(candidate: object) -> None:
    with pytest.raises(BusinessRuleViolation):
        overtime_base_component([candidate])
