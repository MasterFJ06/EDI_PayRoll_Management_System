from __future__ import annotations

import pytest

from dataclasses import replace

from tests.integration.mysql_support import (
    CheckDefinition,
    ColumnDefinition,
    ForeignKeyDefinition,
    IndexDefinition,
    MySQLTestConfigurationError,
    TableDefinition,
    UniqueDefinition,
    _schema_differences,
    _schema_difference_error,
    _parse_columns_and_constraints,
    mysql_test_url_from_environment,
    parse_mysql_test_url,
    parse_schema_snapshot,
)


@pytest.mark.parametrize(
    "value",
    [
        None,
        "",
        "mysql+pymysql://user:pw@localhost:3306/employee_payroll_db",
        "mysql+pymysql://user:pw@localhost:3306/epms_dev",
        "mysql+pymysql://user:pw@example.com:3306/epms_payroll_test",
        "mysql://user:pw@localhost:3306/epms_payroll_test",
        "mysql+pymysql://user@localhost:3306/epms_payroll_test",
        "mysql+pymysql://user:pw@localhost:3306/epms_payroll_test?init_command=DROP+TABLE+x",
        "mysql+pymysql://user:pw@localhost:3306/epms_payroll_test?charset=utf8mb4",
    ],
)
def test_rejects_missing_or_unsafe_mysql_test_url(value: str | None) -> None:
    with pytest.raises(ValueError):
        parse_mysql_test_url(value)


def test_accepts_explicit_local_test_database_url() -> None:
    target = parse_mysql_test_url(
        "mysql+pymysql://epms_test:secret@127.0.0.1:3307/epms_payroll_test"
    )

    assert target.database_name == "epms_payroll_test"
    assert target.url.host == "127.0.0.1"


def test_optional_mode_allows_missing_url_but_strict_mode_rejects_it_offline() -> None:
    assert mysql_test_url_from_environment({}) is None
    with pytest.raises(MySQLTestConfigurationError, match="required"):
        mysql_test_url_from_environment({"EPMS_REQUIRE_MYSQL_TESTS": "1"})


def test_rejects_invalid_strict_mode_flag() -> None:
    with pytest.raises(MySQLTestConfigurationError, match="must be 0 or 1"):
        mysql_test_url_from_environment({"EPMS_REQUIRE_MYSQL_TESTS": "yes"})


def test_integration_conftest_rejects_xdist_worker(monkeypatch: pytest.MonkeyPatch) -> None:
    import tests.integration.conftest as integration_conftest

    monkeypatch.setenv("PYTEST_XDIST_WORKER", "gw0")
    with pytest.raises(pytest.UsageError, match="cannot run under pytest-xdist"):
        integration_conftest.pytest_configure(None)


def _valid_definition() -> TableDefinition:
    return TableDefinition(
        engine="InnoDB",
        columns={
            "id": ColumnDefinition("id", "bigint unsigned", False, None, False),
            "parent_id": ColumnDefinition("parent_id", "bigint unsigned", False, None, False),
            "name": ColumnDefinition("name", "varchar(50)", False, None, False),
        },
        primary_key=("id",),
        foreign_keys=frozenset({
            ForeignKeyDefinition(("parent_id",), "parents", ("id",), "CASCADE", "RESTRICT")
        }),
        unique_constraints=frozenset({UniqueDefinition(("name",), "uq_sample_name")}),
        indexes=frozenset({IndexDefinition(("parent_id",), False)}),
        checks=frozenset({CheckDefinition("ck_sample", ("id", ">", "0"))}),
    )


@pytest.mark.parametrize(
    "actual, expected_message",
    [
        ("type_sql", "type_sql mismatch"),
        ("nullable", "nullable mismatch"),
    ],
)
def test_schema_comparison_rejects_column_type_and_nullability_mismatches(
    actual: str, expected_message: str
) -> None:
    expected = _valid_definition()
    columns = dict(expected.columns)
    columns["name"] = replace(
        columns["name"], **{actual: "varchar(100)" if actual == "type_sql" else True}
    )
    difference = _schema_differences(expected, replace(expected, columns=columns), "sample")
    assert any(expected_message in item for item in difference)
    assert any("expected" in item and "actual" in item for item in difference)


