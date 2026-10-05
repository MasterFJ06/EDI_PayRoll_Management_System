from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies.unit_of_work import get_unit_of_work
from app.infrastructure.security.jwt import create_access_token
from app.main import app


class FakeRepository:
    def __init__(self, id_field: str) -> None:
        self.id_field = id_field
        self.records: list[SimpleNamespace] = []

    def add(self, record: SimpleNamespace) -> SimpleNamespace:
        setattr(record, self.id_field, len(self.records) + 1)
        self.records.append(record)
        return record

    def get_by_id(self, record_id: int) -> SimpleNamespace | None:
        return next(
            (record for record in self.records if getattr(record, self.id_field) == record_id),
            None,
        )


class FakeSalaryStructureRepository(FakeRepository):
    def __init__(self) -> None:
        super().__init__("salary_structure_id")

    def get_by_code(self, code: str) -> SimpleNamespace | None:
        return next((row for row in self.records if row.structure_code == code), None)

    def get_by_id(self, record_id: int) -> SimpleNamespace | None:
        return super().get_by_id(record_id)


class FakeSalaryComponentRepository(FakeRepository):
    def __init__(self) -> None:
        super().__init__("salary_component_id")

    def get_by_code(self, code: str) -> SimpleNamespace | None:
        return next((row for row in self.records if row.component_code == code), None)


class FakeSalaryRevisionRepository(FakeRepository):
    def __init__(self) -> None:
        super().__init__("salary_revision_id")

    def get_by_structure_and_number(
        self, structure_id: int, revision_number: int
    ) -> SimpleNamespace | None:
        return next(
            (
                row
                for row in self.records
                if row.salary_structure_id == structure_id
                and row.revision_number == revision_number
            ),
            None,
        )


class FakeSalaryRevisionComponentRepository:
    def __init__(self) -> None:
        self.records: dict[tuple[int, int], SimpleNamespace] = {}

    def get_by_revision_and_component(
        self, revision_id: int, component_id: int
    ) -> SimpleNamespace | None:
        return self.records.get((revision_id, component_id))

    def add(self, record: SimpleNamespace) -> SimpleNamespace:
        self.records[(record.salary_revision_id, record.salary_component_id)] = record
        return record


class FakeEmployeeSalaryAssignmentRepository(FakeRepository):
    def __init__(self) -> None:
        super().__init__("salary_assignment_id")


class FakeEmployeeRepository:
    def get_by_id(self, employee_id: int) -> SimpleNamespace | None:
        if employee_id == 5:
            return SimpleNamespace(employee_id=5, employment_status="ACTIVE")
        return None


class FakeUserRepository:
    def get_by_id(self, user_id: int) -> SimpleNamespace | None:
        if user_id == 1:
            return SimpleNamespace(
                user_id=1,
                username="api-test-user",
                status="ACTIVE",
            )
        return None


class FakeUnitOfWork:
    def __init__(self) -> None:
        self.users = FakeUserRepository()
        self.employees = FakeEmployeeRepository()
        self.salary_structures = FakeSalaryStructureRepository()
        self.salary_components = FakeSalaryComponentRepository()
        self.salary_revisions = FakeSalaryRevisionRepository()
        self.salary_revision_components = FakeSalaryRevisionComponentRepository()
        self.employee_salary_assignments = FakeEmployeeSalaryAssignmentRepository()
        self.committed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        pass

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.committed = False


@pytest.fixture
def fake_uow():
    uow = FakeUnitOfWork()
    app.dependency_overrides[get_unit_of_work] = lambda: uow
    yield uow
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


def authenticated_headers() -> dict[str, str]:
    token = create_access_token(user_id=1, username="api-test-user")
    return {"Authorization": f"Bearer {token}"}


def structure_payload(**overrides) -> dict[str, object]:
    return {"structure_code": "BASE", "structure_name": "Base Salary", **overrides}


def component_payload(**overrides) -> dict[str, object]:
    return {
        "component_code": "BASIC",
        "component_name": "Basic Pay",
        "component_type": "EARNING",
        **overrides,
    }


def revision_payload(**overrides) -> dict[str, object]:
    return {
        "salary_structure_id": 1,
        "revision_number": 1,
        "effective_from": "2026-01-01",
        **overrides,
    }


def revision_component_payload(**overrides) -> dict[str, object]:
    return {
        "salary_revision_id": 1,
        "salary_component_id": 1,
        "calculation_type": "FIXED",
        "fixed_amount": "1000.00",
        **overrides,
    }


def assignment_payload(**overrides) -> dict[str, object]:
    return {
        "employee_id": 5,
        "salary_revision_id": 1,
        "effective_from": "2026-01-01",
        **overrides,
    }


def seed_structure(uow: FakeUnitOfWork) -> None:
    uow.salary_structures.add(
        SimpleNamespace(
            salary_structure_id=0,
            structure_code="BASE",
            structure_name="Base Salary",
            description=None,
            status="ACTIVE",
        )
    )


