"""Add Workforce schema foundation for Decisions 27-30.

Revision ID: 20261007_01
Revises: None
Create Date: 2026-10-07

Existing Leave Types require an owner-approved mapping when rows already exist.
Supply it as an Alembic x-argument, for example:
    alembic -x leave_type_mapping=1:PAID,2:UNPAID upgrade head
The migration validates the complete mapping before making any schema change.
"""

from __future__ import annotations

from collections.abc import Mapping

import sqlalchemy as sa
from alembic import context, op
from sqlalchemy.dialects import mysql


revision = "20261007_01"
down_revision = None
branch_labels = None
depends_on = None


_LEAVE_TREATMENTS = {"PAID", "UNPAID"}


def _parse_leave_type_mapping(
    raw_mapping: str | None, existing_ids: set[int]
) -> dict[int, str]:
    if not existing_ids:
        if raw_mapping:
            raise RuntimeError(
                "Leave Type mapping was supplied, but no existing Leave Types need mapping."
            )
        return {}
    if not raw_mapping:
        raise RuntimeError(
            "Workforce schema migration blocked: existing Leave Types require an "
            "owner-approved mapping. Supply -x leave_type_mapping=ID:PAID,ID:UNPAID; "
            "no treatment can be inferred from existing data."
        )

    mapping: dict[int, str] = {}
    try:
        for pair in raw_mapping.split(","):
            leave_type_id_text, treatment_text = pair.split(":", 1)
            leave_type_id = int(leave_type_id_text)
            treatment = treatment_text.upper()
            if leave_type_id in mapping or treatment not in _LEAVE_TREATMENTS:
                raise ValueError
            mapping[leave_type_id] = treatment
    except (TypeError, ValueError) as exc:
        raise RuntimeError(
            "Invalid Leave Type mapping. Use unique ID:PAID or ID:UNPAID pairs."
        ) from exc

    if set(mapping) != existing_ids:
        raise RuntimeError(
            "Leave Type mapping must cover every existing Leave Type exactly once; "
            f"expected IDs {sorted(existing_ids)}, received IDs {sorted(mapping)}."
        )
    return mapping


def _existing_leave_type_mapping(connection: sa.Connection) -> dict[int, str]:
    existing_ids = {
        int(row[0])
        for row in connection.execute(
            sa.text("SELECT leave_type_id FROM leave_types ORDER BY leave_type_id")
        )
    }
    raw_mapping = context.get_x_argument(as_dictionary=True).get(
        "leave_type_mapping"
    )
    return _parse_leave_type_mapping(raw_mapping, existing_ids)


