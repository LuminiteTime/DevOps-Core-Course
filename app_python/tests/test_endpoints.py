from fastapi.testclient import TestClient

from app_python import app as app_module
from app_python.app import app


client = TestClient(app)


def test_get_root_returns_expected_structure() -> None:
    res = client.get("/", headers={"user-agent": "pytest"})
    assert res.status_code == 200
    data = res.json()

    assert set(data.keys()) == {"service", "system", "runtime", "request", "endpoints"}

    service = data["service"]
    assert service["name"] == "devops-info-service"
    assert service["version"] == "1.0.0"
    assert service["framework"] == "FastAPI"

    system = data["system"]
    assert isinstance(system["hostname"], str) and system["hostname"]
    assert isinstance(system["cpu_count"], int) and system["cpu_count"] >= 1
    assert isinstance(system["python_version"], str) and system["python_version"]

    runtime = data["runtime"]
    assert isinstance(runtime["uptime_seconds"], int) and runtime["uptime_seconds"] >= 0
    assert runtime["timezone"] == "UTC"
    assert isinstance(runtime["current_time"], str) and runtime["current_time"]

    request = data["request"]
    assert request["method"] == "GET"
    assert request["path"] == "/"
    assert request["user_agent"] == "pytest"
    assert isinstance(request["client_ip"], str) and request["client_ip"]

    endpoints = data["endpoints"]
    assert isinstance(endpoints, list) and endpoints
    paths = {e["path"] for e in endpoints}
    assert paths == {"/", "/health"}


def test_get_health_returns_expected_structure() -> None:
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "healthy"
    assert isinstance(data["timestamp"], str) and data["timestamp"]
    assert isinstance(data["uptime_seconds"], int) and data["uptime_seconds"] >= 0


def test_unknown_endpoint_returns_structured_404() -> None:
    res = client.get("/does-not-exist")
    assert res.status_code == 404
    data = res.json()
    assert data == {"error": "Not Found", "message": "Endpoint does not exist"}


def test_method_not_allowed_returns_405() -> None:
    res = client.post("/health")
    assert res.status_code == 405


def test_main_runs_uvicorn_with_expected_options(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_run(*args, **kwargs) -> None:
        captured["args"] = args
        captured["kwargs"] = kwargs

    monkeypatch.setattr(app_module.uvicorn, "run", fake_run)

    app_module.main()

    assert captured["args"] == ("app:app",)
    assert captured["kwargs"] == {
        "host": app_module.HOST,
        "port": app_module.PORT,
        "reload": app_module.DEBUG,
        "log_config": None,
        "access_log": False,
    }
