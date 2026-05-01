"""Cookie-based auth fallback for the existing bearer dep."""

from __future__ import annotations

import hashlib

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from toolcrate.web.deps import COOKIE_NAME, api_token_auth

TOKEN = "supersecret"
TOKEN_HASH = hashlib.sha256(TOKEN.encode()).hexdigest()


@pytest.fixture()
def client() -> TestClient:
    app = FastAPI()

    @app.get("/protected", dependencies=[__import__("fastapi").Depends(api_token_auth(token_hash=TOKEN_HASH))])
    def protected() -> dict:
        return {"ok": True}

    tc = TestClient(app, raise_server_exceptions=True)
    tc.token = TOKEN  # type: ignore[attr-defined]
    return tc


def test_valid_bearer_accepted(client: TestClient) -> None:
    resp = client.get("/protected", headers={"Authorization": f"Bearer {TOKEN}"})
    assert resp.status_code == 200


def test_invalid_bearer_rejected(client: TestClient) -> None:
    resp = client.get("/protected", headers={"Authorization": "Bearer wrong"})
    assert resp.status_code == 401


def test_valid_cookie_accepted(client: TestClient) -> None:
    resp = client.get("/protected", cookies={COOKIE_NAME: TOKEN})
    assert resp.status_code == 200


def test_invalid_cookie_rejected(client: TestClient) -> None:
    resp = client.get("/protected", cookies={COOKIE_NAME: "wrong"})
    assert resp.status_code == 401


def test_no_credentials_rejected(client: TestClient) -> None:
    resp = client.get("/protected")
    assert resp.status_code == 401


def test_invalid_bearer_does_not_fall_through_to_cookie(client: TestClient) -> None:
    resp = client.get(
        "/protected",
        headers={"Authorization": "Bearer wrong"},
        cookies={"tc_session": client.token},  # type: ignore[attr-defined]
    )
    assert resp.status_code == 401
