from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from toolcrate.web.deps import api_token_auth


def _build_app(token_hash: str):
    app = FastAPI()

    @app.get("/x")
    def x(_=Depends(api_token_auth(token_hash=token_hash))):
        return {"ok": True}

    return app


def test_missing_token_rejected():
    import hashlib
    h = hashlib.sha256(b"secret").hexdigest()
    c = TestClient(_build_app(h))
    assert c.get("/x").status_code == 401


def test_wrong_token_rejected():
    import hashlib
    h = hashlib.sha256(b"secret").hexdigest()
    c = TestClient(_build_app(h))
    assert c.get("/x", headers={"Authorization": "Bearer wrong"}).status_code == 401


def test_correct_token_passes():
    import hashlib
    h = hashlib.sha256(b"secret").hexdigest()
    c = TestClient(_build_app(h))
    r = c.get("/x", headers={"Authorization": "Bearer secret"})
    assert r.status_code == 200
