"""Add Payroll attempt and Workforce snapshot persistence foundation."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql


revision = "20261007_02"
down_revision = "20261007_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "payroll_runs",
        sa.Column(
            "attempt_number",
            mysql.BIGINT(unsigned=True),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "payroll_runs",
        sa.Column("attempt_lease_expires_at", mysql.DATETIME(fsp=6), nullable=True),
    )
    op.create_table(
        "payroll_run_workforce_snapshots",
        sa.Column("payroll_run_id", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("employee_id", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("attempt_number", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("snapshot_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("snapshot", mysql.JSON(), nullable=False),
        sa.PrimaryKeyConstraint(
            "payroll_run_id",
            "employee_id",
            name="pk_payroll_run_workforce_snapshots",
        ),
        sa.ForeignKeyConstraint(
            ["payroll_run_id"],
            ["payroll_runs.payroll_run_id"],
            name="fk_payroll_workforce_snapshot_run",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["employee_id"],
            ["employees.employee_id"],
            name="fk_payroll_workforce_snapshot_employee",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        mysql_engine="InnoDB",
    )
    op.create_index(
        "idx_payroll_run_workforce_snapshots_attempt",
        "payroll_run_workforce_snapshots",
        ["payroll_run_id", "attempt_number"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_payroll_run_workforce_snapshots_attempt",
        table_name="payroll_run_workforce_snapshots",
    )
    op.drop_table("payroll_run_workforce_snapshots")
    op.drop_column("payroll_runs", "attempt_lease_expires_at")
    op.drop_column("payroll_runs", "attempt_number")
