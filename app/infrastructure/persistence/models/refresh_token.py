from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.models.base import Base


_UNSIGNED_BIGINT = Integer().with_variant(mysql.BIGINT(unsigned=True), "mysql")
_DATETIME_6 = DateTime().with_variant(mysql.DATETIME(fsp=6), "mysql")
_SHA256_HEX = String(64).with_variant(mysql.CHAR(64), "mysql")


class RefreshToken(Base):
    """SQLAlchemy model for refresh-token persistence."""

    __tablename__ = "refresh_tokens"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_refresh_tokens_hash"),
        Index("idx_refresh_tokens_family", "family_id", "token_id"),
        Index("idx_refresh_tokens_user", "user_id"),
    )

    token_id: Mapped[int] = mapped_column(
        _UNSIGNED_BIGINT,
        primary_key=True,
        autoincrement=True,
    )

    user_id: Mapped[int] = mapped_column(
        _UNSIGNED_BIGINT,
        ForeignKey(
            "users.user_id",
            name="fk_refresh_tokens_user",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        nullable=False,
    )

    family_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
    )

    token_hash: Mapped[str] = mapped_column(
        _SHA256_HEX,
        nullable=False,
    )

    expires_at: Mapped[datetime] = mapped_column(
        _DATETIME_6,
        nullable=False,
    )

    revoked_at: Mapped[datetime | None] = mapped_column(
        _DATETIME_6,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        _DATETIME_6,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP(6)"),
    )
