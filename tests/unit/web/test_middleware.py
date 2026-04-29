from fastapi import FastAPI
from fastapi.testclient import TestClient

from toolcrate.web.middleware import OriginHostGuardMiddleware


def _build_app():
    app = FastAPI()
    app.add_middleware(OriginHostGuardMiddleware,
                       allowed_hosts={"localhost", "127.0.0.1"})

    @app.get("/x")
    def x():
        return {"ok": True}

    return app


def test_localhost_host_allowed():
    c = TestClient(_build_app())
    r = c.get("/x", headers={"Host": "localhost"})
    assert r.status_code == 200


def test_evil_host_rejected():
    c = TestClient(_build_app())
    r = c.get("/x", headers={"Host": "evil.example"})
    assert r.status_code == 403


def test_origin_must_be_localhost_when_present():
    c = TestClient(_build_app())
    r = c.get("/x", headers={"Host": "localhost", "Origin": "https://evil.example"})
    assert r.status_code == 403


def test_origin_localhost_allowed():
    c = TestClient(_build_app())
    r = c.get("/x", headers={"Host": "localhost", "Origin": "http://localhost:48721"})
    assert r.status_code == 200
