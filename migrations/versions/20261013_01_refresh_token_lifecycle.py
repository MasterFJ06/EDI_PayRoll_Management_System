"""Add persisted opaque refresh-token sessions and family rotation support.

Downgrade drops refresh_tokens and therefore invalidates all refresh sessions.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql


revision = "20261013_01"
down_revision = "20261010_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "refresh_tokens",
        sa.Column(
            "token_id", mysql.BIGINT(unsigned=True), autoincrement=True, nullable=False
        ),
        sa.Column("user_id", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("family_id", sa.String(length=36), nullable=False),
        sa.Column("token_hash", sa.CHAR(length=64), nullable=False),
        sa.Column("expires_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("revoked_at", mysql.DATETIME(fsp=6), nullable=True),
        sa.Column(
            "created_at",
            mysql.DATETIME(fsp=6),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP(6)"),
        ),
        sa.PrimaryKeyConstraint("token_id", name="pk_refresh_tokens"),
        sa.UniqueConstraint("token_hash", name="uq_refresh_tokens_hash"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.user_id"],
            name="fk_refresh_tokens_user",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        mysql_engine="InnoDB",
    )
    op.create_index(
        "idx_refresh_tokens_family", "refresh_tokens", ["family_id", "token_id"]
    )
    op.create_index("idx_refresh_tokens_user", "refresh_tokens", ["user_id"])


def downgrade() -> None:
    op.drop_index("idx_refresh_tokens_user", table_name="refresh_tokens")
    op.drop_index("idx_refresh_tokens_family", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
