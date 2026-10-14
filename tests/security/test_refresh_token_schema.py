from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy.dialects import mysql

from app.infrastructure.persistence.models.refresh_token import RefreshToken


ROOT = Path(__file__).resolve().parents[2]


def test_refresh_token_model_has_hash_family_and_fk_contract() -> None:
    table = RefreshToken.__table__
    compiler = mysql.dialect().type_compiler
    assert set(table.columns.keys()) == {
        "token_id", "user_id", "family_id", "token_hash", "expires_at",
        "revoked_at", "created_at",
    }
    assert compiler.process(table.c.token_id.type) == "BIGINT UNSIGNED"
    assert table.c.family_id.nullable is False
    assert table.c.token_hash.type.length == 64
    assert compiler.process(table.c.user_id.type) == "BIGINT UNSIGNED"
    assert compiler.process(table.c.token_hash.type) == "CHAR(64)"
    assert compiler.process(table.c.expires_at.type) == "DATETIME(6)"
    assert compiler.process(table.c.created_at.type) == "DATETIME(6)"
    assert table.c.expires_at.nullable is False
    assert table.c.revoked_at.nullable is True
    assert {(fk.target_fullname, fk.ondelete, fk.onupdate) for fk in table.c.user_id.foreign_keys} == {
        ("users.user_id", "RESTRICT", "RESTRICT")
    }
    family_index = next(
        index for index in table.indexes if index.name == "idx_refresh_tokens_family"
    )
    assert list(family_index.columns.keys()) == ["family_id", "token_id"]


def test_schema_snapshot_and_forward_migration_define_refresh_token_table() -> None:
    schema = (ROOT / "database" / "schema.sql").read_text(encoding="utf-8")
    assert "CREATE TABLE refresh_tokens" in schema
    assert "token_hash CHAR(64) NOT NULL" in schema
    assert "family_id VARCHAR(36) NOT NULL" in schema

    config = Config(str(ROOT / "alembic.ini"))
    scripts = ScriptDirectory.from_config(config)
    assert scripts.get_current_head() == "20261013_01"
    revision = scripts.get_revision("20261013_01")
    assert revision is not None and revision.down_revision == "20261010_01"
    migration = (ROOT / "migrations" / "versions" / "20261013_01_refresh_token_lifecycle.py").read_text(
        encoding="utf-8"
    )
    assert 'op.create_table(\n        "refresh_tokens"' in migration
    assert 'op.drop_table("refresh_tokens")' in migration
    assert "invalidates all refresh sessions" in migration
