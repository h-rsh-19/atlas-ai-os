from fastapi.testclient import TestClient

from atlas_api.main import app

client = TestClient(app)


def test_root_healthz() -> None:
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "atlas-api"


def test_api_health() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_memory_route_returns_seed_items() -> None:
    response = client.get("/api/memory")

    assert response.status_code == 200
    assert any(memory["source_title"] == "Atlas Product Scope" for memory in response.json())