def test_schema_comparison_rejects_foreign_key_target_mismatch() -> None:
    expected = _valid_definition()
    fks = {replace(next(iter(expected.foreign_keys)), table="other_parent")}
    errors = _schema_differences(expected, replace(expected, foreign_keys=frozenset(fks)))
    assert any("parents" in item and "expected but absent" in item for item in errors)
    assert any("other_parent" in item and "unexpected" in item for item in errors)


def test_schema_comparison_rejects_unique_and_index_definition_mismatches() -> None:
    expected = _valid_definition()
    unique = replace(expected, unique_constraints=frozenset({UniqueDefinition(("parent_id",), "uq_sample_parent")}))
    indexes = replace(expected, indexes=frozenset({IndexDefinition(("name",), False)}))
    assert any("unique_constraints" in item for item in _schema_differences(expected, unique))
    assert any(".indexes mismatch" in item for item in _schema_differences(expected, indexes))


def test_schema_comparison_rejects_check_expression_mismatch() -> None:
    expected = _valid_definition()
    actual = replace(
        expected,
        checks=frozenset({CheckDefinition("mysql_generated_name", ("id", ">=", "0"))}),
    )
    errors = _schema_differences(expected, actual, "sample")
    assert any("sample.check 'ck_sample'" in item and "expected expression" in item for item in errors)
    assert any("unexpected expression" in item and "id" in item for item in errors)


def test_check_metadata_accepts_reliable_layout_and_identifier_quote_changes() -> None:
    expected = _parse_columns_and_constraints(
        """id INT NOT NULL,
        CONSTRAINT ck_state CHECK ((`state` IN ('OPEN', 'CLOSED')))""",
        "InnoDB",
    )
    actual = _parse_columns_and_constraints(
        """id int not null,
        CONSTRAINT generated_check_17 CHECK ( state in ( 'OPEN' , 'CLOSED' ) )""",
        "InnoDB",
    )
    assert _schema_differences(expected, actual, "sample") == []


def test_attendance_status_check_accepts_mysql_charset_introducers() -> None:
    expected = _parse_columns_and_constraints(
        """id INT NOT NULL, CONSTRAINT chk_attendance_status CHECK (
        attendance_status IN ('PRESENT', 'ABSENT', 'HALF_DAY', 'ON_LEAVE', 'HOLIDAY'))""",
        "InnoDB",
    )
    actual = _parse_columns_and_constraints(
        """id INT NOT NULL, CONSTRAINT chk_attendance_status CHECK (
        attendance_status IN (_utf8mb4'PRESENT', _utf8mb4'ABSENT',
        _utf8mb4'HALF_DAY', _utf8mb4'ON_LEAVE', _utf8mb4'HOLIDAY'))""",
        "InnoDB",
    )
    assert _schema_differences(expected, actual, "attendance_records") == []


def test_attendance_time_check_accepts_redundant_predicate_grouping() -> None:
    expected = _parse_columns_and_constraints(
        """check_in_time DATETIME NULL, check_out_time DATETIME NULL,
        CONSTRAINT chk_attendance_time_order CHECK (
        check_out_time IS NULL OR check_in_time IS NULL OR check_out_time >= check_in_time)""",
        "InnoDB",
    )
    actual = _parse_columns_and_constraints(
        """check_in_time DATETIME NULL, check_out_time DATETIME NULL,
        CONSTRAINT chk_attendance_time_order CHECK (
        ((check_out_time IS NULL) OR (check_in_time IS NULL)
        OR (check_out_time >= check_in_time)))""",
        "InnoDB",
    )
    assert _schema_differences(expected, actual, "attendance_records") == []


@pytest.mark.parametrize(
    "actual_expression",
    [
        "attendance_status IN ('PRESENT', 'ABSENT', 'HALF_DAY', 'ON_LEAVE', 'WEEKEND')",
        "attendance_status IN ('PRESENT', 'ABSENT', 'HALF_DAY', 'ON_LEAVE')",
    ],
)
def test_attendance_status_check_keeps_allowed_values_and_conditions_strict(
    actual_expression: str,
) -> None:
    expected = _parse_columns_and_constraints(
        "id INT NOT NULL, CONSTRAINT chk_attendance_status CHECK "
        "(attendance_status IN ('PRESENT', 'ABSENT', 'HALF_DAY', 'ON_LEAVE', 'HOLIDAY'))",
        "InnoDB",
    )
    actual = _parse_columns_and_constraints(
        f"id INT NOT NULL, CONSTRAINT chk_attendance_status CHECK ({actual_expression})",
        "InnoDB",
    )
    assert _schema_differences(expected, actual, "attendance_records")


