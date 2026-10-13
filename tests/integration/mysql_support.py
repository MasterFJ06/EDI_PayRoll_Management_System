"""Safety and read-only schema checks for the opt-in MySQL integration suite.

The future CI job must prepare a named snapshot with
``scripts/prepare_mysql_test_schema.py``, import that exact returned file into
a newly created ephemeral MySQL 8 database, fail on import errors, never run
Alembic, and run this module's schema preflight before seeding. Inspection can
check definitions but cannot establish snapshot provenance.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Mapping

from sqlalchemy import Engine, inspect, text
from sqlalchemy.engine import URL, make_url

from scripts.prepare_mysql_test_schema import validate_test_database_name

_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "database" / "schema.sql"
_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "mysql"}
_TABLE_RE = re.compile(r"(?is)CREATE\s+TABLE\s+`?(\w+)`?\s*\((.*?)\)\s*ENGINE\s*=\s*(\w+)")
_REQUIRED_PATH_TABLES = {
    "users", "roles", "permissions", "user_roles", "role_permissions",
    "employees", "departments", "designations", "attendance_records",
    "employee_salary_assignments", "salary_revisions", "salary_revision_components",
    "salary_structures", "salary_components", "work_calendar_versions",
    "work_calendar_weekly_rules", "work_calendar_date_overrides",
    "workforce_overtime_policy_versions", "payroll_runs", "payroll_results",
    "payroll_result_components", "payroll_processing_issues",
    "payroll_run_workforce_snapshots", "audit_events", "audit_event_changes",
    "payslips", "refresh_tokens",
    "leave_types", "leave_requests", "leave_request_days", "leave_balances",
}


class MySQLTestConfigurationError(ValueError):
    pass


class SchemaVerificationError(ValueError):
    """A prepared-snapshot definition does not match MySQL metadata."""


@dataclass(frozen=True)
class MySQLTestTarget:
    url: URL
    database_name: str


@dataclass(frozen=True)
class ColumnDefinition:
    name: str
    type_sql: str
    nullable: bool
    default_sql: str | None
    generated: bool
    on_update_sql: str | None = None
    auto_increment: bool = False


@dataclass(frozen=True)
class ForeignKeyDefinition:
    columns: tuple[str, ...]
    table: str
    referred_columns: tuple[str, ...]
    ondelete: str | None
    onupdate: str | None
    name: str | None = field(default=None, compare=False)


@dataclass(frozen=True)
class UniqueDefinition:
    columns: tuple[str, ...]
    name: str | None = field(default=None, compare=False)


@dataclass(frozen=True)
class IndexDefinition:
    columns: tuple[str, ...]
    unique: bool
    name: str | None = field(default=None, compare=False)


@dataclass(frozen=True)
class CheckDefinition:
    name: str | None
    expression: tuple[str, ...]


@dataclass(frozen=True)
class TableDefinition:
    engine: str
    columns: Mapping[str, ColumnDefinition]
    primary_key: tuple[str, ...]
    foreign_keys: frozenset[ForeignKeyDefinition]
    unique_constraints: frozenset[UniqueDefinition]
    indexes: frozenset[IndexDefinition]
    checks: frozenset[CheckDefinition]


def parse_mysql_test_url(value: str | None) -> MySQLTestTarget:
    if not value:
        raise MySQLTestConfigurationError("EPMS_MYSQL_TEST_URL is required.")
    try:
        url = make_url(value)
    except Exception as exc:
        raise MySQLTestConfigurationError("Invalid MySQL test URL.") from exc
    if url.query:
        raise MySQLTestConfigurationError("MySQL test URL query options are not allowed.")
    if url.drivername != "mysql+pymysql":
        raise MySQLTestConfigurationError("MySQL test URL must use mysql+pymysql.")
    if (url.host or "").lower() not in _LOCAL_HOSTS:
        raise MySQLTestConfigurationError("MySQL test host must be local or the mysql service.")
    if not url.port or not url.username or not url.password:
        raise MySQLTestConfigurationError("MySQL test URL requires explicit credentials and port.")
    try:
        database_name = validate_test_database_name(url.database)
    except ValueError as exc:
        raise MySQLTestConfigurationError(str(exc)) from exc
    return MySQLTestTarget(url, database_name)


def mysql_test_url_from_environment(environ: Mapping[str, str] | None = None) -> str | None:
    env = os.environ if environ is None else environ
    value = env.get("EPMS_MYSQL_TEST_URL")
    strict = env.get("EPMS_REQUIRE_MYSQL_TESTS", "0")
    if strict not in {"0", "1"}:
        raise MySQLTestConfigurationError("EPMS_REQUIRE_MYSQL_TESTS must be 0 or 1.")
    if not value and strict == "1":
        raise MySQLTestConfigurationError(
            "EPMS_MYSQL_TEST_URL is required when EPMS_REQUIRE_MYSQL_TESTS=1."
        )
    return value


def _normalize_sql(value: str | None) -> str | None:
    if value is None:
        return None
    return " ".join(_sql_tokens(value))


def _normalize_type_sql(value: str) -> str:
    """Normalize type punctuation spacing without changing type modifiers."""
    normalized = _normalize_sql(value) or ""
    normalized = re.sub(r"\s*\(\s*", "(", normalized)
    normalized = re.sub(r"\s*\)", ")", normalized)
    return re.sub(r"\s*,\s*", ",", normalized)


_NUMERIC_TYPE_RE = re.compile(
    r"^(?:tinyint|smallint|mediumint|int|integer|bigint|decimal|numeric|float|double|real)"
    r"(?:\s|\(|$)"
)
_NUMERIC_LITERAL_RE = re.compile(
    r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$"
)


def _numeric_default(column: ColumnDefinition, value: str | None) -> Decimal | None:
    """Parse a numeric default only for a numeric SQL column."""
    if value is None or not _NUMERIC_TYPE_RE.match(column.type_sql):
        return None
    candidate = value
    if (
        len(candidate) >= 2
        and candidate[0] == candidate[-1]
        and candidate[0] in "'\""
    ):
        candidate = candidate[1:-1]
    if not _NUMERIC_LITERAL_RE.fullmatch(candidate):
        return None
    try:
        return Decimal(candidate)
    except InvalidOperation:
        return None


def _numeric_defaults_equivalent(
    expected_column: ColumnDefinition, actual_column: ColumnDefinition
) -> bool:
    if expected_column.type_sql != actual_column.type_sql:
        return False
    expected_value = _numeric_default(expected_column, expected_column.default_sql)
    actual_value = _numeric_default(actual_column, actual_column.default_sql)
    return (
        expected_value is not None
        and actual_value is not None
        and expected_value == actual_value
    )


def _sql_tokens(value: str) -> tuple[str, ...]:
    """Normalize SQL identifiers and spacing while preserving literal values."""
    tokens: list[str] = []
    index = 0
    while index < len(value):
        char = value[index]
        if char.isspace():
            index += 1
        elif char == "`":
            end = value.find("`", index + 1)
            if end < 0:
                tokens.append(value[index:].casefold())
                break
            tokens.append(value[index + 1:end].casefold())
            index = end + 1
        elif char in "'\"":
            quote = char
            end = index + 1
            literal = [char]
            while end < len(value):
                current = value[end]
                literal.append(current)
                if current == "\\" and end + 1 < len(value):
                    end += 1
                    literal.append(value[end])
                elif current == quote:
                    if end + 1 < len(value) and value[end + 1] == quote:
                        end += 1
                        literal.append(value[end])
                    else:
                        end += 1
                        break
                end += 1
            tokens.append("".join(literal))
            index = end
        elif char.isalnum() or char in "_$":
            end = index + 1
            while end < len(value) and (value[end].isalnum() or value[end] in "_$."):
                end += 1
            word = value[index:end]
            # MySQL may expose a character-set introducer immediately before a
            # literal (for example _utf8mb4'PRESENT').
            if not (
                word.startswith("_")
                and word[1:].isalnum()
                and end < len(value)
                and value[end] in "'\""
            ):
                tokens.append(word.casefold())
            index = end
        else:
            pair = value[index:index + 2]
            if pair in {"<=", ">=", "<>", "!="}:
                tokens.append(pair)
                index += 2
            else:
                tokens.append(char)
                index += 1

    return _normalize_expression_grouping(tuple(tokens))


def _normalize_expression_grouping(tokens: tuple[str, ...]) -> tuple[str, ...]:
    """Remove redundant predicate grouping while preserving boolean precedence."""
    normalized: list[str] = []
    index = 0
    while index < len(tokens):
        if tokens[index] != "(":
            normalized.append(tokens[index])
            index += 1
            continue

        depth = 1
        end = index + 1
        while end < len(tokens) and depth:
            if tokens[end] == "(":
                depth += 1
            elif tokens[end] == ")":
                depth -= 1
            end += 1
        if depth:
            normalized.extend(tokens[index:])
            break

        inner = _normalize_expression_grouping(tokens[index + 1:end - 1])
        previous = normalized[-1] if normalized else None
        is_call = previous is not None and previous not in {
            "and", "or", "not", "in", "is", "between", "when", "then", "else"
        } and (
            previous.isidentifier() or previous.replace("$", "").isidentifier()
        )
        has_boolean_connector = _has_top_level_boolean_connector(inner)
        wraps_entire_expression = index == 0 and end == len(tokens)
        if is_call or (has_boolean_connector and not wraps_entire_expression):
            normalized.extend(("(", *inner, ")"))
        else:
            normalized.extend(inner)
        index = end
    return tuple(normalized)


def _has_top_level_boolean_connector(tokens: tuple[str, ...]) -> bool:
    depth = 0
    between_pending = False
    for token in tokens:
        if token == "(":
            depth += 1
        elif token == ")":
            depth -= 1
        elif depth == 0:
            if token == "between":
                between_pending = True
            elif token == "and" and between_pending:
                between_pending = False
            elif token in {"and", "or"}:
                return True
    return False


def _split_items(body: str) -> list[str]:
    items: list[str] = []
    start = depth = 0
    quote: str | None = None
    escaped = False
    for index, char in enumerate(body):
        if quote:
            if char == quote and not escaped:
                quote = None
            escaped = char == "\\" and not escaped
            if char != "\\":
                escaped = False
        elif char in "'\"`":
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        elif char == "," and depth == 0:
            items.append(body[start:index].strip())
            start = index + 1
    items.append(body[start:].strip())
    return [item for item in items if item]


def _parse_columns_and_constraints(body: str, engine: str) -> TableDefinition:
    columns: dict[str, ColumnDefinition] = {}
    pk: tuple[str, ...] = ()
    fks: set[ForeignKeyDefinition] = set()
    uniques: set[UniqueDefinition] = set()
    indexes: set[IndexDefinition] = set()
    checks: set[CheckDefinition] = set()
    for item in _split_items(body):
        stripped = item.strip()
        match = re.match(r"(?is)^CONSTRAINT\s+`?(\w+)`?\s+(.*)$", stripped)
        constraint_name = match.group(1) if match else None
        constraint = match.group(2) if match else stripped
        primary = re.match(r"(?is)^PRIMARY\s+KEY\s*\((.*?)\)$", constraint)
        if primary:
            pk = tuple(re.findall(r"`?(\w+)`?", primary.group(1)))
            continue
        fk = re.match(r"(?is)^FOREIGN\s+KEY\s*\((.*?)\)\s+REFERENCES\s+`?(\w+)`?\s*\((.*?)\)(.*)$", constraint)
        if fk:
            actions = fk.group(4)
            fks.add(ForeignKeyDefinition(
                tuple(re.findall(r"`?(\w+)`?", fk.group(1))), fk.group(2),
                tuple(re.findall(r"`?(\w+)`?", fk.group(3))),
                (re.search(r"(?i)ON\s+DELETE\s+(CASCADE|RESTRICT|SET\s+NULL|NO\s+ACTION)", actions).group(1).upper() if re.search(r"(?i)ON\s+DELETE\s+(CASCADE|RESTRICT|SET\s+NULL|NO\s+ACTION)", actions) else None),
                (re.search(r"(?i)ON\s+UPDATE\s+(CASCADE|RESTRICT|SET\s+NULL|NO\s+ACTION)", actions).group(1).upper() if re.search(r"(?i)ON\s+UPDATE\s+(CASCADE|RESTRICT|SET\s+NULL|NO\s+ACTION)", actions) else None),
                constraint_name,
            ))
            continue
        unique = re.match(r"(?is)^UNIQUE(?:\s+(?:KEY|INDEX))?(?:\s+`?(\w+)`?)?\s*\((.*?)\)$", constraint)
        if unique:
            uniques.add(UniqueDefinition(tuple(re.findall(r"`?(\w+)`?", unique.group(2))), unique.group(1) or constraint_name))
            continue
        index = re.match(r"(?is)^(?:KEY|INDEX)\s+`?(\w+)`?\s*\((.*?)\)$", constraint)
        if index:
            indexes.add(IndexDefinition(tuple(re.findall(r"`?(\w+)`?", index.group(2))), False, index.group(1)))
            continue
        check = re.match(r"(?is)^CHECK\s*\((.*)\)$", constraint)
        if check:
            checks.add(CheckDefinition(constraint_name, _sql_tokens(check.group(1))))
            continue
        col = re.match(r"(?is)^`?(\w+)`?\s+(.+)$", stripped)
        if not col:
            raise ValueError(f"Unsupported schema clause: {stripped[:80]}")
        name, declaration = col.group(1), col.group(2).strip()
        default = re.search(r"(?i)\bDEFAULT\s+((?:CURRENT_TIMESTAMP(?:\(\d+\))?)|(?:'[^']*')|(?:\"[^\"]*\")|(?:TRUE|FALSE)|(?:NULL)|(?:[-+]?\d+(?:\.\d+)?))", declaration)
        type_sql = _normalize_type_sql(re.split(r"\s+(?:NOT\s+NULL|NULL|DEFAULT|AUTO_INCREMENT|GENERATED|AS)\b", declaration, maxsplit=1, flags=re.I)[0])
        if type_sql == "boolean":
            type_sql = "tinyint(1)"
        default_sql = _normalize_sql(default.group(1)) if default else None
        if type_sql == "tinyint(1)" and default_sql == "true":
            default_sql = "1"
        elif type_sql == "tinyint(1)" and default_sql == "false":
            default_sql = "0"
        columns[name] = ColumnDefinition(
            name=name,
            type_sql=type_sql,
            nullable=not bool(re.search(r"(?i)\bNOT\s+NULL\b", declaration)),
            default_sql=default_sql,
            generated=bool(re.search(r"(?i)\bGENERATED\b|\bAS\s*\(", declaration)),
            on_update_sql=(
                _normalize_sql(update.group(1))
                if (update := re.search(r"(?i)\bON\s+UPDATE\s+(CURRENT_TIMESTAMP(?:\(\d+\))?)", declaration))
                else None
            ),
            auto_increment=bool(re.search(r"(?i)\bAUTO_INCREMENT\b", declaration)),
        )
    for name in pk:
        if name in columns:
            columns[name] = ColumnDefinition(
                name, columns[name].type_sql, False, columns[name].default_sql,
                columns[name].generated, columns[name].on_update_sql,
                columns[name].auto_increment,
            )
    return TableDefinition(engine, columns, pk, frozenset(fks), frozenset(uniques), frozenset(indexes), frozenset(checks))


def parse_schema_snapshot(path: Path = _SCHEMA_PATH) -> dict[str, TableDefinition]:
    sql = path.read_text(encoding="utf-8")
    definitions: dict[str, TableDefinition] = {}
    for match in _TABLE_RE.finditer(sql):
        definitions[match.group(1)] = _parse_columns_and_constraints(match.group(2), match.group(3))
    if not definitions:
        raise ValueError("No supported CREATE TABLE definitions found in schema snapshot.")
    return definitions


def _actual_table(inspector, table: str) -> TableDefinition:
    raw_columns = inspector.get_columns(table)
    columns: dict[str, ColumnDefinition] = {}
    for item in raw_columns:
        typ = item["type"]
        type_name = typ.__class__.__name__.upper()
        if type_name in {"BOOLEAN", "BOOL"}:
            type_name = "TINYINT"
            args = ["1"]
        else:
            args = []
        if type_name in {"INTEGER", "INT"}:
            type_name = "INT"
        if getattr(typ, "precision", None) is not None:
            args = [str(typ.precision), str(typ.scale)] if getattr(typ, "scale", None) is not None else [str(typ.precision)]
        elif getattr(typ, "length", None) is not None:
            args = [str(typ.length)]
        elif getattr(typ, "fsp", None) is not None and typ.fsp:
            args = [str(typ.fsp)]
        type_sql = type_name + (f"({','.join(args)})" if args else "")
        if getattr(typ, "unsigned", False):
            type_sql += " unsigned"
        computed = item.get("computed")
        columns[item["name"]] = ColumnDefinition(
            item["name"], _normalize_type_sql(type_sql), bool(item.get("nullable", True)),
            _normalize_sql(str(item.get("default"))) if item.get("default") is not None else None,
            bool(computed),
        )
    pk = tuple((inspector.get_pk_constraint(table).get("constrained_columns") or []))
    fks = set()
    for item in inspector.get_foreign_keys(table):
        options = item.get("options") or {}
        fks.add(ForeignKeyDefinition(tuple(item.get("constrained_columns") or ()), item.get("referred_table") or "", tuple(item.get("referred_columns") or ()), (options.get("ondelete") or "").upper() or None, (options.get("onupdate") or "").upper() or None))
    uniques = {UniqueDefinition(tuple(item.get("column_names") or ()), item.get("name")) for item in inspector.get_unique_constraints(table)}
    indexes = {IndexDefinition(tuple(item.get("column_names") or ()), bool(item.get("unique")), item.get("name")) for item in inspector.get_indexes(table)}
    checks = {
        CheckDefinition(item.get("name"), _sql_tokens(item.get("sqltext") or ""))
        for item in inspector.get_check_constraints(table)
    }
    engine_name = (inspector.get_table_options(table).get("mysql_engine") or "").casefold()
    return TableDefinition(engine_name, columns, pk, frozenset(fks), frozenset(uniques), frozenset(indexes), frozenset(checks))


def _schema_differences(expected: TableDefinition, actual: TableDefinition, table: str = "table") -> list[str]:
    errors: list[str] = []
    if expected.engine.casefold() != actual.engine.casefold():
        errors.append(f"{table}.engine mismatch: expected {expected.engine!r}; actual {actual.engine!r}")
    if expected.primary_key != actual.primary_key:
        errors.append(f"{table}.primary_key mismatch: expected {expected.primary_key!r}; actual {actual.primary_key!r}")
    if set(expected.columns) != set(actual.columns):
        errors.append(f"{table}.columns mismatch: expected {sorted(expected.columns)!r}; actual {sorted(actual.columns)!r}")
    for name in set(expected.columns) & set(actual.columns):
        expected_column, actual_column = expected.columns[name], actual.columns[name]
        for attribute in ("type_sql", "nullable", "default_sql", "generated", "on_update_sql", "auto_increment"):
            expected_value = getattr(expected_column, attribute)
            actual_value = getattr(actual_column, attribute)
            if (
                attribute == "default_sql"
                and expected_column.nullable
                and actual_column.nullable
                and {expected_value, actual_value} == {None, "null"}
            ):
                continue
            if (
                attribute == "default_sql"
                and _numeric_defaults_equivalent(expected_column, actual_column)
            ):
                continue
            if expected_value != actual_value:
                errors.append(
                    f"{table}.{name}.{attribute} mismatch: expected {expected_value!r}; actual {actual_value!r}"
                )
    if expected.foreign_keys != actual.foreign_keys:
        for foreign_key in sorted(expected.foreign_keys - actual.foreign_keys, key=repr):
            errors.append(f"{table}.foreign_key expected but absent: {foreign_key!r}")
        for foreign_key in sorted(actual.foreign_keys - expected.foreign_keys, key=repr):
            errors.append(f"{table}.foreign_key unexpected: {foreign_key!r}")
    if expected.unique_constraints != actual.unique_constraints:
        errors.append(
            f"{table}.unique_constraints mismatch: expected {sorted(expected.unique_constraints, key=repr)!r}; "
            f"actual {sorted(actual.unique_constraints, key=repr)!r}"
        )
    # MySQL may expose a unique key as both a constraint and an index.
    expected_ix = expected.indexes | {IndexDefinition(unique.columns, True, unique.name) for unique in expected.unique_constraints}
    for foreign_key in expected.foreign_keys:
        columns = foreign_key.columns
        if not any(
            existing[: len(columns)] == columns
            for existing in [expected.primary_key, *(unique.columns for unique in expected.unique_constraints), *(ix.columns for ix in expected.indexes)]
        ):
            expected_ix |= {IndexDefinition(columns, False)}
    actual_ix = actual.indexes | {IndexDefinition(unique.columns, True, unique.name) for unique in actual.unique_constraints}
    if expected_ix != actual_ix:
        errors.append(
            f"{table}.indexes mismatch: expected {sorted(expected_ix, key=repr)!r}; "
            f"actual {sorted(actual_ix, key=repr)!r}"
        )
    expected_checks = {check.expression for check in expected.checks}
    actual_checks = {check.expression for check in actual.checks}
    if expected_checks != actual_checks:
        for check in sorted(expected.checks, key=repr):
            if check.expression not in actual_checks:
                errors.append(
                    f"{table}.check {check.name or '<unnamed>'!r} expected expression "
                    f"{check.expression!r}; no equivalent actual expression"
                )
        for check in sorted(actual.checks, key=repr):
            if check.expression not in expected_checks:
                errors.append(
                    f"{table}.check {check.name or '<unnamed>'!r} unexpected expression "
                    f"{check.expression!r}"
                )
    return errors


def _schema_difference_error(differences: list[str]) -> SchemaVerificationError:
    """Keep every field-level mismatch in the exception surfaced by pytest."""
    return SchemaVerificationError(
        "MySQL schema definition mismatch: " + "; ".join(differences)
    )


def _verify_schema_state(connection, prepared_schema: Path) -> None:
    expected = parse_schema_snapshot(prepared_schema)
    inspector = inspect(connection)
    actual_tables = set(inspector.get_table_names())
    if "alembic_version" in actual_tables:
        raise SchemaVerificationError("Alembic-managed tables are not allowed in the snapshot test database.")
    if actual_tables != set(expected):
        raise SchemaVerificationError(f"MySQL table set mismatch: expected {sorted(expected)!r}; actual {sorted(actual_tables)!r}")
    if not _REQUIRED_PATH_TABLES.issubset(actual_tables):
        raise SchemaVerificationError(
            "Prepared snapshot is missing a required integration-path table."
        )
    actual_definitions: dict[str, TableDefinition] = {}
    for table in sorted(expected):
        row = connection.execute(text(f"SHOW CREATE TABLE `{table}`")).one()
        matches = list(_TABLE_RE.finditer(row[1]))
        if len(matches) != 1 or matches[0].group(1) != table:
            raise SchemaVerificationError(f"Could not parse MySQL SHOW CREATE TABLE output for {table!r}.")
        try:
            actual_definitions[table] = _parse_columns_and_constraints(
                matches[0].group(2), matches[0].group(3)
            )
        except ValueError as exc:
            raise SchemaVerificationError(
                f"Could not parse MySQL SHOW CREATE TABLE definition for {table!r}: {exc}"
            ) from exc
    differences = [message for table in sorted(expected) for message in _schema_differences(expected[table], actual_definitions[table], table)]
    if differences:
        raise _schema_difference_error(differences)
    for table in expected:
        if connection.execute(text(f"SELECT 1 FROM `{table}` LIMIT 1")).first() is not None:
            raise SchemaVerificationError(f"Test table {table!r} is not empty before seeding.")
