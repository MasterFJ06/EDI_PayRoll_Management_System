from __future__ import annotations

from pathlib import Path
import tempfile

import pytest

from scripts.prepare_mysql_test_schema import (
    SchemaPreparationError,
    prepare_schema_snapshot,
)


def _project_schema(tmp_path: Path, schema_bytes: bytes) -> Path:
    schema_path = tmp_path / "project" / "database" / "schema.sql"
    schema_path.parent.mkdir(parents=True)
    schema_path.write_bytes(schema_bytes)
    return schema_path


def _output_directory(tmp_path: Path) -> Path:
    output_directory = tmp_path / "temporary"
    output_directory.mkdir()
    return output_directory


def test_rewrites_only_database_directives_and_preserves_source(tmp_path: Path) -> None:
    original = (
        b"-- schema comment\r\n"
        b"CREATE DATABASE IF NOT EXISTS employee_payroll_db\r\n"
        b"    CHARACTER SET utf8mb4\r\n"
        b"    COLLATE utf8mb4_unicode_ci;\r\n"
        b"\r\nUSE employee_payroll_db;\r\n"
        b"CREATE TABLE payroll_runs (id BIGINT) ENGINE = InnoDB;\r\n"
    )
    schema_path = _project_schema(tmp_path, original)

    prepared_path = prepare_schema_snapshot(
        "epms_runtime_test",
        schema_path=schema_path,
        output_directory=_output_directory(tmp_path),
    )

    expected = original.replace(b"employee_payroll_db", b"epms_runtime_test")
    assert prepared_path.read_bytes() == expected
    assert schema_path.read_bytes() == original
    assert prepared_path.parent == tmp_path / "temporary"


def test_prepares_actual_schema_snapshot_without_changing_it(tmp_path: Path) -> None:
    tracked_schema = Path(__file__).resolve().parents[4] / "database" / "schema.sql"
    original = tracked_schema.read_bytes()
    schema_path = _project_schema(tmp_path, original)
    output_directory = _output_directory(tmp_path)

    prepared_path = prepare_schema_snapshot(
        "epms_runtime_test",
        schema_path=schema_path,
        output_directory=output_directory,
    )

    assert prepared_path.read_bytes() == original.replace(
        b"employee_payroll_db", b"epms_runtime_test"
    )
    assert tracked_schema.read_bytes() == original
    assert prepared_path.parent == output_directory


def test_default_output_uses_system_temp_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = (
        Path(__file__).resolve().parents[4] / "database" / "schema.sql"
    ).read_bytes()
    schema_path = _project_schema(tmp_path, original)
    output_directory = _output_directory(tmp_path)
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(output_directory))

    prepared_path = prepare_schema_snapshot(
        "epms_runtime_test",
        schema_path=schema_path,
    )

    assert prepared_path.parent == output_directory
    assert prepared_path.read_bytes() == original.replace(
        b"employee_payroll_db", b"epms_runtime_test"
    )


@pytest.mark.parametrize(
    "database_name",
    [
        None,
        "employee_payroll_db",
        "epms_dev",
        "epms_runtime_test; DROP DATABASE other",
        "EPMS_runtime_test",
        "epms_test_" + "x" * 60,
        "",
    ],
)
def test_rejects_missing_or_invalid_test_database_name(
    tmp_path: Path, database_name: str
) -> None:
    schema_path = _project_schema(
        tmp_path,
        b"CREATE DATABASE IF NOT EXISTS employee_payroll_db\n"
        b"    CHARACTER SET utf8mb4\n"
        b"    COLLATE utf8mb4_unicode_ci;\n"
        b"USE employee_payroll_db;\n",
    )

    with pytest.raises(SchemaPreparationError):
        prepare_schema_snapshot(
            database_name,
            schema_path=schema_path,
            output_directory=_output_directory(tmp_path),
        )


@pytest.mark.parametrize(
    "directives",
    [
        b"USE employee_payroll_db;\n",
        b"CREATE DATABASE IF NOT EXISTS employee_payroll_db\n"
        b"    CHARACTER SET utf8mb4\n"
        b"    COLLATE utf8mb4_unicode_ci;\n",
        b"CREATE DATABASE IF NOT EXISTS employee_payroll_db\n"
        b"    CHARACTER SET utf8mb4\n"
        b"    COLLATE utf8mb4_unicode_ci;\n"
        b"USE employee_payroll_db;\n"
        b"USE other_database;\n",
        b"CREATE DATABASE other_database;\n"
        b"CREATE DATABASE IF NOT EXISTS employee_payroll_db\n"
        b"    CHARACTER SET utf8mb4\n"
        b"    COLLATE utf8mb4_unicode_ci;\n"
        b"USE employee_payroll_db;\n",
        b"CREATE DATABASE IF NOT EXISTS another_database\n"
        b"    CHARACTER SET utf8mb4\n"
        b"    COLLATE utf8mb4_unicode_ci;\n"
        b"USE employee_payroll_db;\n",
    ],
)
def test_rejects_unexpected_or_ambiguous_database_directives(
    tmp_path: Path, directives: bytes
) -> None:
    schema_path = _project_schema(tmp_path, directives)

    with pytest.raises(SchemaPreparationError):
        prepare_schema_snapshot(
            "epms_runtime_test",
            schema_path=schema_path,
            output_directory=_output_directory(tmp_path),
        )


def test_rejects_output_directory_inside_project(tmp_path: Path) -> None:
    schema_path = _project_schema(
        tmp_path,
        b"CREATE DATABASE IF NOT EXISTS employee_payroll_db\n"
        b"    CHARACTER SET utf8mb4\n"
        b"    COLLATE utf8mb4_unicode_ci;\n"
        b"USE employee_payroll_db;\n",
    )

    with pytest.raises(SchemaPreparationError, match="outside the project"):
        prepare_schema_snapshot(
            "epms_runtime_test",
            schema_path=schema_path,
            output_directory=schema_path.parents[1],
        )
