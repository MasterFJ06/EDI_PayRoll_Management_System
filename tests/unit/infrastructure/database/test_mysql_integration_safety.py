from __future__ import annotations

import pytest

from dataclasses import replace

from tests.integration.mysql_support import (
    ColumnDefinition,
    ForeignKeyDefinition,
    IndexDefinition,
    MySQLTestConfigurationError,
    TableDefinition,
    _schema_differences,
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
        unique_constraints=frozenset({("name",)}),
        indexes=frozenset({IndexDefinition(("parent_id",), False)}),
        checks=frozenset({"id > 0"}),
    )


@pytest.mark.parametrize(
    "actual, expected_message",
    [
        ("type_sql", "column definition mismatch"),
        ("nullable", "column definition mismatch"),
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


def test_schema_comparison_rejects_foreign_key_target_mismatch() -> None:
    expected = _valid_definition()
    fks = {replace(next(iter(expected.foreign_keys)), table="other_parent")}
    assert any("foreign-key" in item for item in _schema_differences(expected, replace(expected, foreign_keys=frozenset(fks))))


def test_schema_comparison_rejects_unique_and_index_definition_mismatches() -> None:
    expected = _valid_definition()
    unique = replace(expected, unique_constraints=frozenset({("parent_id",)}))
    indexes = replace(expected, indexes=frozenset({IndexDefinition(("name",), False)}))
    assert any("unique-constraint" in item for item in _schema_differences(expected, unique))
    assert any("index definition" in item for item in _schema_differences(expected, indexes))


def test_schema_comparison_rejects_check_expression_mismatch() -> None:
    expected = _valid_definition()
    actual = replace(expected, checks=frozenset({"id >= 0"}))
    assert any("check-constraint" in item for item in _schema_differences(expected, actual))


def test_current_snapshot_parser_captures_full_payroll_schema_definitions() -> None:
    schema = parse_schema_snapshot()
    assert len(schema) == 33
    assert schema["users"].columns["user_id"].type_sql == "bigint unsigned"
    assert schema["users"].columns["user_id"].auto_increment
    assert schema["users"].primary_key == ("user_id",)
    assert schema["users"].unique_constraints == frozenset({("username",), ("email",)})
    assert schema["employees"].foreign_keys
    assert schema["users"].checks
