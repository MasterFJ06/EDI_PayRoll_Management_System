from app.infrastructure.security.password import (
    hash_password,
    verify_password,
)


def test_password_is_hashed() -> None:
    password = "SecurePassword123!"

    hashed_password = hash_password(password)

    assert hashed_password != password


def test_correct_password_is_verified() -> None:
    password = "SecurePassword123!"

    hashed_password = hash_password(password)

    assert verify_password(password, hashed_password) is True


def test_incorrect_password_is_rejected() -> None:
    password = "SecurePassword123!"

    hashed_password = hash_password(password)

    assert verify_password("WrongPassword123!", hashed_password) is False