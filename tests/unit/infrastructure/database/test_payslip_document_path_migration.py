from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import Mock

from app.infrastructure.persistence.models.payslip import PayslipModel


def _load_migration():
    path = (
        Path(__file__).resolve().parents[4]
        / "migrations"
        / "versions"
        / "20261010_01_nullable_payslip_document_path.py"
    )
    spec = importlib.util.spec_from_file_location("payslip_path_migration", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_schema_snapshot_model_and_migration_agree_on_nullable_path(
    monkeypatch,
) -> None:
    repository_root = Path(__file__).resolve().parents[4]
    schema = (repository_root / "database" / "schema.sql").read_text()
    payslip_ddl = schema.split("CREATE TABLE payslips (", 1)[1].split(") ENGINE", 1)[0]
    assert "document_path VARCHAR(500) NULL" in payslip_ddl
    assert PayslipModel.__table__.c.document_path.nullable is True

    migration = _load_migration()
    alter_column = Mock()
    monkeypatch.setattr(migration.op, "alter_column", alter_column)
    migration.upgrade()
    assert alter_column.call_count == 1
    args, kwargs = alter_column.call_args
    assert args == ("payslips", "document_path")
    assert kwargs["existing_nullable"] is False
    assert kwargs["nullable"] is True
    assert str(kwargs["existing_type"]) == "VARCHAR(500)"
    assert migration.down_revision == "20261007_02"