def _backfill_leave_treatments(
    connection: sa.Connection, mapping: Mapping[int, str]
) -> None:
    for leave_type_id, treatment in mapping.items():
        connection.execute(
            sa.text(
                "UPDATE leave_types SET payroll_treatment = :treatment "
                "WHERE leave_type_id = :leave_type_id"
            ),
            {"treatment": treatment, "leave_type_id": leave_type_id},
        )


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    required_existing_tables = {
        "users",
        "leave_types",
        "leave_requests",
        "salary_revision_components",
        "payroll_results",
    }
    missing = required_existing_tables - set(inspector.get_table_names())
    if missing:
        raise RuntimeError(
            "Workforce schema migration requires the authoritative base schema; "
            f"missing tables: {sorted(missing)}."
        )

    # Validate legacy data before any DDL because MySQL DDL implicitly commits.
    leave_treatments = _existing_leave_type_mapping(connection)

    op.create_table(
        "work_calendar_versions",
        sa.Column(
            "work_calendar_version_id", mysql.BIGINT(unsigned=True),
            primary_key=True, autoincrement=True,
        ),
        sa.Column("version_number", mysql.INTEGER(unsigned=True), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("time_zone", sa.String(length=64), nullable=False),
        sa.Column("created_by_user_id", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("replaces_version_id", mysql.BIGINT(unsigned=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint(
            "work_calendar_version_id", name="pk_work_calendar_versions"
        ),
        sa.UniqueConstraint("version_number", name="uq_work_calendar_version_number"),
        sa.CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="chk_work_calendar_version_dates",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"], ["users.user_id"],
            name="fk_work_calendar_version_creator",
            ondelete="RESTRICT", onupdate="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["replaces_version_id"],
            ["work_calendar_versions.work_calendar_version_id"],
            name="fk_work_calendar_version_replacement",
            ondelete="RESTRICT", onupdate="RESTRICT",
        ),
        mysql_engine="InnoDB",
    )
    op.create_index(
        "idx_work_calendar_version_dates", "work_calendar_versions",
        ["effective_from", "effective_to"],
    )
    op.create_index(
        "idx_work_calendar_version_replacement", "work_calendar_versions",
        ["replaces_version_id"],
    )

    op.create_table(
        "work_calendar_weekly_rules",
        sa.Column(
            "work_calendar_weekly_rule_id", mysql.BIGINT(unsigned=True),
            primary_key=True, autoincrement=True,
        ),
        sa.Column("work_calendar_version_id", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("iso_weekday", mysql.TINYINT(unsigned=True), nullable=False),
        sa.Column("classification", sa.String(length=20), nullable=False),
        sa.Column("scheduled_minutes", mysql.SMALLINT(unsigned=True), nullable=False),
        sa.PrimaryKeyConstraint(
            "work_calendar_weekly_rule_id", name="pk_work_calendar_weekly_rules"
        ),
        sa.UniqueConstraint(
            "work_calendar_version_id", "iso_weekday", name="uq_work_calendar_weekday"
        ),
        sa.CheckConstraint(
            "iso_weekday BETWEEN 1 AND 7", name="chk_work_calendar_iso_weekday"
        ),
        sa.CheckConstraint(
            "classification IN ('WORKING_DAY', 'NON_WORKING_DAY')",
            name="chk_work_calendar_weekly_classification",
        ),
        sa.CheckConstraint(
            "(classification = 'WORKING_DAY' AND scheduled_minutes = 480) "
            "OR (classification = 'NON_WORKING_DAY' AND scheduled_minutes = 0)",
            name="chk_work_calendar_weekly_minutes",
        ),
        sa.ForeignKeyConstraint(
            ["work_calendar_version_id"],
            ["work_calendar_versions.work_calendar_version_id"],
            name="fk_work_calendar_weekly_version",
            ondelete="CASCADE", onupdate="RESTRICT",
        ),
        mysql_engine="InnoDB",
    )

    op.create_table(
        "work_calendar_date_overrides",
        sa.Column(
            "work_calendar_date_override_id", mysql.BIGINT(unsigned=True),
            primary_key=True, autoincrement=True,
        ),
        sa.Column("work_calendar_version_id", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("override_date", sa.Date(), nullable=False),
        sa.Column("classification", sa.String(length=20), nullable=False),
        sa.Column("label", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint(
            "work_calendar_date_override_id", name="pk_work_calendar_date_overrides"
        ),
        sa.UniqueConstraint(
            "work_calendar_version_id", "override_date",
            name="uq_work_calendar_date_override",
        ),
        sa.CheckConstraint(
            "classification IN ('WORKING_DAY', 'NON_WORKING_DAY', 'HOLIDAY')",
            name="chk_work_calendar_override_classification",
        ),
        sa.CheckConstraint(
            "classification <> 'HOLIDAY' OR "
            "(label IS NOT NULL AND CHAR_LENGTH(TRIM(label)) > 0)",
            name="chk_work_calendar_holiday_label",
        ),
        sa.ForeignKeyConstraint(
            ["work_calendar_version_id"],
            ["work_calendar_versions.work_calendar_version_id"],
            name="fk_work_calendar_override_version",
            ondelete="CASCADE", onupdate="RESTRICT",
        ),
        mysql_engine="InnoDB",
    )
    op.create_index(
        "idx_work_calendar_override_date", "work_calendar_date_overrides",
        ["override_date"],
    )

    op.create_table(
        "leave_request_days",
        sa.Column(
            "leave_request_day_id", mysql.BIGINT(unsigned=True),
            primary_key=True, autoincrement=True,
        ),
        sa.Column("leave_request_id", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("leave_date", sa.Date(), nullable=False),
        sa.Column("day_fraction", sa.Numeric(4, 2), nullable=False),
        sa.PrimaryKeyConstraint("leave_request_day_id", name="pk_leave_request_days"),
        sa.UniqueConstraint(
            "leave_request_id", "leave_date", name="uq_leave_request_day"
        ),
        sa.CheckConstraint(
            "day_fraction >= 0.01 AND day_fraction <= 1.00",
            name="chk_leave_request_day_fraction",
        ),
        sa.ForeignKeyConstraint(
            ["leave_request_id"], ["leave_requests.leave_request_id"],
            name="fk_leave_request_day_request",
            ondelete="CASCADE", onupdate="RESTRICT",
        ),
        mysql_engine="InnoDB",
    )

    op.create_table(
        "workforce_overtime_policy_versions",
        sa.Column(
            "workforce_overtime_policy_version_id", mysql.BIGINT(unsigned=True),
            primary_key=True, autoincrement=True,
        ),
        sa.Column("version_number", mysql.INTEGER(unsigned=True), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("non_working_multiplier", sa.Numeric(8, 4), nullable=False),
        sa.Column("created_by_user_id", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint(
            "workforce_overtime_policy_version_id",
            name="pk_workforce_overtime_policy_versions",
        ),
        sa.UniqueConstraint(
            "version_number", name="uq_workforce_overtime_policy_version"
        ),
        sa.CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="chk_workforce_overtime_policy_dates",
        ),
        sa.CheckConstraint(
            "non_working_multiplier >= 0",
            name="chk_workforce_overtime_non_working_multiplier",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"], ["users.user_id"],
            name="fk_workforce_overtime_policy_creator",
            ondelete="RESTRICT", onupdate="RESTRICT",
        ),
        mysql_engine="InnoDB",
    )
    op.create_index(
        "idx_workforce_overtime_policy_dates", "workforce_overtime_policy_versions",
        ["effective_from", "effective_to"],
    )

    if leave_treatments:
        op.add_column(
            "leave_types", sa.Column("payroll_treatment", sa.String(10), nullable=True)
        )
        for leave_type_id, treatment in leave_treatments.items():
            connection.execute(
                sa.text(
                    "UPDATE leave_types SET payroll_treatment = :treatment "
                    "WHERE leave_type_id = :leave_type_id"
                ),
                {"treatment": treatment, "leave_type_id": leave_type_id},
            )
        op.alter_column(
            "leave_types", "payroll_treatment", existing_type=sa.String(10),
            nullable=False,
        )
    else:
        op.add_column(
            "leave_types", sa.Column("payroll_treatment", sa.String(10), nullable=False)
        )
    op.create_check_constraint(
        "chk_leave_types_payroll_treatment", "leave_types",
        "payroll_treatment IN ('PAID', 'UNPAID')",
    )

    op.add_column(
        "salary_revision_components",
        sa.Column(
            "is_overtime_base", sa.Boolean(), nullable=False,
            server_default=sa.text("FALSE"),
        ),
    )
    op.create_check_constraint(
        "chk_salary_overtime_base_boolean", "salary_revision_components",
        "is_overtime_base IN (0, 1)",
    )

    op.add_column(
        "payroll_results",
        sa.Column("workforce_calculation_snapshot", mysql.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("payroll_results", "workforce_calculation_snapshot")
    op.drop_constraint(
        "chk_salary_overtime_base_boolean", "salary_revision_components", type_="check"
    )
    op.drop_column("salary_revision_components", "is_overtime_base")
    op.drop_constraint(
        "chk_leave_types_payroll_treatment", "leave_types", type_="check"
    )
    op.drop_column("leave_types", "payroll_treatment")

    op.drop_index(
        "idx_workforce_overtime_policy_dates",
        table_name="workforce_overtime_policy_versions",
    )
    op.drop_table("workforce_overtime_policy_versions")
    op.drop_table("leave_request_days")
    op.drop_index(
        "idx_work_calendar_override_date",
        table_name="work_calendar_date_overrides",
    )
    op.drop_table("work_calendar_date_overrides")
    op.drop_table("work_calendar_weekly_rules")
    op.drop_constraint(
        "fk_work_calendar_version_replacement",
        "work_calendar_versions",
        type_="foreignkey",
    )
    op.drop_index(
        "idx_work_calendar_version_replacement",
        table_name="work_calendar_versions",
    )
    op.drop_index(
        "idx_work_calendar_version_dates", table_name="work_calendar_versions"
    )
    op.drop_table("work_calendar_versions")
