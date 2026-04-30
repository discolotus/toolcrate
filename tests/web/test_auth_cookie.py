"""Cookie-based auth fallback for the existing bearer dep."""

from __future__ import annotations

import hashlib

import pytest
from fastapi import APIRouter, Depends, FastAPI
from fastapi.testclient import TestClient

from toolcrate.web.deps import api_token_auth


@pytest.fixture()
def client() -> TestClient:
    token = "secret-token-xyz"
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    app = FastAPI()
    auth = Depends(api_token_auth(token_hash=token_hash))
    router = APIRouter(dependencies=[auth])

    @router.get("/protected")
    async def protected() -> dict:
        return {"ok": True}

    app.include_router(router)
    c = TestClient(app)
    c.token = token  # type: ignore[attr-defined]
    return c


def test_cookie_auth_succeeds(client: TestClient) -> None:
    resp = client.get("/protected", cookies={"tc_session": client.token})  # type: ignore[attr-defined]
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


def test_bearer_auth_still_succeeds(client: TestClient) -> None:
    resp = client.get(
        "/protected",
        headers={"Authorization": f"Bearer {client.token}"},  # type: ignore[attr-defined]
    )
    assert resp.status_code == 200


def test_cookie_with_wrong_token_rejected(client: TestClient) -> None:
    resp = client.get("/protected", cookies={"tc_session": "wrong"})
    assert resp.status_code == 401


def test_no_credentials_rejected(client: TestClient) -> None:
    resp = client.get("/protected")
    assert resp.status_code == 401


def test_bearer_takes_precedence_over_cookie(client: TestClient) -> None:
    # If a (valid) Authorization header is present, the cookie value is irrelevant.
    resp = client.get(
        "/protected",
        headers={"Authorization": f"Bearer {client.token}"},  # type: ignore[attr-defined]
        cookies={"tc_session": "garbage"},
    )
    assert resp.status_code == 200
