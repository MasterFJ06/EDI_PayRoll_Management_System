"""Allow record-only payslips before document generation exists."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20261010_01"
down_revision = "20261007_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "payslips",
        "document_path",
        existing_type=sa.String(length=500),
        existing_nullable=False,
        nullable=True,
    )


def downgrade() -> None:
    connection = op.get_bind()
    null_count = connection.scalar(
        sa.text("SELECT COUNT(*) FROM payslips WHERE document_path IS NULL")
    )
    if null_count:
        raise RuntimeError(
            "Cannot restore payslips.document_path NOT NULL while record-only "
            "payslips have no document path."
        )
    op.alter_column(
        "payslips",
        "document_path",
        existing_type=sa.String(length=500),
        existing_nullable=True,
        nullable=False,
    )
