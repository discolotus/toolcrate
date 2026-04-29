"""Integration tests for /health and /info endpoints."""


def test_health_no_auth_required(client, auth_headers):
    r = client.get("/api/v1/health", headers={"Host": "localhost"})
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_info_returns_version(client, auth_headers):
    r = client.get("/api/v1/info", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["version"] == "0.1.0-test"
