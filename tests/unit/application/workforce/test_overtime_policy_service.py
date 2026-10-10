from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.application.workforce.overtime_policy_service import OvertimePolicyService
from app.application.workforce.overtime_schemas import OvertimePolicyCreateRequest
from app.domain.shared.exceptions import BusinessRuleViolation


def make_uow(overlap: bool = False):
    uow = Mock()
    uow.overtime_policies.has_effective_date_overlap.return_value = overlap
    uow.overtime_policies.add.side_effect = lambda policy: SimpleNamespace(
        policy_id=12, version_number=policy.version_number, effective_from=policy.effective_from,
        effective_to=policy.effective_to, non_working_multiplier=policy.non_working_multiplier,
        created_by_user_id=policy.created_by_user_id,
    )
    uow.overtime_policies.get_by_id.return_value = None
    return uow


def request() -> OvertimePolicyCreateRequest:
    return OvertimePolicyCreateRequest(version_number=1, effective_from=date(2026, 1, 1),
                                       effective_to=None, non_working_multiplier=Decimal("1.5"))


def test_create_commits_policy_and_audit_with_authenticated_actor() -> None:
    uow = make_uow()
    result = OvertimePolicyService(uow).create(request(), 7, "request-id")
    assert result.workforce_overtime_policy_version_id == 12
    event, changes = uow.audit_events.add.call_args.args
    assert event.actor_user_id == 7
    assert event.action_type == "OVERTIME_POLICY_CREATED"
    assert event.correlation_id == "request-id"
    assert {change.field_name for change in changes} == {
        "version_number", "effective_period", "non_working_multiplier"
    }
    uow.commit.assert_called_once()


def test_overlapping_policy_create_is_rejected_before_commit() -> None:
    uow = make_uow(overlap=True)
    with pytest.raises(BusinessRuleViolation, match="overlap"):
        OvertimePolicyService(uow).create(request(), 7, None)
    uow.overtime_policies.add.assert_not_called()
    uow.commit.assert_not_called()


def test_get_returns_none_for_missing_policy() -> None:
    assert OvertimePolicyService(make_uow()).get(404) is None