def seed_component(uow: FakeUnitOfWork) -> None:
    uow.salary_components.add(
        SimpleNamespace(
            salary_component_id=0,
            component_code="BASIC",
            component_name="Basic Pay",
            component_type="EARNING",
            status="ACTIVE",
        )
    )


def seed_revision(uow: FakeUnitOfWork) -> None:
    uow.salary_revisions.add(
        SimpleNamespace(
            salary_revision_id=0,
            salary_structure_id=1,
            revision_number=1,
            effective_from=date(2026, 1, 1),
            effective_to=None,
        )
    )


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        ("/api/v1/salary-structures", structure_payload()),
        ("/api/v1/salary-components", component_payload()),
        ("/api/v1/salary-revisions", revision_payload()),
        ("/api/v1/salary-revision-components", revision_component_payload()),
        ("/api/v1/employee-salary-assignments", assignment_payload()),
    ],
)
def test_compensation_endpoints_require_authentication(client, fake_uow, path, payload):
    response = client.post(path, json=payload)
    assert response.status_code == 401


def test_create_salary_structure(client, fake_uow):
    response = client.post(
        "/api/v1/salary-structures",
        json=structure_payload(description="Annual base structure"),
        headers=authenticated_headers(),
    )

    assert response.status_code == 201
    assert response.json() == {
        "salary_structure_id": 1,
        "structure_code": "BASE",
        "structure_name": "Base Salary",
        "description": "Annual base structure",
        "status": "ACTIVE",
    }
    assert fake_uow.committed is True


def test_create_salary_component(client, fake_uow):
    response = client.post(
        "/api/v1/salary-components",
        json=component_payload(),
        headers=authenticated_headers(),
    )

    assert response.status_code == 201
    assert response.json() == {
        "salary_component_id": 1,
        "component_code": "BASIC",
        "component_name": "Basic Pay",
        "component_type": "EARNING",
        "status": "ACTIVE",
    }
    assert fake_uow.committed is True


def test_create_salary_revision(client, fake_uow):
    seed_structure(fake_uow)
    response = client.post(
        "/api/v1/salary-revisions",
        json=revision_payload(),
        headers=authenticated_headers(),
    )

    assert response.status_code == 201
    assert response.json() == {
            "salary_revision_id": 1,
        "salary_structure_id": 1,
        "revision_number": 1,
        "effective_from": "2026-01-01",
        "effective_to": None,
    }
    assert fake_uow.committed is True


def test_create_salary_revision_component(client, fake_uow):
    seed_revision(fake_uow)
    seed_component(fake_uow)
    response = client.post(
        "/api/v1/salary-revision-components",
        json=revision_component_payload(),
        headers=authenticated_headers(),
    )

    assert response.status_code == 201
    assert response.json() == {
        "salary_revision_id": 1,
        "salary_component_id": 1,
        "calculation_type": "FIXED",
        "fixed_amount": "1000.00",
        "percentage_value": None,
        "base_component_id": None,
    }
    assert fake_uow.committed is True


def test_create_percentage_salary_revision_component(client, fake_uow):
    seed_revision(fake_uow)
    seed_component(fake_uow)
    fake_uow.salary_components.add(
        SimpleNamespace(
            salary_component_id=0,
            component_code="TAXABLE",
            component_name="Taxable Pay",
            component_type="EARNING",
            status="ACTIVE",
        )
    )
    response = client.post(
        "/api/v1/salary-revision-components",
        json=revision_component_payload(
            calculation_type="PERCENTAGE",
            fixed_amount=None,
            percentage_value="10.0000",
            base_component_id=2,
        ),
        headers=authenticated_headers(),
    )

    assert response.status_code == 201
    assert response.json()["calculation_type"] == "PERCENTAGE"
    assert response.json()["percentage_value"] == "10.0000"


def test_create_employee_salary_assignment(client, fake_uow):
    seed_revision(fake_uow)
    response = client.post(
        "/api/v1/employee-salary-assignments",
        json=assignment_payload(),
        headers=authenticated_headers(),
    )

    assert response.status_code == 201
    assert response.json() == {
        "salary_assignment_id": 1,
        "employee_id": 5,
        "salary_revision_id": 1,
        "effective_from": "2026-01-01",
        "effective_to": None,
    }
    assert fake_uow.committed is True


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        ("/api/v1/salary-structures", {}),
        ("/api/v1/salary-components", {}),
        ("/api/v1/salary-revisions", {}),
        ("/api/v1/salary-revision-components", {}),
        ("/api/v1/employee-salary-assignments", {}),
        ("/api/v1/salary-structures", structure_payload(structure_name="")),
        ("/api/v1/salary-components", component_payload(component_type="BONUS")),
        ("/api/v1/salary-revisions", revision_payload(revision_number=-1)),
        (
            "/api/v1/salary-revision-components",
            revision_component_payload(fixed_amount="-0.01"),
        ),
        ("/api/v1/employee-salary-assignments", assignment_payload(employee_id=0)),
    ],
)
def test_compensation_request_validation(client, fake_uow, path, payload):
    response = client.post(path, json=payload, headers=authenticated_headers())
    assert response.status_code == 422


