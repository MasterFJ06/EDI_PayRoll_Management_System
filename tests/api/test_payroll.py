from collections.abc import Generator
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.api.dependencies.unit_of_work import get_unit_of_work
from app.infrastructure.persistence.models.payroll_run import PayrollRunModel
from app.infrastructure.security.jwt import create_access_token
from app.main import app


class FakeUserRepository:
    def __init__(self, user: SimpleNamespace) -> None:
        self.user = user

    def get_by_id(self, user_id: int) -> SimpleNamespace | None:
        return self.user if user_id == self.user.user_id else None


class FakeAuthorizationRepository:
    def __init__(self, permissions: set[str]) -> None:
        self.permissions = permissions
        self.calls: list[tuple[int, str]] = []

    def has_permission(self, user_id: int, permission_code: str) -> bool:
        self.calls.append((user_id, permission_code))
        return permission_code in self.permissions


class FakePayrollRunRepository:
    def __init__(self) -> None:
        self.records: list[PayrollRunModel] = []
        self.pending: PayrollRunModel | None = None
        self.fail_on_commit_with_duplicate = False

    def get_by_period(self, year: int, month: int) -> PayrollRunModel | None:
        return next(
            (
                row
                for row in self.records
                if row.payroll_year == year and row.payroll_month == month
            ),
            None,
        )

    def get_by_id(self, run_id: int) -> PayrollRunModel | None:
        return next(
            (row for row in self.records if row.payroll_run_id == run_id), None
        )

    def add(self, model: PayrollRunModel) -> PayrollRunModel:
        model.payroll_run_id = len(self.records) + 1
        self.pending = model
        return model


class FakeUnitOfWork:
    def __init__(self, permissions: set[str]) -> None:
        self.user = SimpleNamespace(
            user_id=12,
            username="payroll-api-test",
            status="ACTIVE",
        )
        self.users = FakeUserRepository(self.user)
        self.authorization = FakeAuthorizationRepository(permissions)
        self.payroll_runs = FakePayrollRunRepository()
        self.committed = False
        self.rolled_back = False

    def commit(self) -> None:
        if self.payroll_runs.fail_on_commit_with_duplicate:
            raise IntegrityError(
                "INSERT payroll_runs",
                {},
                Exception("Duplicate entry for key 'uq_payroll_period'"),
            )
        if self.payroll_runs.pending is not None:
            self.payroll_runs.records.append(self.payroll_runs.pending)
            self.payroll_runs.pending = None
        self.committed = True

    def rollback(self) -> None:
        self.payroll_runs.pending = None
        self.rolled_back = True


@pytest.fixture
def fake_uow() -> Generator[FakeUnitOfWork, None, None]:
    uow = FakeUnitOfWork({"payroll.run.create", "payroll.run.read"})
    app.dependency_overrides[get_unit_of_work] = lambda: uow
    yield uow
    app.dependency_overrides.clear()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


def auth_headers(user_id: int = 12) -> dict[str, str]:
    token = create_access_token(user_id=user_id, username="payroll-api-test")
    return {"Authorization": f"Bearer {token}"}


def run_payload(**overrides: object) -> dict[str, object]:
    return {"year": 2026, "month": 10, **overrides}


def seed_run(uow: FakeUnitOfWork, run_id: int = 7) -> PayrollRunModel:
    run = PayrollRunModel(
        payroll_run_id=run_id,
        payroll_year=2026,
        payroll_month=10,
        status="CREATED",
        initiated_by_user_id=uow.user.user_id,
    )
    uow.payroll_runs.records.append(run)
    return run


def test_create_payroll_run_uses_authenticated_user_and_returns_dto(
    client: TestClient, fake_uow: FakeUnitOfWork
) -> None:
    response = client.post(
        "/api/v1/payroll/runs",
        json=run_payload(),
        headers=auth_headers(),
    )

    assert response.status_code == 201
    assert response.json() == {
        "payroll_run_id": 1,
        "payroll_year": 2026,
        "payroll_month": 10,
        "status": "CREATED",
        "initiated_by_user_id": 12,
    }
    assert fake_uow.payroll_runs.records[0].status == "CREATED"
    assert fake_uow.committed is True
    assert (12, "payroll.run.create") in fake_uow.authorization.calls
    assert "_sa_instance_state" not in response.json()


