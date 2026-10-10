from datetime import date
from decimal import Decimal
from importlib import import_module

from sqlalchemy import CheckConstraint, UniqueConstraint
from sqlalchemy.dialects import mysql

from app.infrastructure.persistence.models import (
    LeaveRequestDayModel,
    PayrollResultModel,
    SalaryRevisionComponentModel,
    WorkCalendarDateOverrideModel,
    WorkCalendarVersionModel,
    WorkCalendarWeeklyRuleModel,
    WorkforceOvertimePolicyVersionModel,
)
from app.infrastructure.persistence.models.base import Base

_migration = import_module(
    "migrations.versions.20261007_01_workforce_schema_foundation"
)


NEW_MODELS = {
    "work_calendar_versions": WorkCalendarVersionModel,
    "work_calendar_weekly_rules": WorkCalendarWeeklyRuleModel,
    "work_calendar_date_overrides": WorkCalendarDateOverrideModel,
    "leave_request_days": LeaveRequestDayModel,
    "workforce_overtime_policy_versions": WorkforceOvertimePolicyVersionModel,
}


def test_workforce_models_are_registered_and_use_innodb() -> None:
    assert set(NEW_MODELS) <= set(Base.metadata.tables)
    for model in NEW_MODELS.values():
        assert model.__table__.dialect_options["mysql"]["engine"] == "InnoDB"


def test_workforce_models_use_mysql_compatible_unsigned_foreign_keys() -> None:
    for model in NEW_MODELS.values():
        for column in model.__table__.columns:
            if column.primary_key or column.foreign_keys:
                assert column.type.compile(dialect=mysql.dialect()) == "BIGINT UNSIGNED"
            for foreign_key in column.foreign_keys:
                assert foreign_key.onupdate == "RESTRICT"
                assert foreign_key.ondelete in {"RESTRICT", "CASCADE"}

    assert str(next(iter(WorkCalendarVersionModel.__table__.c.created_by_user_id.foreign_keys)).target_fullname) == "users.user_id"
    assert str(next(iter(WorkforceOvertimePolicyVersionModel.__table__.c.created_by_user_id.foreign_keys)).target_fullname) == "users.user_id"
    assert str(next(iter(LeaveRequestDayModel.__table__.c.leave_request_id.foreign_keys)).target_fullname) == "leave_requests.leave_request_id"


def test_work_calendar_schema_constraints_are_registered() -> None:
    weekly = WorkCalendarWeeklyRuleModel.__table__
    weekly_unique = {
        tuple(column.name for column in constraint.columns)
        for constraint in weekly.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert ("work_calendar_version_id", "iso_weekday") in weekly_unique
    assert {constraint.name for constraint in weekly.constraints if isinstance(constraint, CheckConstraint)} >= {
        "chk_work_calendar_iso_weekday",
        "chk_work_calendar_weekly_classification",
        "chk_work_calendar_weekly_minutes",
    }

    overrides = WorkCalendarDateOverrideModel.__table__
    assert any(index.name == "idx_work_calendar_override_date" for index in overrides.indexes)
    assert {constraint.name for constraint in overrides.constraints if isinstance(constraint, CheckConstraint)} >= {
        "chk_work_calendar_override_classification",
        "chk_work_calendar_holiday_label",
    }


def test_foundation_models_construct_with_decimal_and_date_values() -> None:
    calendar = WorkCalendarVersionModel(
        version_number=1,
        effective_from=date(2026, 1, 1),
        effective_to=None,
        time_zone="Asia/Kolkata",
        created_by_user_id=7,
    )
    weekly_rule = WorkCalendarWeeklyRuleModel(
        work_calendar_version_id=1,
        iso_weekday=1,
        classification="WORKING_DAY",
        scheduled_minutes=480,
    )
    override = WorkCalendarDateOverrideModel(
        work_calendar_version_id=1,
        override_date=date(2026, 1, 26),
        classification="HOLIDAY",
        label="Republic Day",
    )
    leave_day = LeaveRequestDayModel(
        leave_request_id=3, leave_date=date(2026, 1, 5), day_fraction=Decimal("0.50")
    )
    policy = WorkforceOvertimePolicyVersionModel(
        version_number=1,
        effective_from=date(2026, 1, 1),
        effective_to=None,
        non_working_multiplier=Decimal("2.0000"),
        created_by_user_id=7,
    )

    assert calendar.time_zone == "Asia/Kolkata"
    assert weekly_rule.scheduled_minutes == 480
    assert override.label == "Republic Day"
    assert leave_day.day_fraction == Decimal("0.50")
    assert policy.non_working_multiplier == Decimal("2.0000")


def test_overtime_and_snapshot_columns_match_locked_foundation_shape() -> None:
    overtime = SalaryRevisionComponentModel.__table__.c.is_overtime_base
    snapshot = PayrollResultModel.__table__.c.workforce_calculation_snapshot

    assert overtime.nullable is False
    assert str(overtime.server_default.arg).upper() == "FALSE"
    assert overtime.type.compile(dialect=mysql.dialect()) == "BOOL"
    assert snapshot.nullable is True
    assert snapshot.type.compile(dialect=mysql.dialect()) == "JSON"


def test_leave_treatment_model_column_is_required_and_constrained() -> None:
    from app.infrastructure.persistence.models import LeaveTypeModel

    column = LeaveTypeModel.__table__.c.payroll_treatment
    checks = {
        constraint.name: str(constraint.sqltext)
        for constraint in LeaveTypeModel.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert column.nullable is False
    assert checks["chk_leave_types_payroll_treatment"] == "payroll_treatment IN ('PAID', 'UNPAID')"


def test_migration_requires_explicit_complete_legacy_leave_mapping() -> None:
    parse = _migration._parse_leave_type_mapping

    assert parse("1:PAID,2:UNPAID", {1, 2}) == {1: "PAID", 2: "UNPAID"}
    try:
        parse(None, {1})
    except RuntimeError as exc:
        assert "owner-approved mapping" in str(exc)
    else:
        raise AssertionError("Existing Leave Types must block without an explicit mapping")

    for invalid in ("1:PAID,1:UNPAID", "1:UNKNOWN", "1:PAID,2:UNPAID"):
        try:
            parse(invalid, {1})
        except RuntimeError:
            pass
        else:
            raise AssertionError(f"Invalid or incomplete mapping accepted: {invalid}")
