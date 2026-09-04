from unittest.mock import Mock

import pytest

from app.application.identity.schemas import UserRegistrationRequest
from app.application.identity.user_service import UserService
from app.domain.shared.exceptions import BusinessRuleViolation
from app.application.identity.schemas import (
    UserLoginRequest,
    UserRegistrationRequest,
)
from app.infrastructure.security.password import hash_password

def create_request() -> UserRegistrationRequest:
    return UserRegistrationRequest(
        username="john",
        email="john@example.com",
        password="SecurePassword123!",
    )


def test_register_creates_user() -> None:
    uow = Mock()
    uow.users.get_by_username.return_value = None
    uow.users.get_by_email.return_value = None

    def add_user(user):
        user.user_id = 1
        return user

    uow.users.add.side_effect = add_user

    service = UserService(uow)

    result = service.register(create_request())

    added_user = uow.users.add.call_args[0][0]

    assert added_user.user_id == 1
    assert added_user.username == "john"
    assert added_user.email == "john@example.com"
    assert added_user.password_hash != "SecurePassword123!"
    assert added_user.status == "ACTIVE"

    uow.commit.assert_called_once()

    assert result.user_id == 1
    assert result.username == "john"
    assert result.email == "john@example.com"
    assert result.status == "ACTIVE"


def test_register_rejects_duplicate_username() -> None:
    uow = Mock()
    uow.users.get_by_username.return_value = Mock()

    service = UserService(uow)

    with pytest.raises(BusinessRuleViolation):
        service.register(create_request())

    uow.users.add.assert_not_called()
    uow.commit.assert_not_called()


def test_register_rejects_duplicate_email() -> None:
    uow = Mock()
    uow.users.get_by_username.return_value = None
    uow.users.get_by_email.return_value = Mock()

    service = UserService(uow)

    with pytest.raises(BusinessRuleViolation):
        service.register(create_request())

    uow.users.add.assert_not_called()
    uow.commit.assert_not_called()

def test_authenticate_valid_credentials() -> None:
    uow = Mock()

    user = Mock()
    user.username = "john"
    user.password_hash = hash_password("SecurePassword123!")
    user.status = "ACTIVE"

    uow.users.get_by_username.return_value = user

    service = UserService(uow)

    request = UserLoginRequest(
        username="john",
        password="SecurePassword123!",
    )

    result = service.authenticate(request)

    assert result is user
    uow.users.get_by_username.assert_called_once_with("john")


def test_authenticate_rejects_wrong_password() -> None:
    uow = Mock()

    user = Mock()
    user.username = "john"
    user.password_hash = hash_password("SecurePassword123!")
    user.status = "ACTIVE"

    uow.users.get_by_username.return_value = user

    service = UserService(uow)

    request = UserLoginRequest(
        username="john",
        password="WrongPassword123!",
    )

    with pytest.raises(BusinessRuleViolation, match="Invalid username or password."):
        service.authenticate(request)


def test_authenticate_rejects_unknown_username() -> None:
    uow = Mock()
    uow.users.get_by_username.return_value = None

    service = UserService(uow)

    request = UserLoginRequest(
        username="unknown",
        password="SecurePassword123!",
    )

    with pytest.raises(BusinessRuleViolation, match="Invalid username or password."):
        service.authenticate(request)