def test_check_normalization_preserves_boolean_precedence() -> None:
    expected = _parse_columns_and_constraints(
        "id INT NOT NULL, CONSTRAINT ck_logic CHECK (id = 1 OR (id = 2 AND id = 3))",
        "InnoDB",
    )
    actual = _parse_columns_and_constraints(
        "id INT NOT NULL, CONSTRAINT ck_logic CHECK ((id = 1 OR id = 2) AND id = 3)",
        "InnoDB",
    )
    assert _schema_differences(expected, actual, "sample")


def test_check_normalization_does_not_equate_different_operators() -> None:
    expected = _parse_columns_and_constraints(
        "id INT NOT NULL, CONSTRAINT ck_positive CHECK (id > 0)", "InnoDB"
    )
    actual = _parse_columns_and_constraints(
        "id INT NOT NULL, CONSTRAINT ck_nonnegative CHECK (id >= 0)", "InnoDB"
    )
    errors = _schema_differences(expected, actual, "sample")
    assert any("id" in item and ">" in item and "no equivalent actual" in item for item in errors)
    assert any(">=" in item and "unexpected expression" in item for item in errors)


def test_nullable_missing_and_explicit_null_defaults_are_equivalent() -> None:
    expected = _valid_definition()
    columns = dict(expected.columns)
    columns["name"] = replace(columns["name"], nullable=True, default_sql=None)
    expected = replace(expected, columns=columns)
    actual_columns = dict(columns)
    actual_columns["name"] = replace(actual_columns["name"], default_sql="null")
    actual = replace(expected, columns=actual_columns)
    assert _schema_differences(expected, actual, "sample") == []


@pytest.mark.parametrize(
    ("nullable", "actual_default"),
    [(False, "null"), (True, "'null'"), (True, "0"), (True, "current_timestamp")],
)
def test_default_comparison_preserves_non_equivalent_defaults(
    nullable: bool, actual_default: str
) -> None:
    expected = _valid_definition()
    columns = dict(expected.columns)
    columns["name"] = replace(columns["name"], nullable=nullable, default_sql=None)
    expected = replace(expected, columns=columns)
    actual_columns = dict(expected.columns)
    actual_columns["name"] = replace(
        actual_columns["name"], nullable=nullable, default_sql=actual_default
    )
    actual = replace(expected, columns=actual_columns)
    error = _schema_difference_error(_schema_differences(expected, actual, "sample"))
    assert "sample.name.default_sql mismatch" in str(error)


@pytest.mark.parametrize(
    ("table_name", "expected_column", "actual_column"),
    [
        ("leave_balances", "allocated_days DECIMAL(6,2) NOT NULL DEFAULT 0.00", "allocated_days DECIMAL(6,2) NOT NULL DEFAULT '0.00'"),
        ("leave_balances", "used_days DECIMAL(6,2) NOT NULL DEFAULT 0.00", "used_days DECIMAL(6,2) NOT NULL DEFAULT '0.00'"),
        ("payroll_runs", "attempt_number BIGINT UNSIGNED NOT NULL DEFAULT 0", "attempt_number BIGINT UNSIGNED NOT NULL DEFAULT '0'"),
        ("leave_types", "is_active BOOLEAN NOT NULL DEFAULT TRUE", "is_active TINYINT ( 1 ) NOT NULL DEFAULT '1'"),
        ("roles", "is_active BOOLEAN NOT NULL DEFAULT TRUE", "is_active TINYINT ( 1 ) NOT NULL DEFAULT '1'"),
        ("salary_revision_components", "is_overtime_base BOOLEAN NOT NULL DEFAULT FALSE", "is_overtime_base TINYINT ( 1 ) NOT NULL DEFAULT '0'"),
    ],
)
def test_numeric_defaults_accept_equivalent_mysql_reflection_values(
    table_name: str, expected_column: str, actual_column: str
) -> None:
    expected = _parse_columns_and_constraints(expected_column, "InnoDB")
    actual = _parse_columns_and_constraints(actual_column, "InnoDB")
    assert _schema_differences(expected, actual, table_name) == []


