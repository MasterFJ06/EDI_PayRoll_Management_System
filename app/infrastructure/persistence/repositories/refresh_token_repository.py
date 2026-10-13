from datetime import datetime

from sqlalchemy import select, text, update
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

    def get_by_token_hash_for_update(
        self,
        token_hash: str,
    ) -> RefreshToken | None:
        candidate = self.get_by_token_hash(token_hash)
        if candidate is None:
            return None

        # Lock every member of a family in a stable order. Rotation, replay
        # revocation, and logout therefore cannot deadlock by taking family
        # rows in different orders.
        statement = (
            select(RefreshToken)
            .where(RefreshToken.family_id == candidate.family_id)
            .order_by(RefreshToken.token_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        family = self.session.scalars(statement).all()
        return next((row for row in family if row.token_hash == token_hash), None)

    def get_database_time(self) -> datetime:
        value = self.session.execute(
            text("SELECT CURRENT_TIMESTAMP(6)")
        ).scalar_one()
        if not isinstance(value, datetime):
            raise RuntimeError("Database did not return the current timestamp.")
        return value

    def revoke_family(self, family_id: str, revoked_at: datetime) -> int:
        result = self.session.execute(
            update(RefreshToken)
            .where(
                RefreshToken.family_id == family_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=revoked_at)
        )
        return int(result.rowcount or 0)

    def revoke(
        self,
        refresh_token: RefreshToken,
        revoked_at: datetime,
    ) -> None:
        refresh_token.revoked_at = revoked_at
        self.session.flush()