def test_client_cannot_override_payroll_run_initiator(
    client: TestClient, fake_uow: FakeUnitOfWork
) -> None:
    response = client.post(
        "/api/v1/payroll/runs",
        json=run_payload(initiated_by_user_id=999),
        headers=auth_headers(),
    )

    assert response.status_code == 201
    assert response.json()["initiated_by_user_id"] == 12


def test_duplicate_payroll_period_returns_409(
    client: TestClient, fake_uow: FakeUnitOfWork
) -> None:
    seed_run(fake_uow)

    response = client.post(
        "/api/v1/payroll/runs",
        json=run_payload(),
        headers=auth_headers(),
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "BUSINESS_RULE_VIOLATION"
    assert fake_uow.committed is False


def test_database_period_unique_conflict_is_409_and_rolls_back(
    client: TestClient, fake_uow: FakeUnitOfWork
) -> None:
    fake_uow.payroll_runs.fail_on_commit_with_duplicate = True

    response = client.post(
        "/api/v1/payroll/runs",
        json=run_payload(),
        headers=auth_headers(),
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "BUSINESS_RULE_VIOLATION"
    assert fake_uow.rolled_back is True
    assert fake_uow.payroll_runs.pending is None


@pytest.mark.parametrize(
    "payload",
    [
        {"year": 2026},
        {"month": 10},
        run_payload(month=0),
        run_payload(month=13),
        run_payload(year=0),
        run_payload(year=65536),
    ],
)
def test_invalid_payroll_run_period_returns_422(
    client: TestClient, fake_uow: FakeUnitOfWork, payload: dict[str, object]
) -> None:
    response = client.post(
        "/api/v1/payroll/runs", json=payload, headers=auth_headers()
    )

    assert response.status_code == 422
    assert fake_uow.payroll_runs.pending is None


def test_create_payroll_run_requires_authentication(
    client: TestClient, fake_uow: FakeUnitOfWork
) -> None:
    response = client.post("/api/v1/payroll/runs", json=run_payload())

    assert response.status_code == 401
    assert fake_uow.payroll_runs.records == []


def test_create_payroll_run_requires_create_permission(
    client: TestClient, fake_uow: FakeUnitOfWork
) -> None:
    fake_uow.authorization.permissions = {"payroll.run.read"}

    response = client.post(
        "/api/v1/payroll/runs", json=run_payload(), headers=auth_headers()
    )

    assert response.status_code == 403
    assert fake_uow.payroll_runs.records == []


def test_get_payroll_run_returns_dto(
    client: TestClient, fake_uow: FakeUnitOfWork
) -> None:
    seed_run(fake_uow)

    response = client.get("/api/v1/payroll/runs/7", headers=auth_headers())

    assert response.status_code == 200
    assert response.json() == {
        "payroll_run_id": 7,
        "payroll_year": 2026,
        "payroll_month": 10,
        "status": "CREATED",
        "initiated_by_user_id": 12,
    }
    assert "_sa_instance_state" not in response.json()
    assert (12, "payroll.run.read") in fake_uow.authorization.calls


def test_get_missing_payroll_run_returns_404(
    client: TestClient, fake_uow: FakeUnitOfWork
) -> None:
    response = client.get("/api/v1/payroll/runs/999", headers=auth_headers())

    assert response.status_code == 404
    assert response.json()["detail"] == "Payroll Run not found."


def test_get_payroll_run_requires_read_permission(
    client: TestClient, fake_uow: FakeUnitOfWork
) -> None:
    seed_run(fake_uow)
    fake_uow.authorization.permissions = {"payroll.run.create"}

    response = client.get("/api/v1/payroll/runs/7", headers=auth_headers())

    assert response.status_code == 403


def test_get_payroll_run_requires_authentication(
    client: TestClient, fake_uow: FakeUnitOfWork
) -> None:
    seed_run(fake_uow)

    response = client.get("/api/v1/payroll/runs/7")

    assert response.status_code == 401


def test_payroll_run_routes_appear_in_openapi(client: TestClient) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert paths["/api/v1/payroll/runs"]["post"]["responses"]["201"]
    assert paths["/api/v1/payroll/runs/{run_id}"]["get"]["responses"]["200"]
