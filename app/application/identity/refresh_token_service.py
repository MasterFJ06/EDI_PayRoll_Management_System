"""Application use cases for issuing, rotating, and revoking refresh tokens."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import uuid4

from app.application.common.unit_of_work import UnitOfWork
from app.core.config import get_settings
from app.domain.shared.exceptions import BusinessRuleViolation
from app.infrastructure.persistence.models.refresh_token import RefreshToken
from app.infrastructure.persistence.models.user import User
from app.infrastructure.security.refresh_token import (
    generate_refresh_token,
    hash_refresh_token,
)


@dataclass(frozen=True)
class TokenPair:
    user: User
    refresh_token: str


class RefreshTokenService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def issue(self, user: User) -> str:
        repository = self._repository()
        current_user = self.uow.users.get_by_id_for_update(user.user_id)
        if current_user is None or current_user.status != "ACTIVE":
            self.uow.rollback()
            raise BusinessRuleViolation("User account is not active.")
        now = repository.get_database_time()
        plaintext = generate_refresh_token()
        repository.add(
            RefreshToken(
                user_id=user.user_id,
                family_id=str(uuid4()),
                token_hash=hash_refresh_token(plaintext),
                expires_at=self._expiry(now),
            )
        )
        self.uow.commit()
        return plaintext

    def rotate(self, plaintext: str) -> TokenPair | None:
        repository = self._repository()
        token = repository.get_by_token_hash_for_update(
            hash_refresh_token(plaintext)
        )
        if token is None:
            self.uow.rollback()
            return None

        now = repository.get_database_time()
        if token.revoked_at is not None:
            # Commit family revocation before the endpoint emits its generic 401.
            repository.revoke_family(token.family_id, now)
            self.uow.commit()
            return None
        if token.expires_at <= now:
            self.uow.rollback()
            return None

        user = self.uow.users.get_by_id_for_update(token.user_id)
        if user is None or user.status != "ACTIVE":
            repository.revoke_family(token.family_id, now)
            self.uow.commit()
            return None

        repository.revoke(token, now)
        replacement = generate_refresh_token()
        repository.add(
            RefreshToken(
                user_id=user.user_id,
                family_id=token.family_id,
                token_hash=hash_refresh_token(replacement),
                expires_at=self._expiry(now),
            )
        )
        self.uow.commit()
        return TokenPair(user=user, refresh_token=replacement)

    def logout(self, plaintext: str) -> bool:
        repository = self._repository()
        token = repository.get_by_token_hash_for_update(
            hash_refresh_token(plaintext)
        )
        if token is None:
            self.uow.rollback()
            return False

        now = repository.get_database_time()
        repository.revoke_family(token.family_id, now)
        self.uow.commit()
        return True

    @staticmethod
    def _expiry(now: datetime) -> datetime:
        return now + timedelta(days=get_settings().refresh_token_expire_days)

    def _repository(self):
        if self.uow.refresh_tokens is None or self.uow.users is None:
            raise RuntimeError("Unit of Work has not been started.")
        return self.uow.refresh_tokens
