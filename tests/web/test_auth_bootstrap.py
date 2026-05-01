"""GET /api/v1/auth/bootstrap sets the tc_session cookie; no auth required."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from toolcrate.web.app import AppDeps, create_app
from toolcrate.web.routers.auth_app import build_router as build_auth_app


@pytest.fixture()
def static_dir(tmp_path: Path) -> Path:
    static = tmp_path / "static"
    (static / "assets").mkdir(parents=True)
    (static / "index.html").write_text("<html><body>SPA</body></html>")
    return static


@pytest.fixture()
def client(static_dir: Path) -> TestClient:
    token = "tok-bootstrap"
    th = hashlib.sha256(token.encode()).hexdigest()
    token_file = static_dir.parent / "api-token"
    token_file.write_text(token)
    deps = AppDeps(
        api_token_hash=th,
        allowed_hosts={"localhost", "testserver", "127.0.0.1"},
        routers=[build_auth_app(token_file=token_file, static_dir=static_dir, token_hash=th)],
    )
    return TestClient(create_app(deps))


def test_bootstrap_sets_cookie_no_prior_auth(client: TestClient) -> None:
    resp = client.get("/api/v1/auth/bootstrap")
    assert resp.status_code == 204
    cookie_header = resp.headers.get("set-cookie", "")
    assert "tc_session" in cookie_header
    assert "HttpOnly" in cookie_header
    assert "samesite=strict" in cookie_header.lower()


def test_bootstrap_cookie_enables_api_calls(client: TestClient) -> None:
    """After bootstrap the returned cookie authenticates API calls."""
    bootstrap = client.get("/api/v1/auth/bootstrap")
    assert bootstrap.status_code == 204
    # The TestClient jar should now hold the cookie; use it on /app
    follow = client.get("/app/")
    assert follow.status_code == 200


def test_bootstrap_missing_token_file_returns_503(
    client: TestClient, static_dir: Path
) -> None:
    (static_dir.parent / "api-token").unlink()
    resp = client.get("/api/v1/auth/bootstrap")
    assert resp.status_code == 503


def test_bootstrap_wrong_token_hash_returns_503(
    client: TestClient, static_dir: Path
) -> None:
    (static_dir.parent / "api-token").write_text("different-token")
    resp = client.get("/api/v1/auth/bootstrap")
    assert resp.status_code == 503
