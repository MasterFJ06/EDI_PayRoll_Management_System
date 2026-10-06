from unittest.mock import Mock

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies.current_user import get_current_user
from app.api.dependencies.unit_of_work import get_unit_of_work
from app.infrastructure.security.jwt import create_access_token


def create_test_app(user: Mock | None) -> FastAPI:
    app = FastAPI()

    async def override_unit_of_work():
        uow = Mock()
        uow.users.get_by_id.return_value = user
        yield uow

    app.dependency_overrides[get_unit_of_work] = override_unit_of_work

    @app.get("/protected")
    def protected_endpoint(
        current_user=Depends(get_current_user),
    ):
        return {
            "user_id": current_user.user_id,
            "username": current_user.username,
        }

    return app


def test_current_user_returns_authenticated_user() -> None:
    user = Mock()
    user.user_id = 1
    user.username = "john"
    user.status = "ACTIVE"

    app = create_test_app(user)
    client = TestClient(app)

    token = create_access_token(
        user_id=1,
        username="john",
    )

    response = client.get(
        "/protected",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "user_id": 1,
        "username": "john",
    }


def test_current_user_rejects_invalid_token() -> None:
    user = Mock()
    user.user_id = 1
    user.username = "john"
    user.status = "ACTIVE"

    app = create_test_app(user)
    client = TestClient(app)

    response = client.get(
        "/protected",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired access token."


def test_current_user_rejects_unknown_user() -> None:
    app = create_test_app(None)
    client = TestClient(app)

    token = create_access_token(
        user_id=999,
        username="unknown",
    )

    response = client.get(
        "/protected",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "User not found."


def test_current_user_rejects_inactive_user() -> None:
    user = Mock()
    user.user_id = 1
    user.username = "john"
    user.status = "INACTIVE"

    app = create_test_app(user)
    client = TestClient(app)

    token = create_access_token(
        user_id=1,
        username="john",
    )

    response = client.get(
        "/protected",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "User account is inactive."