@pytest.mark.parametrize(
    ("path", "payload", "detail", "prerequisite"),
    [
        (
            "/api/v1/salary-revisions",
            revision_payload(salary_structure_id=99),
            "Salary structure does not exist",
            None,
        ),
        (
            "/api/v1/salary-revision-components",
            revision_component_payload(salary_revision_id=99),
            "Salary revision does not exist",
            None,
        ),
        (
            "/api/v1/salary-revision-components",
            revision_component_payload(salary_component_id=99),
            "Salary component does not exist",
            "revision",
        ),
        (
            "/api/v1/salary-revision-components",
            revision_component_payload(
                calculation_type="PERCENTAGE",
                fixed_amount=None,
                percentage_value="10.0000",
                base_component_id=99,
            ),
            "Base salary component does not exist",
            "revision_component",
        ),
        (
            "/api/v1/employee-salary-assignments",
            assignment_payload(employee_id=99),
            "Employee does not exist",
            None,
        ),
        (
            "/api/v1/employee-salary-assignments",
            assignment_payload(salary_revision_id=99),
            "Salary revision does not exist",
            None,
        ),
    ],
)
def test_compensation_missing_references_return_business_error(
    client, fake_uow, path, payload, detail, prerequisite
):
    if prerequisite in {"revision", "revision_component"}:
        seed_revision(fake_uow)
    if prerequisite == "revision_component":
        seed_component(fake_uow)
    response = client.post(path, json=payload, headers=authenticated_headers())

    assert response.status_code == 409
    assert detail in response.json()["detail"]
    assert response.json()["error"]["code"] == "BUSINESS_RULE_VIOLATION"


@pytest.mark.parametrize(
    ("path", "payload", "seed"),
    [
        ("/api/v1/salary-structures", structure_payload(), "structure"),
        ("/api/v1/salary-components", component_payload(), "component"),
        (
            "/api/v1/salary-revisions",
            revision_payload(),
            "revision",
        ),
        (
            "/api/v1/salary-revision-components",
            revision_component_payload(),
            "revision_component",
        ),
    ],
)
def test_compensation_duplicates_return_business_error(
    client, fake_uow, path, payload, seed
):
    if seed == "structure":
        fake_uow.salary_structures.add(
            SimpleNamespace(
                salary_structure_id=0,
                structure_code="BASE",
                structure_name="Existing",
            )
        )
    elif seed == "component":
        fake_uow.salary_components.add(
            SimpleNamespace(
                salary_component_id=0,
                component_code="BASIC",
                component_name="Existing",
            )
        )
    elif seed == "revision":
        seed_structure(fake_uow)
        fake_uow.salary_revisions.add(
            SimpleNamespace(
                salary_revision_id=0,
                salary_structure_id=1,
                revision_number=1,
            )
        )
    else:
        seed_revision(fake_uow)
        seed_component(fake_uow)
        fake_uow.salary_revision_components.add(
            SimpleNamespace(salary_revision_id=1, salary_component_id=1)
        )

    response = client.post(path, json=payload, headers=authenticated_headers())

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "BUSINESS_RULE_VIOLATION"
    assert response.json()["error"]["request_id"]
    assert fake_uow.committed is False


def test_invalid_revision_component_shape_returns_domain_error(client, fake_uow):
    seed_revision(fake_uow)
    seed_component(fake_uow)
    response = client.post(
        "/api/v1/salary-revision-components",
        json=revision_component_payload(fixed_amount=None),
        headers=authenticated_headers(),
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "BUSINESS_RULE_VIOLATION"
    assert "do not match its calculation type" in response.json()["detail"]


def test_unexpected_error_uses_centralized_response(client, fake_uow):
    fake_uow.salary_structures.get_by_code = Mock(
        side_effect=RuntimeError("internal database detail")
    )
    response = client.post(
        "/api/v1/salary-structures",
        json=structure_payload(),
        headers=authenticated_headers(),
    )

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_SERVER_ERROR"
    assert response.json()["error"]["message"] == "An unexpected error occurred."
    assert "internal database detail" not in response.text


def test_compensation_routes_appear_in_openapi(client):
    assert client.get("/docs").status_code == 200
    response = client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    for path in (
        "/api/v1/salary-structures",
        "/api/v1/salary-components",
        "/api/v1/salary-revisions",
        "/api/v1/salary-revision-components",
        "/api/v1/employee-salary-assignments",
    ):
        operation = schema["paths"][path]["post"]
        assert operation["responses"]["201"]
        assert operation["security"]
        assert "Compensation" in operation["tags"]
