from unittest.mock import Mock

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies.authorization import require_permission
from app.api.dependencies.unit_of_work import get_unit_of_work
from app.infrastructure.security.jwt import create_access_token


def _client_for_permission(
    has_permission: bool, permission_code: str = "payroll.run.create"
) -> tuple[TestClient, Mock]:
    user = Mock(user_id=41, username="rbac-user", status="ACTIVE")
    uow = Mock()
    uow.users.get_by_id.return_value = user
    uow.authorization.has_permission.return_value = has_permission

    app = FastAPI()

    def override_uow():
        yield uow

    app.dependency_overrides[get_unit_of_work] = override_uow

    @app.get("/protected")
    def protected(
        actor_id: int | None = None,
        current_user=Depends(require_permission(permission_code)),
    ):
        return {"authenticated_user_id": current_user.user_id, "actor_id": actor_id}

    token = create_access_token(user_id=41, username="rbac-user")
    client = TestClient(app)
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client, uow


def test_permission_dependency_allows_authenticated_user_with_permission() -> None:
    client, uow = _client_for_permission(True)

    response = client.get("/protected")

    assert response.status_code == 200
    assert response.json() == {"authenticated_user_id": 41, "actor_id": None}
    uow.authorization.has_permission.assert_called_once_with(41, "payroll.run.create")


def test_permission_dependency_allows_payroll_run_read() -> None:
    client, uow = _client_for_permission(True, "payroll.run.read")

    response = client.get("/protected")

    assert response.status_code == 200
    uow.authorization.has_permission.assert_called_once_with(41, "payroll.run.read")


def test_permission_dependency_returns_403_without_permission() -> None:
    client, uow = _client_for_permission(False)

    response = client.get("/protected")

    assert response.status_code == 403
    assert response.json()["detail"] == "You do not have permission to access this resource."
    uow.authorization.has_permission.assert_called_once_with(41, "payroll.run.create")


def test_permission_dependency_requires_authentication() -> None:
    client, _ = _client_for_permission(True)
    client.headers.clear()

    response = client.get("/protected")

    assert response.status_code == 401


def test_permission_dependency_ignores_client_supplied_actor_id() -> None:
    client, uow = _client_for_permission(True)

    response = client.get("/protected?actor_id=999")

    assert response.status_code == 200
    assert response.json() == {"authenticated_user_id": 41, "actor_id": 999}
    uow.authorization.has_permission.assert_called_once_with(41, "payroll.run.create")