@pytest.mark.parametrize(
    ("actual_column", "expected_attribute"),
    [
        ("allocated_days DECIMAL(6,2) NOT NULL DEFAULT '0.01'", "default_sql"),
        ("allocated_days DECIMAL(6,2) NOT NULL DEFAULT 'unknown'", "default_sql"),
        ("allocated_days VARCHAR(10) NOT NULL DEFAULT '0.00'", "type_sql"),
    ],
)
def test_numeric_default_normalization_keeps_different_values_and_types(
    actual_column: str, expected_attribute: str
) -> None:
    expected = _parse_columns_and_constraints(
        "allocated_days DECIMAL(6,2) NOT NULL DEFAULT 0.00", "InnoDB"
    )
    actual = _parse_columns_and_constraints(actual_column, "InnoDB")
    assert any(
        f".{expected_attribute}" in difference
        for difference in _schema_differences(expected, actual, "sample")
    )


def test_type_normalization_removes_spacing_but_preserves_modifiers() -> None:
    expected = _parse_columns_and_constraints(
        "value TINYINT(1) NOT NULL DEFAULT 1", "InnoDB"
    )
    formatted = _parse_columns_and_constraints(
        "value TINYINT ( 1 ) NOT NULL DEFAULT 1", "InnoDB"
    )
    different_length = _parse_columns_and_constraints(
        "value TINYINT(2) NOT NULL DEFAULT 1", "InnoDB"
    )
    different_modifier = _parse_columns_and_constraints(
        "value TINYINT(1) UNSIGNED NOT NULL DEFAULT 1", "InnoDB"
    )
    assert _schema_differences(expected, formatted, "sample") == []
    assert any("type_sql mismatch" in error for error in _schema_differences(expected, different_length, "sample"))
    assert any("type_sql mismatch" in error for error in _schema_differences(expected, different_modifier, "sample"))


def test_schema_verification_error_preserves_exact_column_and_check_details() -> None:
    expected = _valid_definition()
    actual_columns = dict(expected.columns)
    actual_columns["name"] = replace(
        actual_columns["name"],
        type_sql="varchar(100)",
        nullable=True,
        default_sql="NULL",
    )
    actual = replace(
        expected,
        columns=actual_columns,
        checks=frozenset({CheckDefinition("mysql_check_17", ("id", ">=", "0"))}),
    )

    error = _schema_difference_error(_schema_differences(expected, actual, "sample"))
    message = str(error)
    assert "sample.name.type_sql mismatch: expected 'varchar(50)'; actual 'varchar(100)'" in message
    assert "sample.name.nullable mismatch: expected False; actual True" in message
    assert "sample.name.default_sql mismatch: expected None; actual 'NULL'" in message
    assert "sample.check 'ck_sample' expected expression ('id', '>', '0')" in message
    assert "sample.check 'mysql_check_17' unexpected expression ('id', '>=', '0')" in message


def test_current_snapshot_parser_captures_full_payroll_schema_definitions() -> None:
    schema = parse_schema_snapshot()
    assert len(schema) == 33
    assert schema["users"].columns["user_id"].type_sql == "bigint unsigned"
    assert schema["users"].columns["user_id"].auto_increment
    assert schema["users"].primary_key == ("user_id",)
    assert {item.columns for item in schema["users"].unique_constraints} == {("username",), ("email",)}
    assert schema["employees"].foreign_keys
    assert schema["users"].checks
    assert schema["leave_balances"].columns["allocated_days"] == ColumnDefinition(
        "allocated_days", "decimal(6,2)", False, "0.00", False
    )
    assert schema["leave_balances"].columns["used_days"].default_sql == "0.00"
    assert schema["leave_types"].columns["is_active"] == ColumnDefinition(
        "is_active", "tinyint(1)", False, "1", False
    )
    assert schema["roles"].columns["is_active"] == schema["leave_types"].columns["is_active"]
    assert schema["payroll_runs"].columns["attempt_number"] == ColumnDefinition(
        "attempt_number", "bigint unsigned", False, "0", False
    )
    assert schema["salary_revision_components"].columns["is_overtime_base"] == ColumnDefinition(
        "is_overtime_base", "tinyint(1)", False, "0", False
    )
