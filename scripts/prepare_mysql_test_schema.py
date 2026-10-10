"""Prepare an isolated copy of the current MySQL schema snapshot.

This utility only writes a temporary SQL file. It never connects to MySQL or
executes SQL.
"""

from __future__ import annotations

import argparse
import os
import re
import tempfile
from pathlib import Path


_DEFAULT_SCHEMA = Path(__file__).resolve().parents[1] / "database" / "schema.sql"
_TEST_DATABASE_NAME = re.compile(
    r"\Aepms_(?:[a-z0-9]+_)*test(?:_[a-z0-9]+)*\Z"
)
_CREATE_DATABASE_DIRECTIVE = re.compile(
    rb"(?m)^(CREATE DATABASE IF NOT EXISTS )employee_payroll_db"
    rb"(\r?\n[ \t]+CHARACTER SET utf8mb4"
    rb"\r?\n[ \t]+COLLATE utf8mb4_unicode_ci;[ \t]*\r?$)"
)
_USE_DATABASE_DIRECTIVE = re.compile(
    rb"(?m)^(USE )employee_payroll_db(;[ \t]*\r?$)"
)
_DATABASE_DIRECTIVE = re.compile(
    rb"(?im)^[ \t]*(?:CREATE[ \t]+(?:DATABASE|SCHEMA)\b|USE\b)"
)


class SchemaPreparationError(ValueError):
    """Raised when the schema cannot be safely adapted to a test database."""


def prepare_schema_snapshot(
    database_name: str | None,
    *,
    schema_path: Path = _DEFAULT_SCHEMA,
    output_directory: Path | None = None,
) -> Path:
    """Create a temporary schema copy targeting an explicitly named test DB."""

    validate_test_database_name(database_name)

    source_path = Path(schema_path).resolve(strict=True)
    project_root = (
        source_path.parent.parent
        if source_path.parent.name.casefold() == "database"
        else source_path.parent
    )
    destination_directory = (
        Path(output_directory).resolve(strict=True)
        if output_directory is not None
        else Path(tempfile.gettempdir()).resolve(strict=True)
    )
    if destination_directory == project_root or project_root in destination_directory.parents:
        raise SchemaPreparationError(
            "Temporary schema output must be outside the project directory."
        )
    if not destination_directory.is_dir():
        raise SchemaPreparationError("Temporary schema output must be a directory.")

    try:
        schema_bytes = source_path.read_bytes()
    except OSError as exc:
        raise SchemaPreparationError(f"Could not read schema file: {source_path}") from exc

    create_matches = list(_CREATE_DATABASE_DIRECTIVE.finditer(schema_bytes))
    use_matches = list(_USE_DATABASE_DIRECTIVE.finditer(schema_bytes))
    directives = list(_DATABASE_DIRECTIVE.finditer(schema_bytes))
    if (
        len(create_matches) != 1
        or len(use_matches) != 1
        or len(directives) != 2
        or create_matches[0].start() > use_matches[0].start()
    ):
        raise SchemaPreparationError(
            "Expected exactly one supported CREATE DATABASE directive followed "
            "by exactly one matching USE directive; refusing ambiguous schema."
        )

    target = database_name.encode("ascii")
    adapted = _CREATE_DATABASE_DIRECTIVE.sub(
        lambda match: match.group(1) + target + match.group(2),
        schema_bytes,
        count=1,
    )
    adapted = _USE_DATABASE_DIRECTIVE.sub(
        lambda match: match.group(1) + target + match.group(2),
        adapted,
        count=1,
    )
    if adapted == schema_bytes:
        raise SchemaPreparationError("Schema adaptation made no changes.")

    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix="epms-mysql-test-schema-",
        suffix=".sql",
        dir=destination_directory,
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(file_descriptor, "wb") as temporary_file:
            temporary_file.write(adapted)
    except OSError:
        temporary_path.unlink(missing_ok=True)
        raise
    return temporary_path


def validate_test_database_name(database_name: str | None) -> str:
    """Return a schema-safe disposable database name or reject it."""

    if not isinstance(database_name, str) or not _TEST_DATABASE_NAME.fullmatch(
        database_name
    ):
        raise SchemaPreparationError(
            "Database name must start with 'epms_', contain a 'test' segment, "
            "and use lowercase letters, digits, and underscores only."
        )
    if len(database_name) > 64:
        raise SchemaPreparationError("Database name must not exceed 64 characters.")
    if database_name == "employee_payroll_db":
        raise SchemaPreparationError("The development database is not a test database.")
    return database_name


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database-name",
        required=True,
        help="Explicit isolated test database name (for example epms_runtime_test).",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=_DEFAULT_SCHEMA,
        help="Source schema snapshot (defaults to database/schema.sql).",
    )
    args = parser.parse_args()

    try:
        prepared_path = prepare_schema_snapshot(
            args.database_name,
            schema_path=args.schema,
        )
    except (OSError, SchemaPreparationError) as exc:
        parser.error(str(exc))
    print(prepared_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
