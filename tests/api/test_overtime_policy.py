from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock

from fastapi.testclient import TestClient

from app.api.dependencies.current_user import get_current_user
from app.api.dependencies.unit_of_work import get_unit_of_work
from app.domain.workforce.overtime import OvertimePolicyVersion
from app.infrastructure.persistence.models.user import User
from app.main import app


class PolicyRepo:
    def __init__(self) -> None:
        self.rows = {}
        self.overlap = False

    def has_effective_date_overlap(self, *_args) -> bool:
        return self.overlap

    def add(self, policy):
        created = OvertimePolicyVersion(policy.version_number, policy.effective_from, policy.effective_to,
                                        policy.non_working_multiplier, policy.created_by_user_id, 15)
        self.rows[15] = created
        return created

    def get_by_id(self, policy_id):
        return self.rows.get(policy_id)


def client(permission: bool = True):
    actor = Mock(spec=User)
    actor.user_id = 7
    uow = Mock()
    uow.authorization.has_permission.return_value = permission
    uow.overtime_policies = PolicyRepo()
    app.dependency_overrides[get_current_user] = lambda: actor
    app.dependency_overrides[get_unit_of_work] = lambda: uow
    return TestClient(app), uow


def teardown_function() -> None:
    app.dependency_overrides.clear()


def test_policy_post_and_get_use_authenticated_creator() -> None:
    test_client, _ = client()
    with test_client:
        response = test_client.post("/api/v1/workforce/overtime-policy-versions", json={
            "version_number": 1, "effective_from": "2026-01-01", "effective_to": "2026-12-31",
            "non_working_multiplier": "1.5000",
        })
        fetched = test_client.get("/api/v1/workforce/overtime-policy-versions/15")
    assert response.status_code == 201
    assert response.json()["created_by_user_id"] == 7
    assert response.json()["non_working_multiplier"] == "1.5000"
    assert fetched.status_code == 200


def test_policy_get_not_found() -> None:
    test_client, _ = client()
    with test_client:
        response = test_client.get("/api/v1/workforce/overtime-policy-versions/999")
    assert response.status_code == 404


def test_policy_permissions_are_enforced() -> None:
    test_client, _ = client(permission=False)
    with test_client:
        get_response = test_client.get("/api/v1/workforce/overtime-policy-versions/15")
        post_response = test_client.post("/api/v1/workforce/overtime-policy-versions", json={
            "version_number": 1, "effective_from": "2026-01-01", "non_working_multiplier": "1.5"
        })
    assert get_response.status_code == 403
    assert post_response.status_code == 403


def test_policy_post_validates_extra_fields_and_period() -> None:
    test_client, _ = client()
    with test_client:
        response = test_client.post("/api/v1/workforce/overtime-policy-versions", json={
            "version_number": 1, "effective_from": "2026-12-31", "effective_to": "2026-01-01",
            "non_working_multiplier": "1.5", "created_by_user_id": 99,
        })
    assert response.status_code == 422


def test_policy_create_overlap_returns_conflict() -> None:
    test_client, uow = client()
    uow.overtime_policies.overlap = True
    with test_client:
        response = test_client.post("/api/v1/workforce/overtime-policy-versions", json={
            "version_number": 2, "effective_from": "2027-01-01", "non_working_multiplier": "1.5"
        })
    assert response.status_code == 409


def test_policy_api_requires_authentication() -> None:
    with TestClient(app) as test_client:
        response = test_client.get("/api/v1/workforce/overtime-policy-versions/15")
    assert response.status_code == 401
