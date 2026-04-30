"""Dev-only CORS allow for the Vite dev server at localhost:5173."""

from __future__ import annotations

import hashlib

import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient

from toolcrate.web.app import AppDeps, create_app


@pytest.fixture()
def make_app():
    def _factory(dev_cors_origins=None):
        token = "x"
        th = hashlib.sha256(token.encode()).hexdigest()
        router = APIRouter()

        @router.get("/api/v1/ping")
        async def ping() -> dict:
            return {"pong": True}

        deps = AppDeps(
            api_token_hash=th,
            allowed_hosts={"localhost", "127.0.0.1", "testserver"},
            routers=[router],
            dev_cors_origins=dev_cors_origins or [],
        )
        return TestClient(create_app(deps))

    return _factory


def test_no_cors_when_origins_empty(make_app) -> None:
    c = make_app()
    resp = c.options(
        "/api/v1/ping",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert "access-control-allow-origin" not in {k.lower() for k in resp.headers}


def test_cors_allows_dev_origin_when_configured(make_app) -> None:
    c = make_app(dev_cors_origins=["http://localhost:5173"])
    resp = c.options(
        "/api/v1/ping",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )
    assert resp.status_code in (200, 204)
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert resp.headers.get("access-control-allow-credentials") == "true"
