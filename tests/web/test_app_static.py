"""GET /app/* serves index.html and sets the tc_session cookie."""

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
    (static / "assets" / "main.js").write_text("console.log('spa')")
    return static


@pytest.fixture()
def client(static_dir: Path) -> TestClient:
    token = "tok-abc"
    th = hashlib.sha256(token.encode()).hexdigest()
    token_file = static_dir.parent / "api-token"
    token_file.write_text(token)

    deps = AppDeps(
        api_token_hash=th,
        allowed_hosts={"localhost", "testserver", "127.0.0.1"},
        routers=[build_auth_app(token_file=token_file, static_dir=static_dir, token_hash=th)],
    )
    return TestClient(create_app(deps))


def test_get_app_root_sets_cookie_and_serves_html(client: TestClient) -> None:
    resp = client.get("/app/")
    assert resp.status_code == 200
    assert "<html>" in resp.text
    assert "tc_session" in resp.headers.get("set-cookie", "")
    assert "HttpOnly" in resp.headers["set-cookie"]
    assert "samesite=strict" in resp.headers["set-cookie"].lower()


def test_get_app_subpath_serves_same_html_spa_fallback(client: TestClient) -> None:
    resp = client.get("/app/lists/42")
    assert resp.status_code == 200
    assert "<html>" in resp.text


def test_root_redirects_to_app(client: TestClient) -> None:
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code in (302, 307)
    assert resp.headers["location"].rstrip("/") == "/app"


def test_assets_served_from_static_dir(client: TestClient) -> None:
    resp = client.get("/app/assets/main.js")
    assert resp.status_code == 200
    assert "console.log('spa')" in resp.text


def test_missing_token_file_serves_install_hint(client: TestClient, static_dir: Path) -> None:
    (static_dir.parent / "api-token").unlink()
    resp = client.get("/app/")
    assert resp.status_code == 503
    assert "toolcrate serve" in resp.text


def test_token_hash_mismatch_serves_install_hint(client: TestClient, static_dir: Path) -> None:
    (static_dir.parent / "api-token").write_text("different-token")
    resp = client.get("/app/")
    assert resp.status_code == 503


def test_missing_static_dir_returns_503(tmp_path: Path) -> None:
    token = "tok-abc"
    th = hashlib.sha256(token.encode()).hexdigest()
    token_file = tmp_path / "api-token"
    token_file.write_text(token)
    static = tmp_path / "absent"
    deps = AppDeps(
        api_token_hash=th,
        allowed_hosts={"localhost", "testserver", "127.0.0.1"},
        routers=[build_auth_app(token_file=token_file, static_dir=static, token_hash=th)],
    )
    c = TestClient(create_app(deps))
    resp = c.get("/app/")
    assert resp.status_code == 503
    assert "Frontend not built" in resp.text
