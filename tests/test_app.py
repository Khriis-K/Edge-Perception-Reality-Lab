"""Contract tests for the app shell: health, CORS, and serving the built frontend."""

import pytest
from fastapi.testclient import TestClient

from backend.app import VITE_DEV_ORIGINS, create_app

VITE_ORIGIN = VITE_DEV_ORIGINS[0]
INDEX_HTML = "<!doctype html><title>workbench</title>"


@pytest.fixture
def dist(tmp_path):
    """A minimal built-frontend folder, as `vite build` would leave it."""
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text(INDEX_HTML)
    (dist / "assets" / "app.js").write_text("console.log('app')")
    (tmp_path / "secret.txt").write_text("outside dist")
    return dist


@pytest.fixture
def client(dist):
    return TestClient(create_app(static_dir=dist))


# --- health ---------------------------------------------------------------


def test_health_reports_ok(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.parametrize("path", ["/docs", "/redoc"])
def test_no_interactive_docs_pages_that_load_third_party_scripts(client, path):
    # FastAPI's default docs pages pull Swagger UI / ReDoc from a CDN.
    response = client.get(path)

    assert "cdn.jsdelivr.net" not in response.text


def test_health_is_in_openapi_schema(client):
    schema = client.get("/openapi.json").json()

    assert "/api/health" in schema["paths"]
    assert "HealthResponse" in schema["components"]["schemas"]


# --- CORS -----------------------------------------------------------------


def test_normal_mode_sends_no_cors_headers_even_for_vite_origin(client):
    response = client.get("/api/health", headers={"Origin": VITE_ORIGIN})

    assert "access-control-allow-origin" not in response.headers


def test_dev_mode_allows_vite_dev_server_origin(dist):
    client = TestClient(create_app(static_dir=dist, dev=True))

    response = client.get("/api/health", headers={"Origin": VITE_ORIGIN})

    assert response.headers["access-control-allow-origin"] == VITE_ORIGIN


def test_dev_mode_rejects_other_origins(dist):
    client = TestClient(create_app(static_dir=dist, dev=True))

    response = client.get("/api/health", headers={"Origin": "http://evil.example"})

    assert "access-control-allow-origin" not in response.headers


# --- serving the built frontend ---------------------------------------------


@pytest.mark.parametrize("path", ["/", "/setup", "/benchmark", "/findings/anything"])
def test_client_routes_serve_index_html(client, path):
    response = client.get(path)

    assert response.status_code == 200
    assert response.text == INDEX_HTML


def test_built_assets_are_served(client):
    response = client.get("/assets/app.js")

    assert response.status_code == 200
    assert response.text == "console.log('app')"


def test_unknown_api_route_is_json_404_not_index(client):
    response = client.get("/api/does-not-exist")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")


@pytest.mark.parametrize("path", ["/../secret.txt", "/%2e%2e/secret.txt", "/assets/..%2f..%2fsecret.txt"])
def test_paths_outside_dist_are_never_served(client, path):
    response = client.get(path)

    assert "outside dist" not in response.text


def test_missing_frontend_build_gives_actionable_message(tmp_path):
    client = TestClient(create_app(static_dir=tmp_path / "missing"))

    response = client.get("/")

    assert response.status_code == 503
    assert "npm run build" in response.text
    # The API still works without a frontend build.
    assert client.get("/api/health").status_code == 200
