from app.application.common.unit_of_work import UnitOfWork
from app.application.identity.schemas import (
    UserLoginRequest,
    UserRegistrationRequest,
    UserRegistrationResponse,
)
from app.domain.shared.exceptions import BusinessRuleViolation
from app.infrastructure.persistence.models.user import User
from app.infrastructure.security.password import (
    hash_password,
    verify_password,
)


class UserService:
    """Application service for user identity operations."""

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def register(
        self,
        request: UserRegistrationRequest,
    ) -> UserRegistrationResponse:
        """Register a new system user."""

        if self.uow.users is None:
            raise RuntimeError("Unit of Work has not been started.")

        existing_username = self.uow.users.get_by_username(
            request.username
        )

        if existing_username is not None:
            raise BusinessRuleViolation(
                "Username is already registered."
            )

        existing_email = self.uow.users.get_by_email(
            str(request.email)
        )

        if existing_email is not None:
            raise BusinessRuleViolation(
                "Email is already registered."
            )

        user = User(
            username=request.username,
            email=str(request.email),
            password_hash=hash_password(request.password),
            status="ACTIVE",
        )

        self.uow.users.add(user)
        self.uow.commit()

        return UserRegistrationResponse(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            status=user.status,
        )

    def authenticate(
        self,
        request: UserLoginRequest,
    ) -> User:
        """Authenticate a user using username and password."""

        if self.uow.users is None:
            raise RuntimeError("Unit of Work has not been started.")

        user = self.uow.users.get_by_username(
            request.username
        )

        if user is None:
            raise BusinessRuleViolation(
                "Invalid username or password."
            )

        if not verify_password(
            request.password,
            user.password_hash,
        ):
            raise BusinessRuleViolation(
                "Invalid username or password."
            )

        if user.status != "ACTIVE":
            raise BusinessRuleViolation(
                "User account is not active."
            )

        return user