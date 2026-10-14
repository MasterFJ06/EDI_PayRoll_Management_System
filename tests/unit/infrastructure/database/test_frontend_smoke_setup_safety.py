from types import SimpleNamespace

import pytest

from scripts import frontend_smoke_setup


def _configure_target(monkeypatch, **overrides):
    values = {
        "app_env": "test",
        "database_name": "epms_frontend_smoke_test",
        "database_host": "127.0.0.1",
        "database_port": 3306,
        "database_user": "epms_ci",
        "database_password": "ephemeral-only",
    }
    values.update(overrides)
    monkeypatch.setattr(
        frontend_smoke_setup, "get_settings", lambda: SimpleNamespace(**values)
    )
    monkeypatch.setenv("EPMS_FRONTEND_SMOKE_TEST", "1")
    monkeypatch.setenv("EPMS_SMOKE_API_BASE_URL", frontend_smoke_setup._EXPECTED_API)


def test_smoke_setup_requires_explicit_test_gate(monkeypatch):
    _configure_target(monkeypatch)
    monkeypatch.delenv("EPMS_FRONTEND_SMOKE_TEST")

    with pytest.raises(RuntimeError, match="not explicitly enabled"):
        frontend_smoke_setup._validate_target()


@pytest.mark.parametrize(
    "override",
    [
        {"app_env": "development"},
        {"database_name": "employee_payroll_db"},
        {"database_name": "epms_other_test"},
        {"database_host": "db.example.invalid"},
        {"database_port": 3307},
        {"database_user": "developer"},
        {"database_password": ""},
    ],
)
def test_smoke_setup_rejects_non_workflow_targets(monkeypatch, override):
    _configure_target(monkeypatch, **override)

    with pytest.raises(RuntimeError):
        frontend_smoke_setup._validate_target()


def test_smoke_setup_accepts_only_explicit_disposable_workflow_target(monkeypatch):
    _configure_target(monkeypatch)

    frontend_smoke_setup._validate_target()


def test_smoke_setup_rejects_an_unexpected_api_origin(monkeypatch):
    _configure_target(monkeypatch)
    monkeypatch.setenv("EPMS_SMOKE_API_BASE_URL", "http://127.0.0.1:8000")

    with pytest.raises(RuntimeError, match="explicit local test API URL"):
        frontend_smoke_setup._validate_target()
