from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.persistence.models.refresh_token import RefreshToken


class RefreshTokenRepository:
    """Repository for refresh-token persistence operations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, refresh_token: RefreshToken) -> RefreshToken:
        self.session.add(refresh_token)
        self.session.flush()
        return refresh_token

    def get_by_token_hash(
        self,
        token_hash: str,
    ) -> RefreshToken | None:
        statement = select(RefreshToken).where(
            RefreshToken.token_hash == token_hash
        )
        return self.session.scalar(statement)

    def revoke(
        self,
        refresh_token: RefreshToken,
        revoked_at: datetime,
    ) -> None:
        refresh_token.revoked_at = revoked_at
        self.session.flush()