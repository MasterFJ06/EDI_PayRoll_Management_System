from uuid import UUID

from fastapi.testclient import TestClient


def test_health_check_returns_ok(
    client: TestClient,
) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200

    assert response.json() == {
        "status": "ok",
        "service": "employee-payroll-api",
    }

def test_health_check_returns_request_id(
    client: TestClient,
) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert response.headers["X-Request-ID"]

def test_each_request_gets_unique_request_id(
    client: TestClient,
) -> None:
    first_response = client.get("/api/v1/health")
    second_response = client.get("/api/v1/health")

    first_id = first_response.headers["X-Request-ID"]
    second_id = second_response.headers["X-Request-ID"]

    assert first_id != second_id

def test_request_id_is_valid_uuid(
    client: TestClient,
) -> None:
    response = client.get("/api/v1/health")

    request_id = response.headers["X-Request-ID"]

    UUID(request_id)