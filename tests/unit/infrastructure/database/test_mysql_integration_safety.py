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


def test_column_diagnostics_identify_default_difference() -> None:
    expected = _valid_definition()
    columns = dict(expected.columns)
    columns["name"] = replace(columns["name"], default_sql=None)
    expected = replace(expected, columns=columns)
    actual_columns = dict(columns)
    actual_columns["name"] = replace(actual_columns["name"], default_sql="null")
    actual = replace(expected, columns=actual_columns)
    error = _schema_difference_error(_schema_differences(expected, actual, "sample"))
    assert "sample.name.default_sql mismatch: expected None; actual 'null'" in str(error)


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
