import json
import subprocess
import sys

from fastapi.testclient import TestClient

from app.main import create_app


def test_health_is_available_without_account_or_database():
    with TestClient(create_app()) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["content-type"] == "application/json"


def test_unknown_path_uses_the_common_error_format():
    with TestClient(create_app()) as client:
        response = client.get("/_missing")
    assert response.status_code == 404
    assert response.json() == {
        "error": {"code": "not_found", "message": "요청한 경로를 찾을 수 없습니다."}
    }


def test_health_cannot_accept_mutations_and_preserves_the_allow_header():
    with TestClient(create_app()) as client:
        response = client.post("/health")
    assert response.status_code == 405
    assert "GET" in response.headers["allow"].split(", ")
    assert response.json()["error"]["code"] == "method_not_allowed"


def test_validation_error_does_not_echo_private_input():
    app = create_app()

    @app.get("/_validation")
    def validation_route(count: int):
        return count

    with TestClient(app) as client:
        response = client.get("/_validation", params={"count": "synthetic-private-input"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert "synthetic-private-input" not in response.text


def test_internal_error_does_not_expose_exception_details():
    app = create_app()

    @app.get("/_failure")
    def failure_route():
        raise RuntimeError("synthetic-private-detail")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/_failure")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert "synthetic-private-detail" not in response.text


def test_openapi_describes_only_implemented_api_and_its_response():
    with TestClient(create_app()) as client:
        response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert set(schema["paths"]) == {
        "/health",
        "/auth/session",
        "/mails",
        "/mails/{mail_id}",
        "/search",
        "/search/recent",
    }
    assert schema["paths"]["/health"]["get"]["responses"]["200"]["content"]["application/json"][
        "schema"
    ] == {"$ref": "#/components/schemas/HealthResponse"}
    assert (
        schema["components"]["schemas"]["HealthResponse"]["properties"]["status"]["const"] == "ok"
    )


def test_openapi_export_uses_the_actual_app_without_starting_a_server(tmp_path):
    output = tmp_path / "generated" / "openapi.json"
    subprocess.run(
        [sys.executable, "-m", "app.cli.export_openapi", "--output", str(output)],
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(output.read_text()) == create_app().openapi()
