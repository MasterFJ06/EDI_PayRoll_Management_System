"""Provision synthetic browser-smoke fixtures in the disposable EPMS database.

This script is intentionally test-only. It has no role-assignment HTTP endpoint;
it uses persisted ORM records only after validating the exact GitHub Actions test
database and confirming that the imported snapshot contains no application data.
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import urllib.error
import urllib.request
from datetime import date, timedelta
from pathlib import Path
from uuid import uuid4

from sqlalchemy import inspect, select, text

from app.core.config import get_settings


_EXPECTED_DATABASE = "epms_frontend_smoke_test"
_EXPECTED_API = "http://127.0.0.1:8000/api/v1"
_CATALOG_TABLES = {"roles", "permissions", "role_permissions"}
_ROOT = Path(__file__).resolve().parents[1]


def _validate_target() -> None:
    settings = get_settings()
    if os.environ.get("EPMS_FRONTEND_SMOKE_TEST") != "1":
        raise RuntimeError("Frontend smoke setup is not explicitly enabled.")
    if settings.app_env.casefold() != "test":
        raise RuntimeError("Smoke setup requires APP_ENV=test.")
    if (
        settings.database_name != _EXPECTED_DATABASE
        or settings.database_host not in {"127.0.0.1", "localhost"}
        or settings.database_port != 3306
        or settings.database_user != "epms_ci"
        or not settings.database_password
    ):
        raise RuntimeError("Database settings do not match the dedicated smoke target.")
    if os.environ.get("EPMS_SMOKE_API_BASE_URL") != _EXPECTED_API:
        raise RuntimeError("Smoke setup requires the explicit local test API URL.")


def _db_counts(engine) -> dict[str, int]:
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    expected = {
        "users", "roles", "permissions", "user_roles", "role_permissions",
        "departments", "designations", "employees", "leave_types",
        "work_calendar_versions", "work_calendar_weekly_rules",
    }
    if not expected.issubset(tables):
        raise RuntimeError("The prepared schema is missing required smoke-test tables.")
    preparer = engine.dialect.identifier_preparer
    with engine.connect() as connection:
        actual_database = connection.scalar(text("SELECT DATABASE()"))
        version = connection.scalar(text("SELECT VERSION()"))
        if actual_database != _EXPECTED_DATABASE or not str(version).startswith("8."):
            raise RuntimeError("Connected database is not the expected disposable MySQL 8 target.")
        return {
            table: int(connection.scalar(text(f"SELECT COUNT(*) FROM {preparer.quote(table)}")) or 0)
            for table in tables
        }


def _assert_empty_snapshot(engine) -> None:
    counts = _db_counts(engine)
    populated = [table for table, count in counts.items() if count]
    if populated:
        raise RuntimeError(
            "Refusing smoke setup because imported snapshot tables are not empty: "
            + ", ".join(sorted(populated))
        )


def _assert_seeded_catalog(engine) -> None:
    from app.infrastructure.persistence.models.permission import Permission
    from app.infrastructure.persistence.models.role import Role
    from app.infrastructure.persistence.models.role_permission import RolePermission

    counts = _db_counts(engine)
    populated = [
        table for table, count in counts.items()
        if count and table not in _CATALOG_TABLES
    ]
    if populated:
        raise RuntimeError(
            "Refusing smoke setup because non-catalog tables already contain rows: "
            + ", ".join(sorted(populated))
        )

    with engine.connect() as connection:
        role_names = set(connection.scalars(select(Role.role_name).where(
            Role.role_name.in_(["HR Administrator", "Payroll Administrator"])
        )))
        if role_names != {"HR Administrator", "Payroll Administrator"}:
            raise RuntimeError("RBAC seed is missing an expected administrator role.")

    expected_grants = {
        "HR Administrator": {
            "report.employee.read",
            "report.attendance.read",
            "report.leave.read",
            "workforce.leave.request.create_for_others",
            "workforce.leave.balance.manage_for_others",
        },
        "Payroll Administrator": {
            "compensation.write",
            "payroll.run.create",
            "payroll.run.read",
            "payroll.run.process",
            "payroll.run.retry",
            "payroll.run.recover",
            "payroll.run.finalize",
            "payroll.payslip.create",
            "report.payroll.read",
        },
    }
    with engine.connect() as connection:
        for role_name, codes in expected_grants.items():
            actual = set(connection.scalars(
                select(Permission.permission_code)
                .join(RolePermission, RolePermission.permission_id == Permission.permission_id)
                .join(Role, Role.role_id == RolePermission.role_id)
                .where(Role.role_name == role_name)
            ))
            if actual != codes:
                raise RuntimeError(
                    f"RBAC seed grants for {role_name} do not match the approved catalog."
                )


def _request(path: str, payload: dict, token: str | None = None) -> dict:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        _EXPECTED_API + path,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            if response.status not in {200, 201}:
                raise RuntimeError(f"Smoke setup API request failed with HTTP {response.status}.")
            return json.loads(response.read())
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Smoke setup API request {path} failed with HTTP {exc.code}.") from None
    except urllib.error.URLError:
        raise RuntimeError(f"Smoke setup API request {path} could not reach the API.") from None


def _register(username: str) -> dict[str, str | int]:
    password = secrets.token_urlsafe(24)
    result = _request("/auth/register", {
        "username": username,
        "email": f"{username}@example.com",
        "password": password,
    })
    return {"user_id": result["user_id"], "username": username, "password": password}


def _login(user: dict[str, str | int]) -> str:
    result = _request("/auth/login", {
        "username": user["username"],
        "password": user["password"],
    })
    return str(result["access_token"])


def _next_weekdays(start: date, count: int) -> list[date]:
    found: list[date] = []
    candidate = start + timedelta(days=1)
    while len(found) < count:
        if candidate.isoweekday() <= 5:
            found.append(candidate)
        candidate += timedelta(days=1)
    return found


def _provision(fixture_file: Path) -> None:
    _validate_target()
    from app.infrastructure.database.engine import engine
    from app.infrastructure.database.session import SessionLocal
    from app.infrastructure.persistence.models.leave_type import LeaveTypeModel
    from app.infrastructure.persistence.models.role import Role
    from app.infrastructure.persistence.models.user_role import UserRole
    from app.infrastructure.persistence.models.work_calendar_version import WorkCalendarVersionModel
    from app.infrastructure.persistence.models.work_calendar_weekly_rule import WorkCalendarWeeklyRuleModel

    _assert_seeded_catalog(engine)
    run_suffix = f"{os.environ.get('GITHUB_RUN_ID', 'local')}-{os.environ.get('GITHUB_RUN_ATTEMPT', '1')}-{uuid4().hex[:8]}"
    users = {
        key: _register(f"epms-smoke-{key}-{run_suffix}")
        for key in ("setup", "hr", "payroll", "employee")
    }
    setup_token = _login(users["setup"])
    department = _request("/departments", {
        "department_code": f"SMK-{uuid4().hex[:8]}",
        "department_name": f"Smoke Department {uuid4().hex[:8]}",
    }, setup_token)
    designation = _request("/designations", {
        "designation_code": f"SMK-{uuid4().hex[:8]}",
        "designation_name": f"Smoke Designation {uuid4().hex[:8]}",
    }, setup_token)
    employee = _request("/employees", {
        "employee_code": f"SMK-{uuid4().hex[:12]}",
        "user_id": users["employee"]["user_id"],
        "first_name": "Synthetic",
        "last_name": "Employee",
        "department_id": department["department_id"],
        "designation_id": designation["designation_id"],
        "joining_date": date.today().isoformat(),
    }, setup_token)
    other_employee = _request("/employees", {
        "employee_code": f"SMK-{uuid4().hex[:12]}",
        "first_name": "Synthetic",
        "last_name": "Colleague",
        "department_id": department["department_id"],
        "designation_id": designation["designation_id"],
        "joining_date": date.today().isoformat(),
    }, setup_token)

    work_dates = _next_weekdays(date.today(), 4)
    with SessionLocal() as session:
        roles = {
            role.role_name: role
            for role in session.scalars(select(Role).where(
                Role.role_name.in_(["HR Administrator", "Payroll Administrator"])
            ))
        }
        if len(roles) != 2:
            raise RuntimeError("RBAC seed is missing an expected administrator role.")
        session.add_all([
            UserRole(
                user_id=int(users["hr"]["user_id"]),
                role_id=roles["HR Administrator"].role_id,
                assigned_by_user_id=int(users["setup"]["user_id"]),
            ),
            UserRole(
                user_id=int(users["payroll"]["user_id"]),
                role_id=roles["Payroll Administrator"].role_id,
                assigned_by_user_id=int(users["setup"]["user_id"]),
            ),
        ])
        leave_type = LeaveTypeModel(
            leave_type_code=f"SMK-{uuid4().hex[:8]}",
            leave_type_name=f"Smoke Leave {uuid4().hex[:8]}",
            description="Ephemeral browser smoke reference data.",
            payroll_treatment="PAID",
            is_active=True,
        )
        session.add(leave_type)
        calendar = WorkCalendarVersionModel(
            version_number=1,
            effective_from=date.today() - timedelta(days=1),
            effective_to=None,
            time_zone="UTC",
            created_by_user_id=int(users["setup"]["user_id"]),
            replaces_version_id=None,
        )
        session.add(calendar)
        session.flush()
        session.add_all([
            WorkCalendarWeeklyRuleModel(
                work_calendar_version_id=calendar.work_calendar_version_id,
                iso_weekday=weekday,
                classification="WORKING_DAY" if weekday <= 5 else "NON_WORKING_DAY",
                scheduled_minutes=480 if weekday <= 5 else 0,
            )
            for weekday in range(1, 8)
        ])
        session.commit()
        fixture = {
            "api_base_url": _EXPECTED_API,
            "users": users,
            "department_id": department["department_id"],
            "designation_id": designation["designation_id"],
            "employee_id": employee["employee_id"],
            "other_employee_id": other_employee["employee_id"],
            "leave_type_id": leave_type.leave_type_id,
            "leave_dates": [day.isoformat() for day in work_dates],
        }

    resolved = fixture_file.resolve()
    if _ROOT == resolved or _ROOT in resolved.parents:
        raise RuntimeError("Fixture credentials must be written outside the checkout.")
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(json.dumps(fixture), encoding="utf-8")
    try:
        resolved.chmod(0o600)
    except OSError:
        pass
    print("Provisioned synthetic smoke fixtures in the verified disposable database.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assert-empty", action="store_true")
    parser.add_argument("--provision", action="store_true")
    parser.add_argument("--fixture-file", type=Path)
    args = parser.parse_args()
    if args.assert_empty == args.provision:
        parser.error("Choose exactly one of --assert-empty or --provision.")
    _validate_target()
    if args.assert_empty:
        from app.infrastructure.database.engine import engine
        _assert_empty_snapshot(engine)
        print("Verified the imported disposable smoke database is empty.")
        return 0
    if args.fixture_file is None:
        parser.error("--fixture-file is required with --provision.")
    _provision(args.fixture_file)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
