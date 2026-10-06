"""API start-up and health endpoint tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app


def test_app_creates_successfully() -> None:
    app = create_app()
    assert app.title.endswith("API")
    assert app.version == get_settings().project.version


def test_health_returns_200(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200


def test_health_body_contains_real_status(client: TestClient) -> None:
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["service"] == "computer-vision-api"
    assert body["version"] == get_settings().project.version
    assert body["classes"] == ["bell", "oillamp"]


def test_openapi_document_available(client: TestClient) -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert "/api/health" in response.json()["paths"]


def test_startup_creates_generated_dirs() -> None:
    """Lifespan runs and generated directories exist afterwards."""
    from app.core.paths import ensure_generated_dirs, generated_dir, generated_dir_names

    ensure_generated_dirs()
    for name in generated_dir_names():
        assert generated_dir(name).is_dir(), name
