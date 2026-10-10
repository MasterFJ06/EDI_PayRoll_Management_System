from datetime import date
from unittest.mock import Mock

from fastapi.testclient import TestClient

from app.api.dependencies.current_user import get_current_user
from app.api.dependencies.unit_of_work import get_unit_of_work
from app.domain.organization.work_calendar import (
    CalendarDateOverride,
    WeeklyRule,
    WorkCalendarVersion,
)
from app.infrastructure.persistence.models.user import User
from app.main import app


class CalendarRepository:
    def __init__(self) -> None:
        self.overlap = False
        self.version = WorkCalendarVersion(
            1,
            date(2026, 1, 1),
            date(2026, 12, 31),
            "UTC",
            7,
            tuple(
                WeeklyRule(day, "WORKING_DAY" if day <= 5 else "NON_WORKING_DAY", 480 if day <= 5 else 0)
                for day in range(1, 8)
            ),
            version_id=21,
        )
        self.overrides: list[CalendarDateOverride] = []

    def has_effective_date_overlap(self, effective_from, effective_to):
        return self.overlap

    def add_version(self, version):
        return WorkCalendarVersion(
            version.version_number,
            version.effective_from,
            version.effective_to,
            version.time_zone,
            version.created_by_user_id,
            version.weekly_rules,
            version_id=21,
            replaces_version_id=version.replaces_version_id,
        )

    def get_by_id(self, version_id: int):
        return self.version if version_id == 21 else None

    def get_overrides(self, version_id: int):
        return self.overrides

    def get_override(self, version_id: int, override_date: date):
        return next((item for item in self.overrides if item.override_date == override_date), None)

    def add_override(self, override):
        created = CalendarDateOverride(
            override.work_calendar_version_id,
            override.override_date,
            override.classification,
            override.label,
            override_id=31,
        )
        self.overrides.append(created)
        return created


def authorized_client(
    permission: bool = True, payroll_statuses: list[str] | None = None,
    overlap: bool = False,
) -> TestClient:
    user = Mock(spec=User)
    user.user_id = 7
    uow = Mock()
    uow.authorization.has_permission.return_value = permission
    uow.payroll_runs.get_statuses_overlapping_dates.return_value = payroll_statuses or []
    uow.audit_events.add.return_value = None
    uow.work_calendars = CalendarRepository()
    uow.work_calendars.overlap = overlap
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_unit_of_work] = lambda: uow
    return TestClient(app)


def teardown_function() -> None:
    app.dependency_overrides.clear()


def test_get_work_calendar_version_returns_dto_with_weekly_rules() -> None:
    with authorized_client() as client:
        response = client.get("/api/v1/work-calendar-versions/21")
    assert response.status_code == 200
    assert response.json()["created_by_user_id"] == 7
    assert len(response.json()["weekly_rules"]) == 7
    assert response.json()["date_overrides"] == []


def test_get_work_calendar_version_not_found() -> None:
    with authorized_client() as client:
        response = client.get("/api/v1/work-calendar-versions/22")
    assert response.status_code == 404


def test_calendar_endpoints_enforce_permission() -> None:
    with authorized_client(permission=False) as client:
        response = client.get("/api/v1/work-calendar-versions/21")
    assert response.status_code == 403


def test_calendar_endpoint_requires_authentication() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/work-calendar-versions/21")
    assert response.status_code == 401


def test_create_request_rejects_missing_or_invalid_weekly_rule() -> None:
    with authorized_client() as client:
        response = client.post(
            "/api/v1/work-calendar-versions",
            json={
                "version_number": 1,
                "effective_from": "2026-01-01",
                "effective_to": "2026-12-31",
                "time_zone": "UTC",
                "weekly_rules": [],
            },
        )
    assert response.status_code == 422


def test_create_work_calendar_version_succeeds_and_uses_authenticated_actor() -> None:
    with authorized_client() as client:
        response = client.post(
            "/api/v1/work-calendar-versions",
            json={
                "version_number": 1,
                "effective_from": "2026-01-01",
                "effective_to": "2026-12-31",
                "time_zone": "UTC",
                "weekly_rules": [
                    {
                        "iso_weekday": day,
                        "classification": "WORKING_DAY" if day <= 5 else "NON_WORKING_DAY",
                        "scheduled_minutes": 480 if day <= 5 else 0,
                    }
                    for day in range(1, 8)
                ],
            },
        )
    assert response.status_code == 201
    assert response.json()["created_by_user_id"] == 7
    assert response.json()["work_calendar_version_id"] == 21


def test_create_date_override_succeeds() -> None:
    with authorized_client() as client:
        response = client.post(
            "/api/v1/work-calendar-versions/21/date-overrides",
            json={
                "override_date": "2026-02-02",
                "classification": "HOLIDAY",
                "label": "Founders Day",
            },
        )
    assert response.status_code == 201
    assert response.json()["work_calendar_date_override_id"] == 31
    assert response.json()["classification"] == "HOLIDAY"


def test_create_version_overlap_returns_conflict() -> None:
    with authorized_client(overlap=True) as client:
        response = client.post(
            "/api/v1/work-calendar-versions",
            json={
                "version_number": 2,
                "effective_from": "2027-01-01",
                "time_zone": "UTC",
                "weekly_rules": [
                    {
                        "iso_weekday": day,
                        "classification": "WORKING_DAY" if day <= 5 else "NON_WORKING_DAY",
                        "scheduled_minutes": 480 if day <= 5 else 0,
                    }
                    for day in range(1, 8)
                ],
            },
        )
    assert response.status_code == 409


def test_date_override_with_nonfailed_payroll_run_returns_conflict() -> None:
    with authorized_client(payroll_statuses=["FINALIZED"]) as client:
        response = client.post(
            "/api/v1/work-calendar-versions/21/date-overrides",
            json={
                "override_date": "2026-02-02",
                "classification": "HOLIDAY",
                "label": "Founders Day",
            },
        )
    assert response.status_code == 409
