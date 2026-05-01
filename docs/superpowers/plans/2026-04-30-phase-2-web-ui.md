# Phase 2 — Web UI v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Vite/React/TypeScript SPA on top of the merged Phase 1 FastAPI backend, ship four pages (Dashboard skeleton, Spotify lists master/detail, list detail with three tabs, jobs), wire SSE-driven cache invalidation, set up cookie-based auth for zero-friction local UI, and add a hatch build hook so `pip install` produces a ready-to-serve bundle.

**Architecture:** A new `src/toolcrate/web/frontend/` npm package (Vite + React 18 + TypeScript + Tailwind + shadcn/ui + TanStack Query v5 + React Router v6). Backend is extended only where strictly necessary: extend the existing bearer auth dep to also accept the `tc_session` cookie, add an `/app/{path:path}` static route that sets that cookie before serving `index.html`, and add `POST /api/v1/lists/preview` for the Add-list dialog's autofill. A hatch custom build hook runs `npm ci && npm run build` during wheel build (skips gracefully if `npm` is missing, with a stub HTML telling users how to install Node).

**Tech Stack:** Vite 5, React 18, TypeScript 5 (strict), React Router v6 (data routers), TanStack Query v5, shadcn/ui (Radix + Tailwind 3), react-hook-form + zod, `@tanstack/react-virtual`, `openapi-typescript` for generated types, Vitest + Testing Library + MSW for tests. Backend: FastAPI (existing), pytest, hatchling custom build hook.

**Spec:** [docs/superpowers/specs/2026-04-30-phase-2-web-ui-design.md](../specs/2026-04-30-phase-2-web-ui-design.md). Read sections 3–4 before Task 1.

---

## File Structure

**Backend (modify/create):**

- Modify: `src/toolcrate/web/deps.py` — extend `api_token_auth` to accept `tc_session` cookie alongside `Authorization: Bearer`.
- Create: `src/toolcrate/web/routers/auth_app.py` — `/app/*` router that sets cookie + serves SPA. (Named `auth_app` to avoid future collision with an `auth.py` for OAuth in Phase 3.)
- Modify: `src/toolcrate/web/routers/lists.py` — add `POST /api/v1/lists/preview` endpoint.
- Modify: `src/toolcrate/web/schemas/lists.py` — add `ListPreviewIn` and `ListPreviewOut` schemas.
- Modify: `src/toolcrate/cli/serve.py` — wire new `auth_app` router; pick up `static_dir` from settings; gate dev CORS on `TOOLCRATE_ENV`.
- Modify: `src/toolcrate/web/app.py` — accept `dev_cors_origins` on `AppDeps`, register `CORSMiddleware` when set.
- Create: `tests/web/test_auth_cookie.py`
- Create: `tests/web/test_app_static.py`
- Create: `tests/web/test_lists_preview.py`

**Frontend (all new under `src/toolcrate/web/frontend/`):**

```
package.json
package-lock.json           (committed)
vite.config.ts
tsconfig.json
tsconfig.node.json
tailwind.config.ts
postcss.config.js
index.html
.eslintrc.cjs
.gitignore
src/
  main.tsx
  App.tsx
  router.tsx
  api/
    client.ts
    sse.ts
    types.ts                (generated, committed)
    keys.ts                 (query key factory)
  components/
    Sidebar.tsx
    Layout.tsx
    AddListDialog.tsx
    ListMasterTable.tsx
    TrackTable.tsx
    JobLogPane.tsx
    StatusPill.tsx
    LiveBadge.tsx
    ui/                     (shadcn-generated)
  pages/
    Dashboard.tsx
    SpotifyLists.tsx
    ListDetail.tsx
    Jobs.tsx
  hooks/
    useLists.ts
    useTracks.ts
    useJobs.ts
    usePreview.ts
    useSseInvalidation.ts
  lib/
    cn.ts
    format.ts
  styles/
    globals.css
  test/
    setup.ts
    msw-handlers.ts
__tests__/
  client.test.ts
  sse.test.ts
  AddListDialog.test.tsx
  TrackTable.test.tsx
  Jobs.test.tsx
scripts/
  gen-api.ts                (calls openapi-typescript)
```

**Build infrastructure (modify/create at repo root):**

- Create: `scripts/build_frontend.py` (hatch custom build hook)
- Modify: `pyproject.toml` (build hook, artifacts, dev dep)
- Modify: `Makefile` (add `frontend` and `frontend-dev` targets)
- Modify: `.gitignore` (add `src/toolcrate/web/static/`, `node_modules/`)
- Create: `.github/workflows/frontend.yml` (or extend existing)

---

## Conventions

- All commits use Conventional Commits (`feat:`, `fix:`, `chore:`, `test:`, `docs:`).
- Run `pytest tests/web/...::testname -v` for individual backend tests.
- Run `npm run test -- <file>` from `src/toolcrate/web/frontend/` for individual frontend tests.
- Each task ends with a commit. Don't batch.
- Write tests first when the task touches code. Verify they fail, then implement, then verify they pass.

---

## Task 1: Extend `api_token_auth` to accept `tc_session` cookie

**Files:**
- Modify: `src/toolcrate/web/deps.py`
- Create: `tests/web/test_auth_cookie.py`

- [ ] **Step 1: Write the failing test**

Create `tests/web/test_auth_cookie.py`:

```python
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
```

- [ ] **Step 2: Run tests; confirm they fail**

Run: `pytest tests/web/test_auth_cookie.py -v`

Expected: 4 of 5 tests fail (`test_cookie_auth_succeeds`, `test_cookie_with_wrong_token_rejected`, `test_bearer_takes_precedence_over_cookie`, and likely none of cookies are read at all). At least the cookie-only test must FAIL with 401.

- [ ] **Step 3: Implement cookie support in `api_token_auth`**

Replace `src/toolcrate/web/deps.py` entirely with:

```python
"""Shared FastAPI dependencies."""

from __future__ import annotations

import hashlib
import hmac

from fastapi import Cookie, Header, HTTPException, status

COOKIE_NAME = "tc_session"


def api_token_auth(*, token_hash: str):
    """Build a dependency that compares either Authorization: Bearer <token>
    or Cookie tc_session=<token> against a sha256 hash. Header takes precedence."""

    expected = token_hash.lower()

    def _verify(token: str) -> bool:
        got = hashlib.sha256(token.encode("utf-8")).hexdigest()
        return hmac.compare_digest(got, expected)

    def _dep(
        authorization: str | None = Header(default=None),
        tc_session: str | None = Cookie(default=None),
    ) -> None:
        if authorization and authorization.startswith("Bearer "):
            token = authorization[len("Bearer "):]
            if _verify(token):
                return
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token")
        if tc_session and _verify(tc_session):
            return
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing or invalid credentials")

    return _dep
```

- [ ] **Step 4: Run tests; confirm all pass**

Run: `pytest tests/web/test_auth_cookie.py -v`

Expected: all 5 tests PASS.

- [ ] **Step 5: Run the full backend suite to confirm no regressions**

Run: `pytest tests/web/ -v`

Expected: every existing web test still PASSES (the bearer path is unchanged for valid bearers).

- [ ] **Step 6: Commit**

```bash
git add src/toolcrate/web/deps.py tests/web/test_auth_cookie.py
git commit -m "feat(web): accept tc_session cookie alongside bearer token"
```

---

## Task 2: `/app/*` router serving SPA + setting cookie

**Files:**
- Create: `src/toolcrate/web/routers/auth_app.py`
- Create: `tests/web/test_app_static.py`
- Modify: `src/toolcrate/cli/serve.py` (wire router)

- [ ] **Step 1: Write the failing test**

Create `tests/web/test_app_static.py`:

```python
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
    assert "SameSite=strict" in resp.headers["set-cookie"].lower()


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
```

- [ ] **Step 2: Run; confirm fail (`auth_app` does not exist yet)**

Run: `pytest tests/web/test_app_static.py -v`

Expected: import error / module not found.

- [ ] **Step 3: Implement the router**

Create `src/toolcrate/web/routers/auth_app.py`:

```python
"""SPA serving + cookie bootstrap for the local web UI.

GET /app[/...] reads the API token file, verifies it against the configured
hash, sets a tc_session HttpOnly cookie, and returns index.html. All
sub-paths return the same index.html so React Router owns client routing.
"""

from __future__ import annotations

import hashlib
import hmac
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response

COOKIE_NAME = "tc_session"
INSTALL_HINT_HTML = """\
<!doctype html>
<html><head><title>toolcrate</title></head><body style="font-family:sans-serif;padding:2em">
<h1>toolcrate web UI not ready</h1>
<p>The frontend bundle is missing or the API token file is unreadable.</p>
<ul>
  <li>Run <code>toolcrate serve</code> at least once to bootstrap the API token at
      <code>~/.config/toolcrate/api-token</code>.</li>
  <li>If you installed without Node available, rebuild with Node 20+ on PATH, or
      run <code>make frontend</code> from the source tree.</li>
</ul>
</body></html>
"""


def build_router(*, token_file: Path, static_dir: Path, token_hash: str) -> APIRouter:
    """Build the /app router. Pure factory — no global state."""

    expected_hash = token_hash.lower()
    router = APIRouter()

    def _read_token() -> str | None:
        try:
            raw = token_file.read_text().strip()
        except (FileNotFoundError, PermissionError, OSError):
            return None
        if not raw:
            return None
        got = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        if not hmac.compare_digest(got, expected_hash):
            return None
        return raw

    def _index_or_hint() -> Response:
        index = static_dir / "index.html"
        if not index.exists():
            return HTMLResponse(INSTALL_HINT_HTML, status_code=503)
        token = _read_token()
        if token is None:
            return HTMLResponse(INSTALL_HINT_HTML, status_code=503)
        resp = FileResponse(index)
        resp.set_cookie(
            key=COOKIE_NAME,
            value=token,
            httponly=True,
            samesite="strict",
            secure=False,  # 127.0.0.1 is plain HTTP
            path="/",
        )
        return resp

    @router.get("/")
    async def redirect_root() -> RedirectResponse:
        return RedirectResponse(url="/app/")

    @router.get("/app", include_in_schema=False)
    @router.get("/app/", include_in_schema=False)
    async def app_root() -> Response:
        return _index_or_hint()

    @router.get("/app/assets/{path:path}", include_in_schema=False)
    async def assets(path: str) -> Response:
        target = (static_dir / "assets" / path).resolve()
        # Defense in depth: ensure the resolved path stays inside the assets dir.
        try:
            target.relative_to((static_dir / "assets").resolve())
        except ValueError:
            return Response(status_code=404)
        if not target.exists() or not target.is_file():
            return Response(status_code=404)
        return FileResponse(target)

    @router.get("/app/{path:path}", include_in_schema=False)
    async def spa_fallback(path: str) -> Response:
        return _index_or_hint()

    return router
```

- [ ] **Step 4: Run the static tests; confirm they pass**

Run: `pytest tests/web/test_app_static.py -v`

Expected: all 7 tests PASS.

- [ ] **Step 5: Wire the router into `serve.py`**

In `src/toolcrate/cli/serve.py`, around the `routers=[...]` list (currently lines ~122–128), add the new router. After the import block, add:

```python
from toolcrate.web.routers.auth_app import build_router as build_auth_app
```

Inside `serve()`, after `api_token = _ensure_api_token(config_dir)` and before the `deps = AppDeps(...)` block, add:

```python
    static_dir = Path(__file__).resolve().parents[1] / "web" / "static"
    token_file = config_dir / "api-token"
```

Then in the `routers=[...]` list inside `AppDeps`, append:

```python
            build_auth_app(token_file=token_file, static_dir=static_dir, token_hash=api_token_hash),
```

(Order of routers does not matter; place it last for readability.)

- [ ] **Step 6: Smoke-run `toolcrate serve` locally**

Run (in a separate shell): `toolcrate serve --port 48721`

In another shell: `curl -i http://127.0.0.1:48721/app/`

Expected: HTTP 503 with the install hint (because `static/index.html` does not exist yet — that's the entire next phase). Stop the server with `Ctrl-C`.

- [ ] **Step 7: Commit**

```bash
git add src/toolcrate/web/routers/auth_app.py tests/web/test_app_static.py src/toolcrate/cli/serve.py
git commit -m "feat(web): /app router serves SPA and sets tc_session cookie"
```

---

## Task 3: `POST /api/v1/lists/preview` for Add-list autofill

**Files:**
- Modify: `src/toolcrate/web/schemas/lists.py`
- Modify: `src/toolcrate/web/routers/lists.py`
- Create: `tests/web/test_lists_preview.py`

- [ ] **Step 1: Add request/response schemas**

Append to `src/toolcrate/web/schemas/lists.py`:

```python
class ListPreviewIn(BaseModel):
    source_url: str = Field(min_length=1)


class ListPreviewOut(BaseModel):
    source_type: SourceType
    external_id: str
    name: str
    owner: str
    total_tracks: int
    art_url: str | None = None
```

- [ ] **Step 2: Write the failing endpoint test**

Create `tests/web/test_lists_preview.py`:

```python
"""POST /api/v1/lists/preview — autofill helper for the Add-list dialog."""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from toolcrate.core.spotify import SpotifyPlaylist, SpotifyTrack
from toolcrate.web.app import AppDeps, create_app
from toolcrate.web.routers.lists import build_router as build_lists


class _StubSrc:
    """Stand-in for SourceListService that only needs preview_url to work."""

    def __init__(self) -> None:
        self.preview_url = AsyncMock()


@pytest.fixture()
def stub_src() -> _StubSrc:
    return _StubSrc()


@pytest.fixture()
def stub_queue() -> object:
    class _Q:  # noqa: D401
        async def enqueue(self, *_a, **_kw):
            raise AssertionError("not used in preview tests")
    return _Q()


@pytest.fixture()
def client(stub_src: _StubSrc, stub_queue: object) -> Iterator[TestClient]:
    token = "tok-1"
    th = hashlib.sha256(token.encode()).hexdigest()
    deps = AppDeps(
        api_token_hash=th,
        allowed_hosts={"localhost", "testserver", "127.0.0.1"},
        routers=[build_lists(src=stub_src, queue=stub_queue, token_hash=th)],  # type: ignore[arg-type]
    )
    c = TestClient(create_app(deps))
    yield c


@pytest.fixture()
def auth() -> dict:
    return {"Authorization": "Bearer tok-1"}


def test_preview_spotify_playlist_returns_metadata(
    client: TestClient, stub_src: _StubSrc, auth: dict
) -> None:
    stub_src.preview_url.return_value = SpotifyPlaylist(
        id="abc123",
        name="Daft Punk Essentials",
        owner="spotify",
        image_url="https://i.scdn.co/x.jpg",
        tracks=[
            SpotifyTrack("t1", "Daft Punk", "One More Time", "Discovery", "GBARL0001234", 320),
            SpotifyTrack("t2", "Daft Punk", "Aerodynamic", "Discovery", "GBARL0001235", 213),
        ],
    )
    resp = client.post(
        "/api/v1/lists/preview",
        json={"source_url": "https://open.spotify.com/playlist/abc123"},
        headers=auth,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body == {
        "source_type": "spotify_playlist",
        "external_id": "abc123",
        "name": "Daft Punk Essentials",
        "owner": "spotify",
        "total_tracks": 2,
        "art_url": "https://i.scdn.co/x.jpg",
    }
    stub_src.preview_url.assert_awaited_once_with("https://open.spotify.com/playlist/abc123")


def test_preview_unrecognized_url_returns_400(
    client: TestClient, stub_src: _StubSrc, auth: dict
) -> None:
    from toolcrate.core.exceptions import ValidationError

    stub_src.preview_url.side_effect = ValidationError("unsupported source url")
    resp = client.post(
        "/api/v1/lists/preview",
        json={"source_url": "https://not-spotify.example/foo"},
        headers=auth,
    )
    assert resp.status_code == 400
    assert "unsupported" in resp.json()["detail"].lower()


def test_preview_remote_404_returns_404(
    client: TestClient, stub_src: _StubSrc, auth: dict
) -> None:
    from toolcrate.core.exceptions import NotFound

    stub_src.preview_url.side_effect = NotFound("playlist missing")
    resp = client.post(
        "/api/v1/lists/preview",
        json={"source_url": "https://open.spotify.com/playlist/zzz"},
        headers=auth,
    )
    assert resp.status_code == 404


def test_preview_requires_auth(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/lists/preview",
        json={"source_url": "https://open.spotify.com/playlist/abc"},
    )
    assert resp.status_code == 401
```

- [ ] **Step 3: Run; confirm fail**

Run: `pytest tests/web/test_lists_preview.py -v`

Expected: tests fail (`preview_url` does not exist on `SourceListService`, and the endpoint is not registered).

- [ ] **Step 4: Add `SourceListService.preview_url`**

In `src/toolcrate/core/source_lists.py`, add a method on `SourceListService`:

```python
    async def preview_url(self, url: str) -> SpotifyPlaylist:
        """Fetch playlist metadata for the Add-list autofill UI without persisting.

        Raises ValidationError if the URL doesn't match a supported source type.
        Raises NotFound if the remote refuses (404 / no such playlist).
        """
        from toolcrate.core.spotify import SpotifyClient, parse_playlist_url

        playlist_id = parse_playlist_url(url)
        if playlist_id is None:
            raise ValidationError("unsupported source url")
        client_id, client_secret = self._spotify_credentials()
        async with SpotifyClient(client_id=client_id, client_secret=client_secret) as sp:
            try:
                return await sp.fetch_playlist(playlist_id)
            except IntegrationError as e:
                msg = str(e).lower()
                if "404" in msg:
                    raise NotFound("playlist not found on remote") from e
                raise
```

The exact import location of `IntegrationError`, `NotFound`, `ValidationError`, and `_spotify_credentials` is whatever the existing `source_lists.py` already uses; do not duplicate or rename. If `_spotify_credentials` doesn't exist, factor the credential read out of whatever method already calls `SpotifyClient` (search for `SpotifyClient(` in `core/source_lists.py` and `core/sync.py`). If `SpotifyClient` doesn't yet support `async with` (no `__aenter__`/`__aexit__`), call `sp = SpotifyClient(...)` then `try: ... finally: await sp.aclose()` instead — match the existing pattern.

If you make a refactor here, that becomes its own preceding commit (`refactor: extract spotify credential resolver`).

- [ ] **Step 5: Add the endpoint to `routers/lists.py`**

Inside `build_router` in `src/toolcrate/web/routers/lists.py`, after the existing `create` route, add:

```python
    @router.post("/preview", response_model=ListPreviewOut)
    async def preview(payload: ListPreviewIn) -> ListPreviewOut:
        try:
            playlist = await src.preview_url(payload.source_url)
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        except NotFound as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        return ListPreviewOut(
            source_type="spotify_playlist",
            external_id=playlist.id,
            name=playlist.name,
            owner=playlist.owner,
            total_tracks=len(playlist.tracks),
            art_url=playlist.image_url,
        )
```

Update the imports at the top of the file:

```python
from toolcrate.web.schemas.lists import (
    ListPreviewIn,
    ListPreviewOut,
    SourceListIn,
    SourceListOut,
    SourceListPatch,
)
```

- [ ] **Step 6: Run; confirm pass**

Run: `pytest tests/web/test_lists_preview.py -v`

Expected: all 4 tests PASS.

- [ ] **Step 7: Run full backend suite**

Run: `pytest tests/ -v`

Expected: every test PASSES. If any pre-existing test fails, your `preview_url` refactor likely broke an internal contract — revert and add `preview_url` as a fully separate method instead of refactoring shared helpers.

- [ ] **Step 8: Commit**

```bash
git add src/toolcrate/core/source_lists.py src/toolcrate/web/schemas/lists.py src/toolcrate/web/routers/lists.py tests/web/test_lists_preview.py
git commit -m "feat(web): POST /lists/preview returns Spotify playlist metadata for Add-list dialog"
```

---

## Task 4: Dev-mode CORS hook on `AppDeps`

**Files:**
- Modify: `src/toolcrate/web/app.py`
- Modify: `src/toolcrate/cli/serve.py`
- Create: `tests/web/test_dev_cors.py`

- [ ] **Step 1: Write the failing test**

Create `tests/web/test_dev_cors.py`:

```python
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
    # No CORS middleware → preflight is rejected (405) or returns no CORS headers.
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
```

Note: the existing `OriginHostGuardMiddleware` will reject the preflight if `localhost` is not in `allowed_hosts`. The fixture above includes `localhost`, so the guard passes; CORS headers are what we are actually asserting.

- [ ] **Step 2: Run; confirm fail (`dev_cors_origins` does not exist on `AppDeps`)**

Run: `pytest tests/web/test_dev_cors.py -v`

Expected: TypeError or attribute error.

- [ ] **Step 3: Extend `AppDeps` and `create_app`**

Replace `src/toolcrate/web/app.py` with:

```python
"""FastAPI app factory."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .middleware import OriginHostGuardMiddleware


@dataclass
class AppDeps:
    api_token_hash: str
    allowed_hosts: set[str]
    routers: Iterable = ()
    dev_cors_origins: Sequence[str] = field(default_factory=list)


def create_app(deps: AppDeps) -> FastAPI:
    app = FastAPI(
        title="toolcrate",
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
    )
    if deps.dev_cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(deps.dev_cors_origins),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    app.add_middleware(OriginHostGuardMiddleware, allowed_hosts=deps.allowed_hosts)
    for router in deps.routers:
        app.include_router(router)
    return app
```

Order matters: register `CORSMiddleware` **before** `OriginHostGuardMiddleware` in the source so it executes outermost (Starlette stacks in reverse).

- [ ] **Step 4: Wire env-flag in `serve.py`**

In `src/toolcrate/cli/serve.py`, inside `serve()` just before constructing `AppDeps`, add:

```python
    dev_cors = (
        ["http://localhost:5173"] if os.environ.get("TOOLCRATE_ENV") == "dev" else []
    )
```

Add `dev_cors_origins=dev_cors,` as a keyword argument to the `AppDeps(...)` call.

- [ ] **Step 5: Run tests; confirm pass**

Run: `pytest tests/web/test_dev_cors.py tests/web/test_auth_cookie.py tests/web/test_app_static.py -v`

Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add src/toolcrate/web/app.py src/toolcrate/cli/serve.py tests/web/test_dev_cors.py
git commit -m "feat(web): opt-in CORS for Vite dev server via TOOLCRATE_ENV=dev"
```

---

## Task 5: Hatch custom build hook + repo-level wiring

**Files:**
- Create: `scripts/build_frontend.py`
- Modify: `pyproject.toml`
- Modify: `Makefile`
- Modify: `.gitignore`

- [ ] **Step 1: Write the build hook**

Create `scripts/build_frontend.py`:

```python
"""Hatch build hook that compiles the React SPA into src/toolcrate/web/static/.

Skips gracefully when:
  - TOOLCRATE_SKIP_FRONTEND_BUILD=1 in the environment (CI lint/test stages)
  - npm is not on PATH (writes a stub index.html with install instructions)

When `npm` is available, runs `npm ci && npm run build` from the frontend
package directory; Vite is configured to emit into the static dir.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

STUB_HTML = """\
<!doctype html>
<html><head><title>toolcrate</title></head><body style="font-family:sans-serif;padding:2em">
<h1>toolcrate web UI not built</h1>
<p>Node 20+ was not on PATH when this package was built. The CLI still works.</p>
<p>To build the UI, install Node 20+ and run <code>make frontend</code> from the source tree.</p>
</body></html>
"""


class FrontendBuildHook(BuildHookInterface):
    PLUGIN_NAME = "frontend"

    def initialize(self, version: str, build_data: dict) -> None:
        root = Path(self.root)
        frontend_dir = root / "src" / "toolcrate" / "web" / "frontend"
        static_dir = root / "src" / "toolcrate" / "web" / "static"

        if os.environ.get("TOOLCRATE_SKIP_FRONTEND_BUILD") == "1":
            self.app.display_info("[frontend] TOOLCRATE_SKIP_FRONTEND_BUILD=1, skipping")
            self._ensure_stub(static_dir)
            return

        if not frontend_dir.exists():
            self.app.display_warning(f"[frontend] {frontend_dir} not found, skipping")
            self._ensure_stub(static_dir)
            return

        npm = shutil.which("npm")
        if npm is None:
            self.app.display_warning("[frontend] npm not on PATH; writing stub index.html")
            self._ensure_stub(static_dir)
            return

        static_dir.mkdir(parents=True, exist_ok=True)
        self.app.display_info("[frontend] running npm ci")
        subprocess.run([npm, "ci"], cwd=frontend_dir, check=True)
        self.app.display_info("[frontend] running npm run build")
        subprocess.run([npm, "run", "build"], cwd=frontend_dir, check=True)

        if not (static_dir / "index.html").exists():
            self.app.abort("[frontend] build finished but no index.html in static_dir")
            sys.exit(1)

    def _ensure_stub(self, static_dir: Path) -> None:
        static_dir.mkdir(parents=True, exist_ok=True)
        index = static_dir / "index.html"
        if not index.exists():
            index.write_text(STUB_HTML)
```

- [ ] **Step 2: Register the hook in `pyproject.toml`**

Open `pyproject.toml`. Add (or merge into existing tables):

```toml
[tool.hatch.build.hooks.custom]
path = "scripts/build_frontend.py"

[tool.hatch.build.targets.wheel]
packages = ["src/toolcrate"]
artifacts = ["src/toolcrate/web/static/**"]

[tool.hatch.build.targets.sdist]
include = [
  "src/toolcrate",
  "scripts/build_frontend.py",
  "alembic.ini",
  "alembic",
  "Makefile",
  "README.md",
  "pyproject.toml",
  "tests",
]
```

If `[tool.hatch.build.targets.wheel]` already has `packages` defined, merge the `artifacts` line in. If `[tool.hatch.build.targets.sdist]` already exists, merge — do not duplicate.

- [ ] **Step 3: Add Make targets**

In `Makefile`, append:

```make
.PHONY: frontend frontend-dev frontend-test

frontend:
	cd src/toolcrate/web/frontend && npm ci && npm run build

frontend-dev:
	cd src/toolcrate/web/frontend && npm ci && npm run dev

frontend-test:
	cd src/toolcrate/web/frontend && npm ci && npm run lint && npm run typecheck && npm run test -- --run && npm run build
```

- [ ] **Step 4: Update `.gitignore`**

Append to `.gitignore`:

```
# Built frontend bundle (built during wheel build by scripts/build_frontend.py)
src/toolcrate/web/static/

# Frontend node_modules
src/toolcrate/web/frontend/node_modules/
```

- [ ] **Step 5: Smoke-test the hook with no frontend dir yet**

Run: `TOOLCRATE_SKIP_FRONTEND_BUILD=1 python -m build --wheel 2>&1 | tail -20`

Expected: a wheel is produced. The hook should display a `[frontend] TOOLCRATE_SKIP_FRONTEND_BUILD=1, skipping` line. If `python -m build` is not installed, install with `pip install build` first.

If the build fails due to other unrelated reasons (e.g. missing system deps), that is fine — the goal here is only to confirm the hook itself runs without errors. Note any error output and proceed; the hook's real exercise comes in Task 11 once the frontend dir exists.

- [ ] **Step 6: Commit**

```bash
git add scripts/build_frontend.py pyproject.toml Makefile .gitignore
git commit -m "build(frontend): hatch hook compiles React SPA during wheel build"
```

---

## Task 6: Vite + React + TypeScript scaffold

**Files (all new):** `src/toolcrate/web/frontend/{package.json,vite.config.ts,tsconfig.json,tsconfig.node.json,index.html,.eslintrc.cjs,.gitignore,src/main.tsx,src/App.tsx,src/styles/globals.css}`

- [ ] **Step 1: Create the npm package**

Run from repo root:

```bash
mkdir -p src/toolcrate/web/frontend
cd src/toolcrate/web/frontend
```

- [ ] **Step 2: Write `package.json`**

Create `src/toolcrate/web/frontend/package.json`:

```json
{
  "name": "@toolcrate/web-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "lint": "eslint . --ext .ts,.tsx --report-unused-disable-directives --max-warnings 0",
    "typecheck": "tsc --noEmit",
    "test": "vitest",
    "gen:api": "tsx scripts/gen-api.ts"
  },
  "dependencies": {
    "@radix-ui/react-dialog": "^1.1.6",
    "@radix-ui/react-slot": "^1.1.2",
    "@radix-ui/react-tabs": "^1.1.3",
    "@tanstack/react-query": "^5.66.0",
    "@tanstack/react-virtual": "^3.10.9",
    "class-variance-authority": "^0.7.1",
    "clsx": "^2.1.1",
    "lucide-react": "^0.475.0",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-hook-form": "^7.54.2",
    "react-router-dom": "^6.30.0",
    "sonner": "^1.7.4",
    "tailwind-merge": "^3.0.2",
    "zod": "^3.24.2"
  },
  "devDependencies": {
    "@testing-library/dom": "^10.4.0",
    "@testing-library/jest-dom": "^6.6.3",
    "@testing-library/react": "^16.2.0",
    "@testing-library/user-event": "^14.6.1",
    "@types/node": "^22.13.4",
    "@types/react": "^18.3.18",
    "@types/react-dom": "^18.3.5",
    "@typescript-eslint/eslint-plugin": "^8.24.0",
    "@typescript-eslint/parser": "^8.24.0",
    "@vitejs/plugin-react": "^4.3.4",
    "autoprefixer": "^10.4.20",
    "eslint": "^8.57.1",
    "eslint-plugin-react-hooks": "^5.1.0",
    "eslint-plugin-react-refresh": "^0.4.18",
    "jsdom": "^26.0.0",
    "msw": "^2.7.0",
    "openapi-typescript": "^7.6.1",
    "postcss": "^8.5.2",
    "tailwindcss": "^3.4.17",
    "tsx": "^4.19.2",
    "typescript": "^5.7.3",
    "vite": "^5.4.14",
    "vitest": "^2.1.9"
  }
}
```

- [ ] **Step 3: Write `vite.config.ts`**

Create `src/toolcrate/web/frontend/vite.config.ts`:

```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:48721",
        changeOrigin: false,
        ws: false,
      },
    },
  },
  build: {
    outDir: "../static",
    emptyOutDir: true,
    sourcemap: true,
    target: "es2022",
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    globals: true,
    css: false,
  },
});
```

- [ ] **Step 4: Write the two `tsconfig`s**

`src/toolcrate/web/frontend/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "useDefineForClassFields": true,
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "Bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": { "@/*": ["./src/*"] },
    "types": ["vitest/globals", "@testing-library/jest-dom"]
  },
  "include": ["src", "__tests__", "scripts"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

`src/toolcrate/web/frontend/tsconfig.node.json`:

```json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "allowSyntheticDefaultImports": true,
    "strict": true
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **Step 5: Write the entry HTML and React entry**

`src/toolcrate/web/frontend/index.html`:

```html
<!doctype html>
<html lang="en" class="dark">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>toolcrate</title>
  </head>
  <body class="bg-background text-foreground">
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

`src/toolcrate/web/frontend/src/main.tsx`:

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./styles/globals.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
```

`src/toolcrate/web/frontend/src/App.tsx` (placeholder; replaced in Task 10):

```tsx
export default function App() {
  return <div className="p-8 text-2xl">toolcrate — booting…</div>;
}
```

`src/toolcrate/web/frontend/src/styles/globals.css` (Tailwind base; expanded in Task 7):

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

- [ ] **Step 6: Write ESLint config**

`src/toolcrate/web/frontend/.eslintrc.cjs`:

```js
module.exports = {
  root: true,
  env: { browser: true, es2022: true, node: true },
  parser: "@typescript-eslint/parser",
  parserOptions: { ecmaVersion: "latest", sourceType: "module" },
  extends: [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
    "plugin:react-hooks/recommended",
  ],
  plugins: ["react-refresh"],
  rules: {
    "react-refresh/only-export-components": ["warn", { allowConstantExport: true }],
    "@typescript-eslint/no-unused-vars": ["error", { argsIgnorePattern: "^_" }],
  },
  ignorePatterns: ["dist", "node_modules", "src/api/types.ts"],
};
```

- [ ] **Step 7: Write the frontend `.gitignore`**

`src/toolcrate/web/frontend/.gitignore`:

```
node_modules
dist
.vite
*.log
```

- [ ] **Step 8: Install + smoke-build**

Run from `src/toolcrate/web/frontend/`:

```bash
npm install
npm run build
```

Expected: build succeeds; output appears at `src/toolcrate/web/static/index.html` (one level up). If npm refuses due to peer-dep complaints, rerun with `npm install --legacy-peer-deps` and add `legacy-peer-deps=true` to a new `src/toolcrate/web/frontend/.npmrc`.

- [ ] **Step 9: Smoke-run via `toolcrate serve`**

Run (separate shell): `toolcrate serve --port 48721`

Run: `curl -i http://127.0.0.1:48721/app/`

Expected: HTTP 200 with the placeholder "toolcrate — booting…" content. The `Set-Cookie: tc_session=...` header is present.

Stop the server.

- [ ] **Step 10: Commit**

The committed `package-lock.json` is large but required.

```bash
git add src/toolcrate/web/frontend/package.json src/toolcrate/web/frontend/package-lock.json src/toolcrate/web/frontend/vite.config.ts src/toolcrate/web/frontend/tsconfig.json src/toolcrate/web/frontend/tsconfig.node.json src/toolcrate/web/frontend/index.html src/toolcrate/web/frontend/.eslintrc.cjs src/toolcrate/web/frontend/.gitignore src/toolcrate/web/frontend/src
git commit -m "feat(frontend): vite + react + ts scaffold with tailwind base"
```

---

## Task 7: Tailwind + shadcn/ui base components

**Files (new):** `tailwind.config.ts`, `postcss.config.js`, `src/lib/cn.ts`, `src/components/ui/{button,dialog,input,table,tabs,badge,card}.tsx` (auto-generated by shadcn CLI), expanded `src/styles/globals.css`.

- [ ] **Step 1: Write `tailwind.config.ts`**

`src/toolcrate/web/frontend/tailwind.config.ts`:

```ts
import type { Config } from "tailwindcss";

export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}", "./__tests__/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
    },
  },
  plugins: [],
} satisfies Config;
```

- [ ] **Step 2: Write `postcss.config.js`**

`src/toolcrate/web/frontend/postcss.config.js`:

```js
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
```

- [ ] **Step 3: Write the shadcn-style `cn` helper**

`src/toolcrate/web/frontend/src/lib/cn.ts`:

```ts
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
```

- [ ] **Step 4: Replace `globals.css` with the dark-mode shadcn defaults**

`src/toolcrate/web/frontend/src/styles/globals.css`:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 240 10% 3.9%;
    --card: 0 0% 100%;
    --card-foreground: 240 10% 3.9%;
    --primary: 240 5.9% 10%;
    --primary-foreground: 0 0% 98%;
    --secondary: 240 4.8% 95.9%;
    --secondary-foreground: 240 5.9% 10%;
    --muted: 240 4.8% 95.9%;
    --muted-foreground: 240 3.8% 46.1%;
    --accent: 240 4.8% 95.9%;
    --accent-foreground: 240 5.9% 10%;
    --destructive: 0 84.2% 60.2%;
    --destructive-foreground: 0 0% 98%;
    --border: 240 5.9% 90%;
    --input: 240 5.9% 90%;
    --ring: 240 10% 3.9%;
    --radius: 0.5rem;
  }
  .dark {
    --background: 240 10% 3.9%;
    --foreground: 0 0% 98%;
    --card: 240 10% 3.9%;
    --card-foreground: 0 0% 98%;
    --primary: 0 0% 98%;
    --primary-foreground: 240 5.9% 10%;
    --secondary: 240 3.7% 15.9%;
    --secondary-foreground: 0 0% 98%;
    --muted: 240 3.7% 15.9%;
    --muted-foreground: 240 5% 64.9%;
    --accent: 240 3.7% 15.9%;
    --accent-foreground: 0 0% 98%;
    --destructive: 0 62.8% 30.6%;
    --destructive-foreground: 0 0% 98%;
    --border: 240 3.7% 15.9%;
    --input: 240 3.7% 15.9%;
    --ring: 240 4.9% 83.9%;
  }
  body {
    @apply bg-background text-foreground;
  }
}
```

- [ ] **Step 5: Generate the shadcn primitives we need**

Inline rather than running the shadcn CLI (avoids interactive prompts during automated execution). Create the following files exactly as written. These match shadcn's `new-york` style + slate base, which are the defaults for the Radix primitives we declared in `package.json`.

`src/toolcrate/web/frontend/src/components/ui/button.tsx`:

```tsx
import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/cn";

const buttonVariants = cva(
  "inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground shadow hover:bg-primary/90",
        destructive: "bg-destructive text-destructive-foreground shadow-sm hover:bg-destructive/90",
        outline: "border border-input bg-background shadow-sm hover:bg-accent hover:text-accent-foreground",
        secondary: "bg-secondary text-secondary-foreground shadow-sm hover:bg-secondary/80",
        ghost: "hover:bg-accent hover:text-accent-foreground",
        link: "text-primary underline-offset-4 hover:underline",
      },
      size: {
        default: "h-9 px-4 py-2",
        sm: "h-8 rounded-md px-3 text-xs",
        lg: "h-10 rounded-md px-8",
        icon: "h-9 w-9",
      },
    },
    defaultVariants: { variant: "default", size: "default" },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return <Comp className={cn(buttonVariants({ variant, size, className }))} ref={ref} {...props} />;
  },
);
Button.displayName = "Button";

export { buttonVariants };
```

`src/toolcrate/web/frontend/src/components/ui/input.tsx`:

```tsx
import * as React from "react";
import { cn } from "@/lib/cn";

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, type, ...props }, ref) => (
    <input
      type={type}
      className={cn(
        "flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
      ref={ref}
      {...props}
    />
  ),
);
Input.displayName = "Input";
```

`src/toolcrate/web/frontend/src/components/ui/badge.tsx`:

```tsx
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/cn";
import * as React from "react";

const badgeVariants = cva(
  "inline-flex items-center rounded-md border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default: "border-transparent bg-primary text-primary-foreground shadow hover:bg-primary/80",
        secondary: "border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80",
        destructive: "border-transparent bg-destructive text-destructive-foreground shadow hover:bg-destructive/80",
        outline: "text-foreground",
        success: "border-transparent bg-emerald-700 text-white",
        warning: "border-transparent bg-amber-600 text-white",
      },
    },
    defaultVariants: { variant: "default" },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}
```

`src/toolcrate/web/frontend/src/components/ui/card.tsx`:

```tsx
import * as React from "react";
import { cn } from "@/lib/cn";

export const Card = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("rounded-xl border bg-card text-card-foreground shadow", className)} {...props} />
  ),
);
Card.displayName = "Card";

export const CardHeader = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("flex flex-col space-y-1.5 p-6", className)} {...props} />
  ),
);
CardHeader.displayName = "CardHeader";

export const CardTitle = React.forwardRef<HTMLHeadingElement, React.HTMLAttributes<HTMLHeadingElement>>(
  ({ className, ...props }, ref) => (
    <h3 ref={ref} className={cn("font-semibold leading-none tracking-tight", className)} {...props} />
  ),
);
CardTitle.displayName = "CardTitle";

export const CardContent = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => <div ref={ref} className={cn("p-6 pt-0", className)} {...props} />,
);
CardContent.displayName = "CardContent";
```

`src/toolcrate/web/frontend/src/components/ui/dialog.tsx`:

```tsx
import * as React from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { cn } from "@/lib/cn";

export const Dialog = DialogPrimitive.Root;
export const DialogTrigger = DialogPrimitive.Trigger;
export const DialogClose = DialogPrimitive.Close;

export const DialogPortal = ({ ...props }: DialogPrimitive.DialogPortalProps) => (
  <DialogPrimitive.Portal {...props} />
);

export const DialogOverlay = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Overlay>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Overlay>
>(({ className, ...props }, ref) => (
  <DialogPrimitive.Overlay
    ref={ref}
    className={cn("fixed inset-0 z-50 bg-black/80 data-[state=open]:animate-in data-[state=closed]:animate-out", className)}
    {...props}
  />
));
DialogOverlay.displayName = DialogPrimitive.Overlay.displayName;

export const DialogContent = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Content>
>(({ className, children, ...props }, ref) => (
  <DialogPortal>
    <DialogOverlay />
    <DialogPrimitive.Content
      ref={ref}
      className={cn(
        "fixed left-1/2 top-1/2 z-50 grid w-full max-w-lg -translate-x-1/2 -translate-y-1/2 gap-4 border bg-background p-6 shadow-lg duration-200 sm:rounded-lg",
        className,
      )}
      {...props}
    >
      {children}
      <DialogPrimitive.Close className="absolute right-4 top-4 rounded-sm opacity-70 ring-offset-background transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:pointer-events-none">
        <X className="h-4 w-4" />
        <span className="sr-only">Close</span>
      </DialogPrimitive.Close>
    </DialogPrimitive.Content>
  </DialogPortal>
));
DialogContent.displayName = DialogPrimitive.Content.displayName;

export const DialogHeader = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cn("flex flex-col space-y-1.5 text-center sm:text-left", className)} {...props} />
);

export const DialogFooter = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cn("flex flex-col-reverse sm:flex-row sm:justify-end sm:space-x-2", className)} {...props} />
);

export const DialogTitle = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Title>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Title>
>(({ className, ...props }, ref) => (
  <DialogPrimitive.Title ref={ref} className={cn("text-lg font-semibold leading-none tracking-tight", className)} {...props} />
));
DialogTitle.displayName = DialogPrimitive.Title.displayName;

export const DialogDescription = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Description>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Description>
>(({ className, ...props }, ref) => (
  <DialogPrimitive.Description ref={ref} className={cn("text-sm text-muted-foreground", className)} {...props} />
));
DialogDescription.displayName = DialogPrimitive.Description.displayName;
```

`src/toolcrate/web/frontend/src/components/ui/tabs.tsx`:

```tsx
import * as React from "react";
import * as TabsPrimitive from "@radix-ui/react-tabs";
import { cn } from "@/lib/cn";

export const Tabs = TabsPrimitive.Root;

export const TabsList = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.List>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.List>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.List
    ref={ref}
    className={cn("inline-flex h-9 items-center justify-center rounded-lg bg-muted p-1 text-muted-foreground", className)}
    {...props}
  />
));
TabsList.displayName = TabsPrimitive.List.displayName;

export const TabsTrigger = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Trigger>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Trigger>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.Trigger
    ref={ref}
    className={cn(
      "inline-flex items-center justify-center whitespace-nowrap rounded-md px-3 py-1 text-sm font-medium transition-all data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow",
      className,
    )}
    {...props}
  />
));
TabsTrigger.displayName = TabsPrimitive.Trigger.displayName;

export const TabsContent = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Content>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.Content ref={ref} className={cn("mt-2 focus-visible:outline-none", className)} {...props} />
));
TabsContent.displayName = TabsPrimitive.Content.displayName;
```

`src/toolcrate/web/frontend/src/components/ui/table.tsx`:

```tsx
import * as React from "react";
import { cn } from "@/lib/cn";

export const Table = React.forwardRef<HTMLTableElement, React.HTMLAttributes<HTMLTableElement>>(
  ({ className, ...props }, ref) => (
    <div className="relative w-full overflow-auto">
      <table ref={ref} className={cn("w-full caption-bottom text-sm", className)} {...props} />
    </div>
  ),
);
Table.displayName = "Table";

export const TableHeader = React.forwardRef<HTMLTableSectionElement, React.HTMLAttributes<HTMLTableSectionElement>>(
  ({ className, ...props }, ref) => <thead ref={ref} className={cn("[&_tr]:border-b", className)} {...props} />,
);
TableHeader.displayName = "TableHeader";

export const TableBody = React.forwardRef<HTMLTableSectionElement, React.HTMLAttributes<HTMLTableSectionElement>>(
  ({ className, ...props }, ref) => <tbody ref={ref} className={cn("[&_tr:last-child]:border-0", className)} {...props} />,
);
TableBody.displayName = "TableBody";

export const TableRow = React.forwardRef<HTMLTableRowElement, React.HTMLAttributes<HTMLTableRowElement>>(
  ({ className, ...props }, ref) => (
    <tr ref={ref} className={cn("border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted", className)} {...props} />
  ),
);
TableRow.displayName = "TableRow";

export const TableHead = React.forwardRef<HTMLTableCellElement, React.ThHTMLAttributes<HTMLTableCellElement>>(
  ({ className, ...props }, ref) => (
    <th ref={ref} className={cn("h-10 px-2 text-left align-middle font-medium text-muted-foreground", className)} {...props} />
  ),
);
TableHead.displayName = "TableHead";

export const TableCell = React.forwardRef<HTMLTableCellElement, React.TdHTMLAttributes<HTMLTableCellElement>>(
  ({ className, ...props }, ref) => (
    <td ref={ref} className={cn("p-2 align-middle", className)} {...props} />
  ),
);
TableCell.displayName = "TableCell";
```

- [ ] **Step 6: Verify build**

Run from `src/toolcrate/web/frontend/`:

```bash
npm run typecheck
npm run lint
npm run build
```

Expected: all three commands succeed.

- [ ] **Step 7: Commit**

```bash
git add src/toolcrate/web/frontend/tailwind.config.ts src/toolcrate/web/frontend/postcss.config.js src/toolcrate/web/frontend/src/lib/cn.ts src/toolcrate/web/frontend/src/components/ui src/toolcrate/web/frontend/src/styles/globals.css src/toolcrate/web/frontend/package.json src/toolcrate/web/frontend/package-lock.json
git commit -m "feat(frontend): tailwind + shadcn-style ui primitives (button/input/dialog/tabs/table/badge/card)"
```

---

## Task 8: API client (fetch wrapper, RFC 7807, OpenAPI types)

**Files (new):**
- `src/api/client.ts`
- `src/api/keys.ts`
- `scripts/gen-api.ts`
- `src/api/types.ts` (generated, committed)
- `__tests__/client.test.ts`
- `src/test/setup.ts`
- `src/test/msw-handlers.ts`

- [ ] **Step 1: Write the OpenAPI codegen script**

`src/toolcrate/web/frontend/scripts/gen-api.ts`:

```ts
#!/usr/bin/env tsx
/**
 * Regenerate src/api/types.ts from the running backend's OpenAPI document.
 *
 * Usage: TOOLCRATE_API_BASE=http://127.0.0.1:48721 npm run gen:api
 */
import openapiTS, { astToString } from "openapi-typescript";
import { writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const base = process.env.TOOLCRATE_API_BASE ?? "http://127.0.0.1:48721";
const url = new URL("/api/openapi.json", base);

const ast = await openapiTS(url);
const out = astToString(ast);
const target = path.join(__dirname, "..", "src", "api", "types.ts");
await writeFile(target, "/* eslint-disable */\n/* prettier-ignore */\n" + out);
console.log(`wrote ${target}`);
```

- [ ] **Step 2: Generate the initial types file**

In one shell, start the backend: `toolcrate serve --port 48721`.

In another shell, from `src/toolcrate/web/frontend/`:

```bash
npm run gen:api
```

If `gen:api` fails because the backend is not running, manually create `src/toolcrate/web/frontend/src/api/types.ts` with this minimal placeholder while still making generation the source of truth going forward:

```ts
/* eslint-disable */
/* prettier-ignore */
// Generated placeholder. Run `npm run gen:api` against a running backend to regenerate.
export type paths = Record<string, never>;
export type components = { schemas: Record<string, never> };
```

Either way, the file must exist before the next step.

- [ ] **Step 3: Write the failing client test**

`src/toolcrate/web/frontend/src/test/setup.ts`:

```ts
import "@testing-library/jest-dom/vitest";
import { afterAll, afterEach, beforeAll } from "vitest";
import { server } from "./msw-handlers";

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

`src/toolcrate/web/frontend/src/test/msw-handlers.ts`:

```ts
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";

export const server = setupServer();
export { http, HttpResponse };
```

`src/toolcrate/web/frontend/__tests__/client.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { ApiError, apiFetch } from "@/api/client";
import { server, http, HttpResponse } from "@/test/msw-handlers";

describe("apiFetch", () => {
  it("returns parsed JSON on 2xx", async () => {
    server.use(
      http.get("/api/v1/lists", () => HttpResponse.json({ items: [], total: 0, limit: 100, offset: 0 })),
    );
    const data = await apiFetch<{ total: number }>("/api/v1/lists");
    expect(data.total).toBe(0);
  });

  it("returns null on 204", async () => {
    server.use(http.delete("/api/v1/lists/1", () => new HttpResponse(null, { status: 204 })));
    const data = await apiFetch<null>("/api/v1/lists/1", { method: "DELETE" });
    expect(data).toBeNull();
  });

  it("throws ApiError with parsed RFC 7807 body", async () => {
    server.use(
      http.post("/api/v1/lists/preview", () =>
        HttpResponse.json(
          { type: "about:blank#bad_url", title: "Bad URL", status: 400, detail: "unsupported source url", code: "bad_url" },
          { status: 400, headers: { "content-type": "application/problem+json" } },
        ),
      ),
    );
    await expect(
      apiFetch("/api/v1/lists/preview", { method: "POST", body: JSON.stringify({}) }),
    ).rejects.toMatchObject({ status: 400, code: "bad_url", title: "Bad URL" });
  });

  it("throws generic ApiError on non-JSON 5xx", async () => {
    server.use(http.get("/api/v1/jobs", () => new HttpResponse("oops", { status: 500 })));
    let caught: unknown;
    try {
      await apiFetch("/api/v1/jobs");
    } catch (e) {
      caught = e;
    }
    expect(caught).toBeInstanceOf(ApiError);
    expect((caught as ApiError).status).toBe(500);
  });

  it("sends credentials and JSON content-type by default", async () => {
    let capturedRequest: Request | undefined;
    server.use(
      http.post("/api/v1/lists", async ({ request }) => {
        capturedRequest = request;
        return HttpResponse.json({ id: 1 }, { status: 201 });
      }),
    );
    await apiFetch("/api/v1/lists", { method: "POST", body: JSON.stringify({ name: "x" }) });
    expect(capturedRequest?.headers.get("content-type")).toBe("application/json");
    expect(capturedRequest?.credentials).toBe("include");
  });
});
```

- [ ] **Step 4: Run; confirm fail**

From `src/toolcrate/web/frontend/`:

```bash
npm run test -- --run __tests__/client.test.ts
```

Expected: tests fail (`@/api/client` import not found).

- [ ] **Step 5: Implement the client**

`src/toolcrate/web/frontend/src/api/client.ts`:

```ts
export interface ProblemJson {
  type?: string;
  title?: string;
  status?: number;
  detail?: string;
  code?: string;
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string | undefined;
  readonly title: string | undefined;
  readonly detail: string | undefined;
  readonly raw: unknown;

  constructor(status: number, body: ProblemJson | string | undefined) {
    const title = typeof body === "object" && body ? body.title : undefined;
    const detail = typeof body === "object" && body ? body.detail : undefined;
    super(`${status} ${title ?? "request failed"}${detail ? `: ${detail}` : ""}`);
    this.name = "ApiError";
    this.status = status;
    this.code = typeof body === "object" && body ? body.code : undefined;
    this.title = title;
    this.detail = detail;
    this.raw = body;
  }
}

export interface ApiFetchOptions extends Omit<RequestInit, "body"> {
  body?: BodyInit | null;
}

export async function apiFetch<T = unknown>(path: string, options: ApiFetchOptions = {}): Promise<T> {
  const headers = new Headers(options.headers ?? {});
  if (options.body && !headers.has("content-type")) {
    headers.set("content-type", "application/json");
  }
  if (!headers.has("accept")) {
    headers.set("accept", "application/json");
  }

  const resp = await fetch(path, {
    ...options,
    headers,
    credentials: options.credentials ?? "include",
  });

  if (resp.status === 204) {
    return null as T;
  }

  const contentType = resp.headers.get("content-type") ?? "";
  const isJson = contentType.includes("json");
  const body = isJson ? await resp.json().catch(() => undefined) : await resp.text().catch(() => "");

  if (!resp.ok) {
    throw new ApiError(resp.status, body as ProblemJson | string | undefined);
  }
  return body as T;
}
```

- [ ] **Step 6: Write the query-key factory**

`src/toolcrate/web/frontend/src/api/keys.ts`:

```ts
export const queryKeys = {
  lists: { all: ["lists"] as const, byId: (id: number) => ["lists", id] as const },
  tracks: (listId: number, status?: string) => (status ? (["lists", listId, "tracks", { status }] as const) : (["lists", listId, "tracks"] as const)),
  jobs: { all: ["jobs"] as const, list: (filters: Record<string, unknown>) => ["jobs", filters] as const, byId: (id: number) => ["jobs", id] as const },
  preview: (url: string) => ["preview", url] as const,
};
```

- [ ] **Step 7: Run tests; confirm pass**

```bash
npm run test -- --run __tests__/client.test.ts
```

Expected: all 5 tests PASS.

- [ ] **Step 8: Commit**

```bash
git add src/toolcrate/web/frontend/src/api/client.ts src/toolcrate/web/frontend/src/api/keys.ts src/toolcrate/web/frontend/src/api/types.ts src/toolcrate/web/frontend/scripts/gen-api.ts src/toolcrate/web/frontend/__tests__/client.test.ts src/toolcrate/web/frontend/src/test
git commit -m "feat(frontend): typed fetch client with RFC 7807 error parsing + query keys"
```

---

## Task 9: SSE provider + query invalidator

**Files:**
- Create: `src/api/sse.ts`
- Create: `src/hooks/useSseInvalidation.ts`
- Create: `src/components/LiveBadge.tsx`
- Create: `__tests__/sse.test.ts`

- [ ] **Step 1: Write the failing SSE test**

`src/toolcrate/web/frontend/__tests__/sse.test.ts`:

```ts
import { describe, it, expect, vi, beforeEach } from "vitest";
import { dispatchSseEvent, type SseEvent } from "@/api/sse";

const invalidate = vi.fn();
const queryClient = { invalidateQueries: invalidate } as unknown as import("@tanstack/react-query").QueryClient;

beforeEach(() => invalidate.mockReset());

function ev(name: string, data: unknown): SseEvent {
  return { name, data };
}

describe("dispatchSseEvent", () => {
  it("invalidates lists on list.created", () => {
    dispatchSseEvent(queryClient, ev("list.created", { id: 1 }));
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["lists"] });
  });

  it("invalidates lists + specific list on list.updated", () => {
    dispatchSseEvent(queryClient, ev("list.updated", { id: 7 }));
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["lists"] });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["lists", 7] });
  });

  it("invalidates jobs and source list on job.update with source_list_id", () => {
    dispatchSseEvent(queryClient, ev("job.update", { id: 9, source_list_id: 42 }));
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["jobs"] });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["lists", 42] });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["lists", 42, "tracks"] });
  });

  it("invalidates tracks on track.updated", () => {
    dispatchSseEvent(queryClient, ev("track.updated", { source_list_id: 3 }));
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["lists", 3, "tracks"] });
  });

  it("ignores unknown event types", () => {
    dispatchSseEvent(queryClient, ev("mystery.thing", {}));
    expect(invalidate).not.toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run; confirm fail**

```bash
npm run test -- --run __tests__/sse.test.ts
```

Expected: import error for `@/api/sse`.

- [ ] **Step 3: Implement the dispatcher and provider**

`src/toolcrate/web/frontend/src/api/sse.ts`:

```ts
import type { QueryClient } from "@tanstack/react-query";
import { queryKeys } from "./keys";

export interface SseEvent {
  name: string;
  data: unknown;
}

export function dispatchSseEvent(client: QueryClient, event: SseEvent): void {
  const payload = (event.data ?? {}) as { id?: number; source_list_id?: number };
  switch (event.name) {
    case "list.created":
    case "list.deleted":
      client.invalidateQueries({ queryKey: queryKeys.lists.all });
      return;
    case "list.updated":
      client.invalidateQueries({ queryKey: queryKeys.lists.all });
      if (payload.id !== undefined) {
        client.invalidateQueries({ queryKey: queryKeys.lists.byId(payload.id) });
      }
      return;
    case "job.created":
    case "job.update":
    case "job.finished":
      client.invalidateQueries({ queryKey: queryKeys.jobs.all });
      if (payload.source_list_id !== undefined) {
        client.invalidateQueries({ queryKey: queryKeys.lists.byId(payload.source_list_id) });
        client.invalidateQueries({ queryKey: queryKeys.tracks(payload.source_list_id) });
      }
      return;
    case "track.updated":
      if (payload.source_list_id !== undefined) {
        client.invalidateQueries({ queryKey: queryKeys.tracks(payload.source_list_id) });
      }
      return;
    default:
      return;
  }
}

export interface LogEvent {
  job_id: number;
  line: string;
  ts: string;
}

export function isLogAppend(event: SseEvent): event is { name: "log.append"; data: LogEvent } {
  return event.name === "log.append";
}
```

`src/toolcrate/web/frontend/src/hooks/useSseInvalidation.ts`:

```ts
import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { dispatchSseEvent, isLogAppend, type SseEvent } from "@/api/sse";

type LogListener = (line: string, ts: string) => void;
const logListeners: Map<number, Set<LogListener>> = new Map();

export function subscribeJobLog(jobId: number, listener: LogListener): () => void {
  let bucket = logListeners.get(jobId);
  if (!bucket) {
    bucket = new Set();
    logListeners.set(jobId, bucket);
  }
  bucket.add(listener);
  return () => {
    bucket?.delete(listener);
    if (bucket && bucket.size === 0) logListeners.delete(jobId);
  };
}

export function useSseInvalidation(): { live: boolean } {
  const queryClient = useQueryClient();
  const [live, setLive] = useState(false);
  const sourceRef = useRef<EventSource | null>(null);
  const retryRef = useRef(0);

  useEffect(() => {
    let cancelled = false;

    const connect = () => {
      if (cancelled) return;
      const es = new EventSource("/api/v1/events");
      sourceRef.current = es;

      es.onopen = () => {
        retryRef.current = 0;
        setLive(true);
      };
      es.onerror = () => {
        setLive(false);
        es.close();
        if (cancelled) return;
        const delay = Math.min(30_000, 500 * 2 ** retryRef.current++);
        setTimeout(connect, delay);
      };

      const handle = (name: string, data: unknown) => {
        const event: SseEvent = { name, data };
        dispatchSseEvent(queryClient, event);
        if (isLogAppend(event)) {
          const log = event.data;
          const bucket = logListeners.get(log.job_id);
          bucket?.forEach((l) => l(log.line, log.ts));
        }
      };

      const wire = (name: string) =>
        es.addEventListener(name, (msg) => {
          try {
            handle(name, JSON.parse((msg as MessageEvent<string>).data));
          } catch {
            handle(name, undefined);
          }
        });

      [
        "list.created",
        "list.updated",
        "list.deleted",
        "job.created",
        "job.update",
        "job.finished",
        "track.updated",
        "log.append",
      ].forEach(wire);
    };

    connect();
    return () => {
      cancelled = true;
      sourceRef.current?.close();
    };
  }, [queryClient]);

  return { live };
}
```

`src/toolcrate/web/frontend/src/components/LiveBadge.tsx`:

```tsx
import { Badge } from "@/components/ui/badge";

export function LiveBadge({ live }: { live: boolean }) {
  return (
    <Badge variant={live ? "success" : "warning"} className="text-[10px] uppercase tracking-wider">
      {live ? "live" : "reconnecting"}
    </Badge>
  );
}
```

- [ ] **Step 4: Run tests; confirm pass**

```bash
npm run test -- --run __tests__/sse.test.ts
```

Expected: all 5 PASS.

- [ ] **Step 5: Commit**

```bash
git add src/toolcrate/web/frontend/src/api/sse.ts src/toolcrate/web/frontend/src/hooks/useSseInvalidation.ts src/toolcrate/web/frontend/src/components/LiveBadge.tsx src/toolcrate/web/frontend/__tests__/sse.test.ts
git commit -m "feat(frontend): SSE event dispatcher invalidates TanStack Query caches"
```

---

## Task 10: Router + layout + sidebar

**Files:**
- Replace: `src/App.tsx`
- Create: `src/router.tsx`
- Create: `src/components/Layout.tsx`
- Create: `src/components/Sidebar.tsx`
- Replace `src/pages/Dashboard.tsx`, `src/pages/SpotifyLists.tsx`, `src/pages/ListDetail.tsx`, `src/pages/Jobs.tsx` with stubs (filled in later tasks).

- [ ] **Step 1: Create page stubs**

`src/toolcrate/web/frontend/src/pages/Dashboard.tsx`:

```tsx
export default function Dashboard() {
  return <h1 className="text-2xl font-semibold">Dashboard</h1>;
}
```

`src/toolcrate/web/frontend/src/pages/SpotifyLists.tsx`:

```tsx
export default function SpotifyLists() {
  return <h1 className="text-2xl font-semibold">Spotify lists</h1>;
}
```

`src/toolcrate/web/frontend/src/pages/ListDetail.tsx`:

```tsx
import { useParams } from "react-router-dom";

export default function ListDetail() {
  const { id } = useParams();
  return <h1 className="text-2xl font-semibold">List {id}</h1>;
}
```

`src/toolcrate/web/frontend/src/pages/Jobs.tsx`:

```tsx
export default function Jobs() {
  return <h1 className="text-2xl font-semibold">Jobs</h1>;
}
```

- [ ] **Step 2: Write the Sidebar**

`src/toolcrate/web/frontend/src/components/Sidebar.tsx`:

```tsx
import { NavLink } from "react-router-dom";
import { LayoutDashboard, ListMusic, Briefcase } from "lucide-react";
import { cn } from "@/lib/cn";

const items = [
  { to: "/app", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/app/sources/spotify", label: "Spotify lists", icon: ListMusic },
  { to: "/app/jobs", label: "Jobs", icon: Briefcase },
];

export function Sidebar() {
  return (
    <aside className="w-56 shrink-0 border-r border-border bg-card/40">
      <div className="px-4 py-4 text-lg font-semibold tracking-tight">toolcrate</div>
      <nav className="flex flex-col gap-1 px-2">
        {items.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors",
                isActive ? "bg-accent text-accent-foreground" : "text-muted-foreground hover:bg-accent/50 hover:text-foreground",
              )
            }
          >
            <Icon className="h-4 w-4" />
            {label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
```

- [ ] **Step 3: Write the Layout**

`src/toolcrate/web/frontend/src/components/Layout.tsx`:

```tsx
import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { LiveBadge } from "./LiveBadge";
import { useSseInvalidation } from "@/hooks/useSseInvalidation";
import { Toaster } from "sonner";

export function Layout() {
  const { live } = useSseInvalidation();
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-12 items-center justify-end border-b border-border px-4">
          <LiveBadge live={live} />
        </header>
        <main className="min-w-0 flex-1 p-6">
          <Outlet />
        </main>
      </div>
      <Toaster richColors position="top-right" />
    </div>
  );
}
```

- [ ] **Step 4: Write the router + provider in `App.tsx`**

`src/toolcrate/web/frontend/src/router.tsx`:

```tsx
import { createBrowserRouter, Navigate } from "react-router-dom";
import { Layout } from "@/components/Layout";
import Dashboard from "@/pages/Dashboard";
import SpotifyLists from "@/pages/SpotifyLists";
import ListDetail from "@/pages/ListDetail";
import Jobs from "@/pages/Jobs";

export const router = createBrowserRouter([
  {
    path: "/app",
    element: <Layout />,
    children: [
      { index: true, element: <Dashboard /> },
      { path: "sources/spotify", element: <SpotifyLists /> },
      { path: "lists/:id", element: <ListDetail /> },
      { path: "jobs", element: <Jobs /> },
      { path: "*", element: <Navigate to="/app" replace /> },
    ],
  },
  { path: "/", element: <Navigate to="/app" replace /> },
  { path: "*", element: <Navigate to="/app" replace /> },
]);
```

Replace `src/toolcrate/web/frontend/src/App.tsx`:

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider } from "react-router-dom";
import { useState } from "react";
import { router } from "./router";

export default function App() {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: { staleTime: 5_000, refetchOnWindowFocus: false },
        },
      }),
  );
  return (
    <QueryClientProvider client={client}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  );
}
```

- [ ] **Step 5: Build + smoke**

```bash
npm run typecheck
npm run lint
npm run build
```

Expected: all three succeed.

Run `toolcrate serve --port 48721` and visit `http://127.0.0.1:48721/app/`. Expected: sidebar with 3 links, Dashboard heading, "live"/"reconnecting" badge in the header. Click each sidebar link — URL updates, no full reload, page heading changes.

- [ ] **Step 6: Commit**

```bash
git add src/toolcrate/web/frontend/src/App.tsx src/toolcrate/web/frontend/src/router.tsx src/toolcrate/web/frontend/src/components/Layout.tsx src/toolcrate/web/frontend/src/components/Sidebar.tsx src/toolcrate/web/frontend/src/pages
git commit -m "feat(frontend): app shell with router, sidebar, sse-backed layout"
```

---

## Task 11: Lists + tracks + jobs hooks (server-state queries)

**Files:**
- Create: `src/hooks/useLists.ts`
- Create: `src/hooks/useTracks.ts`
- Create: `src/hooks/useJobs.ts`
- Create: `src/hooks/usePreview.ts`

These hooks have no UI yet — pages call them in tasks 12–17. Tested implicitly through page tests.

- [ ] **Step 1: Define the resource shapes**

`src/toolcrate/web/frontend/src/api/resources.ts`:

```ts
// Manually-curated DTOs to keep pages decoupled from generated types.
// Refresh by hand when /api/openapi.json changes; the types in src/api/types.ts
// remain the source of truth for compile-time checking elsewhere.

export interface SourceList {
  id: number;
  name: string;
  source_type: "spotify_playlist" | "youtube_djset" | "manual";
  source_url: string;
  external_id: string;
  download_path: string;
  enabled: boolean;
  sync_interval: string;
  last_synced_at: string | null;
  last_sync_status: string;
  last_error: string | null;
  oauth_account_id: number | null;
  metadata_json: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface TrackEntry {
  id: number;
  source_list_id: number;
  position: number;
  artist: string | null;
  title: string | null;
  album: string | null;
  duration_sec: number | null;
  isrc: string | null;
  spotify_track_id: string | null;
  download_status: "pending" | "queued" | "downloading" | "done" | "failed" | "skipped";
  first_seen_at: string;
  last_seen_at: string;
}

export interface Job {
  id: number;
  type: "sync_list" | "recognize_djset" | "download_track" | "library_scan";
  state: "pending" | "running" | "success" | "failed" | "cancelled";
  priority: number;
  source_list_id: number | null;
  attempts: number;
  max_attempts: number;
  scheduled_for: string;
  started_at: string | null;
  finished_at: string | null;
  progress_json: { current?: number; total?: number; message?: string };
  error: string | null;
}

export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface ListPreview {
  source_type: "spotify_playlist";
  external_id: string;
  name: string;
  owner: string;
  total_tracks: number;
  art_url: string | null;
}
```

- [ ] **Step 2: Write `useLists.ts`**

```ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/api/client";
import { queryKeys } from "@/api/keys";
import type { Page, SourceList } from "@/api/resources";

export function useLists(filter: { source_type?: string } = {}) {
  const qs = filter.source_type ? `?source_type=${encodeURIComponent(filter.source_type)}` : "";
  return useQuery({
    queryKey: [...queryKeys.lists.all, filter],
    queryFn: () => apiFetch<Page<SourceList>>(`/api/v1/lists${qs}`),
  });
}

export function useList(id: number) {
  return useQuery({
    queryKey: queryKeys.lists.byId(id),
    queryFn: () => apiFetch<SourceList>(`/api/v1/lists/${id}`),
  });
}

export function useCreateList() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { name: string; source_url: string; source_type?: string; sync_interval?: string }) =>
      apiFetch<SourceList>("/api/v1/lists", { method: "POST", body: JSON.stringify(input) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.lists.all }),
  });
}

export function usePatchList(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (patch: Partial<Pick<SourceList, "name" | "download_path" | "sync_interval" | "enabled">>) =>
      apiFetch<SourceList>(`/api/v1/lists/${id}`, { method: "PATCH", body: JSON.stringify(patch) }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.lists.all });
      qc.invalidateQueries({ queryKey: queryKeys.lists.byId(id) });
    },
  });
}

export function useTriggerSync(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => apiFetch<{ job_id: number }>(`/api/v1/lists/${id}/sync`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.jobs.all }),
  });
}
```

- [ ] **Step 3: Write `useTracks.ts`**

```ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/api/client";
import { queryKeys } from "@/api/keys";
import type { Page, TrackEntry } from "@/api/resources";

export function useTracks(listId: number, status?: string) {
  const qs = status ? `?status=${encodeURIComponent(status)}&limit=2000` : "?limit=2000";
  return useQuery({
    queryKey: queryKeys.tracks(listId, status),
    queryFn: () => apiFetch<Page<TrackEntry>>(`/api/v1/lists/${listId}/tracks${qs}`),
    enabled: Number.isFinite(listId),
  });
}

export function useRetryTrack(listId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (trackId: number) =>
      apiFetch<{ job_id: number }>(`/api/v1/lists/${listId}/tracks/${trackId}/download`, { method: "POST" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.tracks(listId) });
      qc.invalidateQueries({ queryKey: queryKeys.jobs.all });
    },
  });
}

export function useSkipTrack(listId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (trackId: number) =>
      apiFetch<TrackEntry>(`/api/v1/lists/${listId}/tracks/${trackId}/skip`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.tracks(listId) }),
  });
}
```

- [ ] **Step 4: Write `useJobs.ts`**

```ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/api/client";
import { queryKeys } from "@/api/keys";
import type { Job, Page } from "@/api/resources";

export interface JobFilter {
  state?: string;
  type?: string;
  list_id?: number;
  limit?: number;
  offset?: number;
}

export function useJobs(filter: JobFilter = {}) {
  const params = new URLSearchParams();
  Object.entries(filter).forEach(([k, v]) => v !== undefined && v !== "" && params.set(k, String(v)));
  const qs = params.toString() ? `?${params.toString()}` : "";
  return useQuery({
    queryKey: queryKeys.jobs.list(filter),
    queryFn: () => apiFetch<Page<Job>>(`/api/v1/jobs${qs}`),
  });
}

export function useJob(id: number) {
  return useQuery({
    queryKey: queryKeys.jobs.byId(id),
    queryFn: () => apiFetch<Job>(`/api/v1/jobs/${id}`),
  });
}

export function useCancelJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => apiFetch<Job>(`/api/v1/jobs/${id}/cancel`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.jobs.all }),
  });
}

export function useRetryJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => apiFetch<Job>(`/api/v1/jobs/${id}/retry`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.jobs.all }),
  });
}
```

- [ ] **Step 5: Write `usePreview.ts`**

```ts
import { useMutation } from "@tanstack/react-query";
import { apiFetch } from "@/api/client";
import type { ListPreview } from "@/api/resources";

export function usePreviewMutation() {
  return useMutation({
    mutationFn: (source_url: string) =>
      apiFetch<ListPreview>("/api/v1/lists/preview", {
        method: "POST",
        body: JSON.stringify({ source_url }),
      }),
  });
}
```

- [ ] **Step 6: Build**

```bash
npm run typecheck
npm run build
```

Expected: success.

- [ ] **Step 7: Commit**

```bash
git add src/toolcrate/web/frontend/src/api/resources.ts src/toolcrate/web/frontend/src/hooks
git commit -m "feat(frontend): tanstack query hooks for lists, tracks, jobs, preview"
```

---

## Task 12: Dashboard page

**Files:** Replace `src/pages/Dashboard.tsx`. Create `src/lib/format.ts`.

- [ ] **Step 1: Write `format.ts`**

```ts
export function fmtRelative(iso: string | null | undefined): string {
  if (!iso) return "never";
  const ms = Date.now() - new Date(iso).getTime();
  if (Number.isNaN(ms)) return "—";
  const s = Math.round(ms / 1000);
  if (s < 60) return `${s}s ago`;
  const m = Math.round(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.round(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.round(h / 24);
  return `${d}d ago`;
}

export function fmtDuration(seconds: number | null | undefined): string {
  if (!seconds || seconds <= 0) return "—";
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}
```

- [ ] **Step 2: Replace `Dashboard.tsx`**

```tsx
import { Link } from "react-router-dom";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { useLists } from "@/hooks/useLists";
import { useJobs } from "@/hooks/useJobs";
import { fmtRelative } from "@/lib/format";

export default function Dashboard() {
  const lists = useLists();
  const activeJobs = useJobs({ state: "running", limit: 50 });
  const pendingJobs = useJobs({ state: "pending", limit: 50 });
  const recentJobs = useJobs({ limit: 10 });

  const totalLists = lists.data?.total ?? 0;
  const activeCount = (activeJobs.data?.total ?? 0) + (pendingJobs.data?.total ?? 0);

  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
      <Card>
        <CardHeader>
          <CardTitle>Lists</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-3xl font-semibold">{totalLists}</div>
          <Link to="/app/sources/spotify" className="text-sm text-muted-foreground underline-offset-4 hover:underline">
            Manage Spotify lists
          </Link>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Active jobs</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-3xl font-semibold">{activeCount}</div>
          <Link to="/app/jobs?state=running" className="text-sm text-muted-foreground underline-offset-4 hover:underline">
            View running jobs
          </Link>
        </CardContent>
      </Card>

      <Card className="md:col-span-3">
        <CardHeader>
          <CardTitle>Recent activity</CardTitle>
        </CardHeader>
        <CardContent className="text-sm">
          {recentJobs.data?.items.length ? (
            <ul className="divide-y divide-border">
              {recentJobs.data.items.map((j) => (
                <li key={j.id} className="flex items-center justify-between py-2">
                  <span className="font-mono text-xs">{j.type}</span>
                  <span className="text-muted-foreground">{j.state}</span>
                  <span className="text-muted-foreground">{fmtRelative(j.finished_at ?? j.started_at)}</span>
                </li>
              ))}
            </ul>
          ) : (
            <div className="text-muted-foreground">No recent activity yet.</div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
```

- [ ] **Step 3: Build + smoke**

```bash
npm run typecheck
npm run build
```

Visit `http://127.0.0.1:48721/app/` after restarting `toolcrate serve`. Expected: three cards, populated counts, empty activity table on a fresh DB.

- [ ] **Step 4: Commit**

```bash
git add src/toolcrate/web/frontend/src/pages/Dashboard.tsx src/toolcrate/web/frontend/src/lib/format.ts
git commit -m "feat(frontend): dashboard skeleton with lists/jobs counts and recent activity"
```

---

## Task 13: AddListDialog (paste URL → preview → submit)

**Files:**
- Create: `src/components/AddListDialog.tsx`
- Create: `__tests__/AddListDialog.test.tsx`

- [ ] **Step 1: Write the failing test**

`src/toolcrate/web/frontend/__tests__/AddListDialog.test.tsx`:

```tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { server, http, HttpResponse } from "@/test/msw-handlers";
import { AddListDialog } from "@/components/AddListDialog";

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <QueryClientProvider client={qc}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>
  );
}

describe("AddListDialog", () => {
  it("autofills name from preview after URL paste", async () => {
    server.use(
      http.post("/api/v1/lists/preview", () =>
        HttpResponse.json({
          source_type: "spotify_playlist",
          external_id: "abc",
          name: "Beach Vibes",
          owner: "spotify",
          total_tracks: 12,
          art_url: null,
        }),
      ),
    );
    render(wrap(<AddListDialog open onClose={vi.fn()} />));

    const url = await screen.findByLabelText(/playlist url/i);
    await userEvent.type(url, "https://open.spotify.com/playlist/abc");

    const name = await screen.findByLabelText(/name/i);
    await waitFor(() => expect(name).toHaveValue("Beach Vibes"));
    expect(screen.getByText(/12 tracks/i)).toBeInTheDocument();
  });

  it("shows error when preview returns 400", async () => {
    server.use(
      http.post("/api/v1/lists/preview", () =>
        HttpResponse.json(
          { type: "about:blank#bad_url", title: "Bad URL", status: 400, detail: "unsupported", code: "bad_url" },
          { status: 400, headers: { "content-type": "application/problem+json" } },
        ),
      ),
    );
    render(wrap(<AddListDialog open onClose={vi.fn()} />));
    await userEvent.type(await screen.findByLabelText(/playlist url/i), "https://nope.example/x");
    expect(await screen.findByText(/unsupported|bad url/i)).toBeInTheDocument();
  });

  it("submits and calls onClose on success", async () => {
    let captured: Request | undefined;
    server.use(
      http.post("/api/v1/lists/preview", () =>
        HttpResponse.json({
          source_type: "spotify_playlist",
          external_id: "abc",
          name: "Beach Vibes",
          owner: "spotify",
          total_tracks: 12,
          art_url: null,
        }),
      ),
      http.post("/api/v1/lists", async ({ request }) => {
        captured = request.clone();
        return HttpResponse.json({ id: 7 }, { status: 201 });
      }),
    );
    const onClose = vi.fn();
    render(wrap(<AddListDialog open onClose={onClose} />));

    await userEvent.type(await screen.findByLabelText(/playlist url/i), "https://open.spotify.com/playlist/abc");
    await waitFor(() => expect(screen.getByLabelText(/name/i)).toHaveValue("Beach Vibes"));
    await userEvent.click(screen.getByRole("button", { name: /create/i }));

    await waitFor(() => expect(onClose).toHaveBeenCalledWith({ id: 7 }));
    const body = captured ? await captured.json() : {};
    expect(body).toMatchObject({
      name: "Beach Vibes",
      source_url: "https://open.spotify.com/playlist/abc",
      source_type: "spotify_playlist",
    });
  });
});
```

- [ ] **Step 2: Run; confirm fail**

```bash
npm run test -- --run __tests__/AddListDialog.test.tsx
```

Expected: import error.

- [ ] **Step 3: Implement the dialog**

`src/toolcrate/web/frontend/src/components/AddListDialog.tsx`:

```tsx
import { useEffect, useMemo, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useCreateList } from "@/hooks/useLists";
import { usePreviewMutation } from "@/hooks/usePreview";
import { ApiError } from "@/api/client";
import type { ListPreview } from "@/api/resources";

const URL_RE = /^https?:\/\/open\.spotify\.com\/playlist\/[A-Za-z0-9]+/;

const schema = z.object({
  source_url: z.string().regex(URL_RE, "Must be an open.spotify.com playlist URL"),
  name: z.string().min(1, "Required"),
  sync_interval: z.string().min(1),
});
type Form = z.infer<typeof schema>;

export interface AddListDialogProps {
  open: boolean;
  onClose: (created?: { id: number }) => void;
}

export function AddListDialog({ open, onClose }: AddListDialogProps) {
  const { register, handleSubmit, watch, setValue, formState } = useForm<Form>({
    defaultValues: { source_url: "", name: "", sync_interval: "manual" },
  });
  const url = watch("source_url");
  const [preview, setPreview] = useState<ListPreview | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const previewMut = usePreviewMutation();
  const createMut = useCreateList();
  const debounceRef = useRef<number | undefined>(undefined);

  const validUrl = useMemo(() => URL_RE.test(url), [url]);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (!validUrl) {
      setPreview(null);
      setPreviewError(null);
      return;
    }
    debounceRef.current = window.setTimeout(async () => {
      try {
        const data = await previewMut.mutateAsync(url);
        setPreview(data);
        setPreviewError(null);
        setValue("name", data.name, { shouldValidate: true });
      } catch (e) {
        setPreview(null);
        setPreviewError(e instanceof ApiError ? e.detail ?? e.title ?? "preview failed" : "preview failed");
      }
    }, 300);
    return () => clearTimeout(debounceRef.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [url, validUrl]);

  const onSubmit = handleSubmit(async (form) => {
    const created = await createMut.mutateAsync({
      name: form.name,
      source_url: form.source_url,
      source_type: "spotify_playlist",
      sync_interval: form.sync_interval,
    });
    onClose({ id: created.id });
  });

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add Spotify list</DialogTitle>
        </DialogHeader>
        <form className="space-y-4" onSubmit={onSubmit}>
          <div className="space-y-1">
            <label className="text-sm" htmlFor="source_url">
              Playlist URL
            </label>
            <Input id="source_url" autoFocus {...register("source_url")} />
            {previewError && <p className="text-xs text-destructive">{previewError}</p>}
          </div>
          {preview && (
            <div className="rounded-md border border-border p-3 text-sm">
              <div className="font-medium">{preview.name}</div>
              <div className="text-muted-foreground">
                by {preview.owner} · {preview.total_tracks} tracks
              </div>
            </div>
          )}
          <div className="space-y-1">
            <label className="text-sm" htmlFor="name">
              Name
            </label>
            <Input id="name" {...register("name")} />
            {formState.errors.name && <p className="text-xs text-destructive">{formState.errors.name.message}</p>}
          </div>
          <div className="space-y-1">
            <label className="text-sm" htmlFor="sync_interval">
              Sync interval
            </label>
            <select
              id="sync_interval"
              className="h-9 w-full rounded-md border border-input bg-transparent px-2 text-sm"
              {...register("sync_interval")}
            >
              <option value="manual">manual</option>
              <option value="hourly">hourly</option>
              <option value="daily">daily</option>
            </select>
          </div>
          <DialogFooter>
            <Button type="button" variant="ghost" onClick={() => onClose()}>
              Cancel
            </Button>
            <Button type="submit" disabled={createMut.isPending || !validUrl || !!formState.errors.name}>
              {createMut.isPending ? "Creating…" : "Create"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
```

- [ ] **Step 4: Run tests; confirm pass**

```bash
npm run test -- --run __tests__/AddListDialog.test.tsx
```

Expected: all 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/toolcrate/web/frontend/src/components/AddListDialog.tsx src/toolcrate/web/frontend/__tests__/AddListDialog.test.tsx
git commit -m "feat(frontend): AddListDialog with debounced preview + name autofill"
```

---

## Task 14: Spotify Lists page (master/detail)

**Files:**
- Create: `src/components/StatusPill.tsx`
- Create: `src/components/ListMasterTable.tsx`
- Replace: `src/pages/SpotifyLists.tsx`

- [ ] **Step 1: Write the StatusPill**

`src/toolcrate/web/frontend/src/components/StatusPill.tsx`:

```tsx
import { Badge, type BadgeProps } from "@/components/ui/badge";

const SYNC_VARIANT: Record<string, BadgeProps["variant"]> = {
  ok: "success",
  error: "destructive",
  never: "secondary",
};

const TRACK_VARIANT: Record<string, BadgeProps["variant"]> = {
  done: "success",
  downloading: "default",
  queued: "secondary",
  pending: "outline",
  failed: "destructive",
  skipped: "secondary",
};

const JOB_VARIANT: Record<string, BadgeProps["variant"]> = {
  success: "success",
  running: "default",
  pending: "secondary",
  failed: "destructive",
  cancelled: "outline",
};

const VARIANTS = { sync: SYNC_VARIANT, track: TRACK_VARIANT, job: JOB_VARIANT };

export function StatusPill({ kind, value }: { kind: keyof typeof VARIANTS; value: string }) {
  const variant = VARIANTS[kind][value] ?? "outline";
  return <Badge variant={variant}>{value}</Badge>;
}
```

- [ ] **Step 2: Write `ListMasterTable.tsx`**

```tsx
import { Link } from "react-router-dom";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { StatusPill } from "./StatusPill";
import { fmtRelative } from "@/lib/format";
import type { SourceList } from "@/api/resources";

export function ListMasterTable({ items, selectedId }: { items: SourceList[]; selectedId?: number }) {
  if (items.length === 0) {
    return <div className="rounded-md border border-dashed border-border p-8 text-center text-muted-foreground">No lists yet. Click “Add Spotify list” to start.</div>;
  }
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Name</TableHead>
          <TableHead>Last sync</TableHead>
          <TableHead>Status</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {items.map((l) => (
          <TableRow key={l.id} data-state={selectedId === l.id ? "selected" : undefined}>
            <TableCell>
              <Link to={`/app/lists/${l.id}`} className="font-medium hover:underline">
                {l.name}
              </Link>
            </TableCell>
            <TableCell className="text-muted-foreground">{fmtRelative(l.last_synced_at)}</TableCell>
            <TableCell>
              <StatusPill kind="sync" value={l.last_sync_status} />
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
```

- [ ] **Step 3: Replace `SpotifyLists.tsx`**

```tsx
import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { useLists } from "@/hooks/useLists";
import { ListMasterTable } from "@/components/ListMasterTable";
import { AddListDialog } from "@/components/AddListDialog";

export default function SpotifyLists() {
  const { id } = useParams();
  const selectedId = id ? Number(id) : undefined;
  const navigate = useNavigate();
  const lists = useLists({ source_type: "spotify_playlist" });
  const [open, setOpen] = useState(false);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Spotify lists</h1>
        <Button onClick={() => setOpen(true)}>Add Spotify list</Button>
      </div>
      <ListMasterTable items={lists.data?.items ?? []} selectedId={selectedId} />
      {open && (
        <AddListDialog
          open
          onClose={(created) => {
            setOpen(false);
            if (created) navigate(`/app/lists/${created.id}`);
          }}
        />
      )}
    </div>
  );
}
```

- [ ] **Step 4: Build + smoke**

```bash
npm run typecheck
npm run build
```

Restart `toolcrate serve`, visit `http://127.0.0.1:48721/app/sources/spotify`. Expected: empty-state hint, "Add Spotify list" button opens dialog. Paste a public playlist URL — preview appears, name autofills, submit creates list and routes to `/app/lists/<id>` (the detail page is still a stub until Task 15).

- [ ] **Step 5: Commit**

```bash
git add src/toolcrate/web/frontend/src/components/StatusPill.tsx src/toolcrate/web/frontend/src/components/ListMasterTable.tsx src/toolcrate/web/frontend/src/pages/SpotifyLists.tsx
git commit -m "feat(frontend): spotify lists master view with add-list flow"
```

---

## Task 15: List detail — Tracks tab

**Files:**
- Create: `src/components/TrackTable.tsx`
- Replace: `src/pages/ListDetail.tsx`
- Create: `__tests__/TrackTable.test.tsx`

- [ ] **Step 1: Write the failing TrackTable test**

`src/toolcrate/web/frontend/__tests__/TrackTable.test.tsx`:

```tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TrackTable } from "@/components/TrackTable";
import type { TrackEntry } from "@/api/resources";

const t = (over: Partial<TrackEntry> = {}): TrackEntry => ({
  id: 1,
  source_list_id: 1,
  position: 1,
  artist: "A",
  title: "T",
  album: "Alb",
  duration_sec: 200,
  isrc: null,
  spotify_track_id: null,
  download_status: "pending",
  first_seen_at: "2026-04-30T00:00:00Z",
  last_seen_at: "2026-04-30T00:00:00Z",
  ...over,
});

describe("TrackTable", () => {
  it("renders rows with status pill", () => {
    render(<TrackTable items={[t({ id: 1, title: "Song A", download_status: "done" }), t({ id: 2, title: "Song B", download_status: "failed" })]} onRetry={vi.fn()} />);
    expect(screen.getByText("Song A")).toBeInTheDocument();
    expect(screen.getByText("Song B")).toBeInTheDocument();
    expect(screen.getByText("done")).toBeInTheDocument();
    expect(screen.getByText("failed")).toBeInTheDocument();
  });

  it("calls onRetry when retry clicked on failed row", async () => {
    const onRetry = vi.fn();
    render(<TrackTable items={[t({ id: 99, download_status: "failed" })]} onRetry={onRetry} />);
    await userEvent.click(screen.getByRole("button", { name: /retry/i }));
    expect(onRetry).toHaveBeenCalledWith(99);
  });

  it("does not show retry button on done rows", () => {
    render(<TrackTable items={[t({ id: 1, download_status: "done" })]} onRetry={vi.fn()} />);
    expect(screen.queryByRole("button", { name: /retry/i })).not.toBeInTheDocument();
  });

  it("renders empty state when no items", () => {
    render(<TrackTable items={[]} onRetry={vi.fn()} />);
    expect(screen.getByText(/no tracks yet/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run; confirm fail**

```bash
npm run test -- --run __tests__/TrackTable.test.tsx
```

Expected: import error.

- [ ] **Step 3: Implement TrackTable**

`src/toolcrate/web/frontend/src/components/TrackTable.tsx`:

```tsx
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { StatusPill } from "./StatusPill";
import { Button } from "@/components/ui/button";
import { fmtDuration } from "@/lib/format";
import type { TrackEntry } from "@/api/resources";

export function TrackTable({ items, onRetry }: { items: TrackEntry[]; onRetry: (id: number) => void }) {
  if (items.length === 0) {
    return <div className="rounded-md border border-dashed border-border p-8 text-center text-muted-foreground">No tracks yet. Trigger a sync to populate.</div>;
  }
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="w-12">#</TableHead>
          <TableHead>Artist</TableHead>
          <TableHead>Title</TableHead>
          <TableHead className="w-20">Duration</TableHead>
          <TableHead className="w-28">Status</TableHead>
          <TableHead className="w-24" />
        </TableRow>
      </TableHeader>
      <TableBody>
        {items.map((t) => (
          <TableRow key={t.id}>
            <TableCell className="text-muted-foreground">{t.position}</TableCell>
            <TableCell>{t.artist ?? "—"}</TableCell>
            <TableCell className="font-medium">{t.title ?? "—"}</TableCell>
            <TableCell className="text-muted-foreground">{fmtDuration(t.duration_sec)}</TableCell>
            <TableCell>
              <StatusPill kind="track" value={t.download_status} />
            </TableCell>
            <TableCell>
              {(t.download_status === "failed" || t.download_status === "skipped" || t.download_status === "pending") && (
                <Button size="sm" variant="outline" onClick={() => onRetry(t.id)}>
                  Retry
                </Button>
              )}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
```

- [ ] **Step 4: Run TrackTable tests; confirm pass**

```bash
npm run test -- --run __tests__/TrackTable.test.tsx
```

Expected: all 4 PASS.

- [ ] **Step 5: Replace `ListDetail.tsx` with the Tracks tab**

```tsx
import { useParams, Navigate } from "react-router-dom";
import { useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { TrackTable } from "@/components/TrackTable";
import { useList, useTriggerSync } from "@/hooks/useLists";
import { useTracks, useRetryTrack } from "@/hooks/useTracks";
import { fmtRelative } from "@/lib/format";
import { StatusPill } from "@/components/StatusPill";

const STATUS_OPTIONS = ["", "pending", "queued", "downloading", "done", "failed", "skipped"];

export default function ListDetail() {
  const { id } = useParams();
  const numericId = id ? Number(id) : NaN;
  if (!Number.isFinite(numericId)) return <Navigate to="/app/sources/spotify" replace />;

  const list = useList(numericId);
  const [statusFilter, setStatusFilter] = useState("");
  const tracks = useTracks(numericId, statusFilter || undefined);
  const sync = useTriggerSync(numericId);
  const retry = useRetryTrack(numericId);

  if (list.isLoading) return <div>Loading…</div>;
  if (list.error || !list.data) return <div className="text-destructive">List not found.</div>;

  return (
    <div className="space-y-4">
      <header className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">{list.data.name}</h1>
          <p className="text-sm text-muted-foreground">
            Last sync {fmtRelative(list.data.last_synced_at)} · <StatusPill kind="sync" value={list.data.last_sync_status} />
          </p>
        </div>
        <Button onClick={() => sync.mutate()} disabled={sync.isPending}>
          {sync.isPending ? "Queuing…" : "Sync now"}
        </Button>
      </header>
      <Tabs defaultValue="tracks">
        <TabsList>
          <TabsTrigger value="tracks">Tracks</TabsTrigger>
          <TabsTrigger value="history">History</TabsTrigger>
          <TabsTrigger value="settings">Settings</TabsTrigger>
        </TabsList>
        <TabsContent value="tracks" className="space-y-3">
          <div className="flex flex-wrap gap-2">
            {STATUS_OPTIONS.map((opt) => (
              <Button
                key={opt || "all"}
                size="sm"
                variant={statusFilter === opt ? "default" : "outline"}
                onClick={() => setStatusFilter(opt)}
              >
                {opt || "all"}
              </Button>
            ))}
          </div>
          <TrackTable items={tracks.data?.items ?? []} onRetry={(tid) => retry.mutate(tid)} />
        </TabsContent>
        <TabsContent value="history">
          <ListHistory listId={numericId} />
        </TabsContent>
        <TabsContent value="settings">
          <ListSettings listId={numericId} />
        </TabsContent>
      </Tabs>
    </div>
  );
}

// History + Settings are filled in by Tasks 16 + 17.
function ListHistory({ listId: _listId }: { listId: number }) {
  return <div className="text-muted-foreground">History tab — filled in by the next task.</div>;
}
function ListSettings({ listId: _listId }: { listId: number }) {
  return <div className="text-muted-foreground">Settings tab — filled in by the next task.</div>;
}
```

- [ ] **Step 6: Build + smoke**

```bash
npm run typecheck
npm run build
```

Restart server, navigate `/app/lists/<id>` for a list created via the Add dialog. Expected: header with name + last-sync info, three tabs, Tracks tab shows the empty-state message until sync populates rows. Click "Sync now" — UI dispatches POST `/sync`, header updates as SSE events arrive (state transitions visible in real time).

- [ ] **Step 7: Commit**

```bash
git add src/toolcrate/web/frontend/src/components/TrackTable.tsx src/toolcrate/web/frontend/__tests__/TrackTable.test.tsx src/toolcrate/web/frontend/src/pages/ListDetail.tsx
git commit -m "feat(frontend): list detail — tracks tab with status filters and retry"
```

---

## Task 16: List detail — History + Settings tabs

**Files:**
- Modify: `src/pages/ListDetail.tsx` (replace `ListHistory` and `ListSettings` stubs)
- Create: `src/components/JobLogPane.tsx`

- [ ] **Step 1: Write `JobLogPane.tsx`**

`src/toolcrate/web/frontend/src/components/JobLogPane.tsx`:

```tsx
import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { apiFetch } from "@/api/client";
import { subscribeJobLog } from "@/hooks/useSseInvalidation";

export function JobLogPane({ jobId }: { jobId: number }) {
  const [lines, setLines] = useState<string[]>([]);
  const [follow, setFollow] = useState(true);
  const ref = useRef<HTMLPreElement | null>(null);
  const offsetRef = useRef(0);

  useEffect(() => {
    let cancelled = false;
    setLines([]);
    offsetRef.current = 0;

    const loadInitial = async () => {
      try {
        const page = await apiFetch<{ lines: string[]; next_offset: number | null }>(
          `/api/v1/jobs/${jobId}/log?limit=2000`,
        );
        if (cancelled) return;
        setLines(page.lines);
        offsetRef.current = page.lines.length;
      } catch {
        // 404 etc. — fall through to the SSE feed
      }
    };
    loadInitial();

    const unsub = subscribeJobLog(jobId, (line) => {
      setLines((prev) => prev.concat(line));
    });

    return () => {
      cancelled = true;
      unsub();
    };
  }, [jobId]);

  useEffect(() => {
    if (follow && ref.current) {
      ref.current.scrollTop = ref.current.scrollHeight;
    }
  }, [lines, follow]);

  return (
    <div className="space-y-2">
      <div className="flex justify-end">
        <Button size="sm" variant={follow ? "default" : "outline"} onClick={() => setFollow((f) => !f)}>
          {follow ? "Following" : "Paused"}
        </Button>
      </div>
      <pre
        ref={ref}
        className="max-h-96 overflow-auto rounded-md border border-border bg-card p-3 font-mono text-xs leading-snug"
      >
        {lines.join("\n") || "(no log yet)"}
      </pre>
    </div>
  );
}
```

- [ ] **Step 2: Replace `ListHistory` and `ListSettings`**

In `src/pages/ListDetail.tsx`, replace the two stub functions at the bottom with full implementations. Keep all earlier code unchanged.

```tsx
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useJobs } from "@/hooks/useJobs";
import { usePatchList } from "@/hooks/useLists";
import { JobLogPane } from "@/components/JobLogPane";
import { useForm } from "react-hook-form";

function ListHistory({ listId }: { listId: number }) {
  const jobs = useJobs({ list_id: listId, limit: 50 });
  const [expanded, setExpanded] = useState<number | null>(null);

  if (!jobs.data) return <div className="text-muted-foreground">Loading…</div>;
  if (jobs.data.items.length === 0) return <div className="text-muted-foreground">No sync history yet.</div>;

  return (
    <ul className="space-y-2">
      {jobs.data.items.map((j) => (
        <li key={j.id} className="rounded-md border border-border">
          <button
            type="button"
            className="flex w-full items-center justify-between px-3 py-2 text-sm hover:bg-accent/40"
            onClick={() => setExpanded(expanded === j.id ? null : j.id)}
          >
            <span>
              <span className="font-mono text-xs">{j.type}</span>
              <span className="ml-2 text-muted-foreground">{j.state}</span>
            </span>
            <span className="text-xs text-muted-foreground">
              {j.started_at ?? j.scheduled_for}
            </span>
          </button>
          {expanded === j.id && (
            <div className="border-t border-border p-3">
              <JobLogPane jobId={j.id} />
            </div>
          )}
        </li>
      ))}
    </ul>
  );
}

interface SettingsForm {
  name: string;
  download_path: string;
  sync_interval: string;
  enabled: boolean;
}

function ListSettings({ listId }: { listId: number }) {
  const list = useList(listId);
  const patch = usePatchList(listId);
  const { register, handleSubmit, formState, reset } = useForm<SettingsForm>({
    values: list.data
      ? {
          name: list.data.name,
          download_path: list.data.download_path,
          sync_interval: list.data.sync_interval,
          enabled: list.data.enabled,
        }
      : undefined,
  });

  if (!list.data) return <div className="text-muted-foreground">Loading…</div>;

  const onSubmit = handleSubmit(async (form) => {
    await patch.mutateAsync(form);
    reset(form);
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Settings</CardTitle>
      </CardHeader>
      <CardContent>
        <form className="space-y-4 max-w-xl" onSubmit={onSubmit}>
          <Field label="Name" id="name">
            <Input id="name" {...register("name", { required: true })} />
          </Field>
          <Field label="Download path" id="download_path">
            <Input id="download_path" {...register("download_path", { required: true })} />
          </Field>
          <Field label="Sync interval" id="sync_interval">
            <select
              id="sync_interval"
              className="h-9 w-full rounded-md border border-input bg-transparent px-2 text-sm"
              {...register("sync_interval")}
            >
              <option value="manual">manual</option>
              <option value="hourly">hourly</option>
              <option value="daily">daily</option>
            </select>
          </Field>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" {...register("enabled")} /> Enabled (scheduled syncs)
          </label>
          <div className="flex gap-2">
            <Button type="submit" disabled={!formState.isDirty || patch.isPending}>
              {patch.isPending ? "Saving…" : "Save"}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

function Field({ label, id, children }: { label: string; id: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <label className="text-sm" htmlFor={id}>
        {label}
      </label>
      {children}
    </div>
  );
}
```

(Add `useState`, `useList` to the existing imports if not already present.)

- [ ] **Step 3: Build + smoke**

```bash
npm run typecheck
npm run build
```

Restart server, open a list. Expected: History tab shows past sync jobs, click expands and shows the log; Settings tab edits name/path/sync_interval/enabled and saves.

- [ ] **Step 4: Commit**

```bash
git add src/toolcrate/web/frontend/src/components/JobLogPane.tsx src/toolcrate/web/frontend/src/pages/ListDetail.tsx
git commit -m "feat(frontend): list detail — history (job log) + settings tabs"
```

---

## Task 17: Jobs page

**Files:**
- Replace: `src/pages/Jobs.tsx`
- Create: `__tests__/Jobs.test.tsx`

- [ ] **Step 1: Write the failing test**

`src/toolcrate/web/frontend/__tests__/Jobs.test.tsx`:

```tsx
import { describe, it, expect } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import Jobs from "@/pages/Jobs";
import { server, http, HttpResponse } from "@/test/msw-handlers";

function wrap(ui: React.ReactNode, initialEntries = ["/app/jobs"]) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={initialEntries}>{ui}</MemoryRouter>
    </QueryClientProvider>
  );
}

const job = (over: Partial<Record<string, unknown>> = {}) => ({
  id: 1,
  type: "sync_list",
  state: "running",
  priority: 0,
  source_list_id: 1,
  attempts: 1,
  max_attempts: 3,
  scheduled_for: "2026-04-30T00:00:00Z",
  started_at: "2026-04-30T00:00:00Z",
  finished_at: null,
  progress_json: { current: 5, total: 20 },
  error: null,
  ...over,
});

describe("Jobs page", () => {
  it("renders jobs from server", async () => {
    server.use(http.get("/api/v1/jobs", () => HttpResponse.json({ items: [job()], total: 1, limit: 100, offset: 0 })));
    render(wrap(<Jobs />));
    expect(await screen.findByText(/sync_list/)).toBeInTheDocument();
    expect(screen.getByText(/5 \/ 20/)).toBeInTheDocument();
  });

  it("shows Cancel only on running jobs", async () => {
    server.use(
      http.get("/api/v1/jobs", () =>
        HttpResponse.json({
          items: [job({ id: 1, state: "running" }), job({ id: 2, state: "success" })],
          total: 2,
          limit: 100,
          offset: 0,
        }),
      ),
    );
    render(wrap(<Jobs />));
    await screen.findByText(/sync_list/);
    const cancels = screen.getAllByRole("button", { name: /cancel/i });
    expect(cancels).toHaveLength(1);
  });

  it("filters by state via the state buttons", async () => {
    let lastUrl = "";
    server.use(
      http.get("/api/v1/jobs", ({ request }) => {
        lastUrl = request.url;
        return HttpResponse.json({ items: [], total: 0, limit: 100, offset: 0 });
      }),
    );
    render(wrap(<Jobs />));
    await waitFor(() => expect(lastUrl).toContain("/jobs"));
    await userEvent.click(screen.getByRole("button", { name: /^running$/i }));
    await waitFor(() => expect(lastUrl).toContain("state=running"));
  });
});
```

- [ ] **Step 2: Run; confirm fail**

```bash
npm run test -- --run __tests__/Jobs.test.tsx
```

Expected: page is still a stub, none of the assertions match.

- [ ] **Step 3: Replace `Jobs.tsx`**

```tsx
import { useSearchParams } from "react-router-dom";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { StatusPill } from "@/components/StatusPill";
import { useCancelJob, useJobs, useRetryJob } from "@/hooks/useJobs";
import type { Job } from "@/api/resources";

const STATES = ["", "pending", "running", "success", "failed", "cancelled"];
const TYPES = ["", "sync_list", "download_track", "library_scan", "recognize_djset"];

export default function Jobs() {
  const [params, setParams] = useSearchParams();
  const state = params.get("state") ?? "";
  const type = params.get("type") ?? "";

  const jobs = useJobs({ state: state || undefined, type: type || undefined, limit: 200 });
  const cancel = useCancelJob();
  const retry = useRetryJob();

  const setFilter = (key: "state" | "type", value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next, { replace: true });
  };

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Jobs</h1>
      <FilterRow label="State" value={state} options={STATES} onChange={(v) => setFilter("state", v)} />
      <FilterRow label="Type" value={type} options={TYPES} onChange={(v) => setFilter("type", v)} />
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-12">ID</TableHead>
            <TableHead>Type</TableHead>
            <TableHead>State</TableHead>
            <TableHead>Progress</TableHead>
            <TableHead>List</TableHead>
            <TableHead className="w-32" />
          </TableRow>
        </TableHeader>
        <TableBody>
          {jobs.data?.items.map((j: Job) => (
            <TableRow key={j.id}>
              <TableCell className="font-mono text-xs">{j.id}</TableCell>
              <TableCell className="font-mono text-xs">{j.type}</TableCell>
              <TableCell>
                <StatusPill kind="job" value={j.state} />
              </TableCell>
              <TableCell className="text-xs text-muted-foreground">
                {j.progress_json.total
                  ? `${j.progress_json.current ?? 0} / ${j.progress_json.total}`
                  : j.progress_json.message ?? "—"}
              </TableCell>
              <TableCell className="text-xs text-muted-foreground">{j.source_list_id ?? "—"}</TableCell>
              <TableCell>
                {j.state === "running" || j.state === "pending" ? (
                  <Button size="sm" variant="outline" onClick={() => cancel.mutate(j.id)}>
                    Cancel
                  </Button>
                ) : j.state === "failed" ? (
                  <Button size="sm" variant="outline" onClick={() => retry.mutate(j.id)}>
                    Retry
                  </Button>
                ) : null}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

function FilterRow({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: string[];
  onChange: (v: string) => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-2 text-sm">
      <span className="text-muted-foreground">{label}:</span>
      {options.map((opt) => (
        <Button
          key={opt || "all"}
          size="sm"
          variant={value === opt ? "default" : "outline"}
          onClick={() => onChange(opt)}
        >
          {opt || "all"}
        </Button>
      ))}
    </div>
  );
}
```

- [ ] **Step 4: Run tests; confirm pass**

```bash
npm run test -- --run __tests__/Jobs.test.tsx
```

Expected: all 3 PASS.

- [ ] **Step 5: Run the whole frontend test suite**

```bash
npm run test -- --run
```

Expected: every test PASSES (5 client + 5 sse + 3 AddListDialog + 4 TrackTable + 3 Jobs = 20 tests).

- [ ] **Step 6: Commit**

```bash
git add src/toolcrate/web/frontend/src/pages/Jobs.tsx src/toolcrate/web/frontend/__tests__/Jobs.test.tsx
git commit -m "feat(frontend): jobs page with state/type filters and cancel/retry actions"
```

---

## Task 18: CI workflow for frontend

**Files:**
- Create: `.github/workflows/frontend.yml` (or extend the existing CI workflow if all jobs live in one file)

- [ ] **Step 1: Write the workflow**

```yaml
name: Frontend

on:
  push:
    branches: [main]
  pull_request:
    paths:
      - "src/toolcrate/web/frontend/**"
      - ".github/workflows/frontend.yml"

defaults:
  run:
    working-directory: src/toolcrate/web/frontend

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm"
          cache-dependency-path: src/toolcrate/web/frontend/package-lock.json
      - run: npm ci
      - run: npm run lint
      - run: npm run typecheck
      - run: npm run test -- --run
      - run: npm run build
      - name: Verify generated types are committed
        run: |
          if [ -f src/api/types.ts ] && git diff --exit-code -- src/api/types.ts; then
            echo "ok"
          else
            echo "::warning::src/api/types.ts may be stale (skip if backend changed without re-running gen:api)"
          fi
```

- [ ] **Step 2: Inspect existing CI structure**

If `.github/workflows/` already contains a comprehensive single workflow, prefer adding a `frontend` job to it instead of a new file. List the directory:

```bash
ls .github/workflows/
```

If a single `ci.yml` exists, append the `test` job above as a top-level job inside that file (rename to `frontend`) and remove the new file.

- [ ] **Step 3: Verify locally**

```bash
make frontend-test
```

Expected: lint, typecheck, tests, and build all succeed.

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/frontend.yml
git commit -m "ci(frontend): lint/typecheck/test/build the SPA on PR"
```

---

## Task 19: Final wiring + README + self-review

**Files:**
- Modify: `README.md`
- Modify: `docs/SERVE.md` (if present)
- Create: `docs/FRONTEND.md`

- [ ] **Step 1: Verify the full stack still boots**

```bash
make frontend
toolcrate serve --port 48721
```

In another shell, hit the API and the SPA:

```bash
curl -i http://127.0.0.1:48721/api/v1/health
curl -i http://127.0.0.1:48721/app/ | head -20
```

Expected: `/api/v1/health` returns 200 with the health JSON; `/app/` returns 200, sets a `tc_session` cookie, and serves a non-stub `<html>` (no "Frontend not built" hint).

- [ ] **Step 2: Run the full pytest suite once more**

```bash
pytest tests/ -v
```

Expected: every backend test PASSES.

- [ ] **Step 3: Run the frontend tests once more**

```bash
cd src/toolcrate/web/frontend
npm run test -- --run
```

Expected: 20 tests PASS.

- [ ] **Step 4: Add a frontend section to `README.md`**

Add a new top-level section after the `toolcrate serve` section. If `README.md` does not have a `toolcrate serve` section yet, create one before this:

```markdown
### Web UI

`toolcrate serve` exposes a local web UI at `http://127.0.0.1:48721/app/`. The first
request to `/app` reads the API token from `~/.config/toolcrate/api-token`, sets it
as an `HttpOnly` cookie, and serves the React SPA. No login screen.

The SPA (Phase 2) covers:

- Dashboard skeleton (counts of lists and jobs, recent activity).
- Spotify lists master/detail with paste-URL Add-list flow.
- List detail with Tracks (filterable, retry per track), History (job log via SSE),
  and Settings (name, download path, sync interval, enabled) tabs.
- Jobs view with state/type filters, cancel running jobs, retry failed jobs.

Live progress is multiplexed over `/api/v1/events` (SSE).

#### Building the frontend manually

The wheel build (`pip install toolcrate`) compiles the SPA automatically when Node
20+ is on `PATH`. To build by hand:

    make frontend

To run the Vite dev server with hot reload (proxies API calls to a backend at
`127.0.0.1:48721`):

    TOOLCRATE_ENV=dev toolcrate serve --port 48721 &
    make frontend-dev
    # then visit http://localhost:5173
```

- [ ] **Step 5: Write `docs/FRONTEND.md`** (concise developer pointer)

```markdown
# toolcrate frontend

Lives at `src/toolcrate/web/frontend/`. Vite + React 18 + TypeScript + Tailwind +
shadcn/ui (Radix). State: TanStack Query v5 + custom SSE invalidator.

## Layout

    src/toolcrate/web/frontend/
      package.json
      src/
        api/      # fetch client, query keys, generated openapi types, SSE
        components/ # Sidebar, Layout, AddListDialog, ListMasterTable, TrackTable, etc.
        hooks/    # query/mutation hooks per resource + useSseInvalidation
        pages/    # Dashboard, SpotifyLists, ListDetail, Jobs
        lib/      # cn, format
        styles/globals.css
      __tests__/  # vitest specs
      scripts/gen-api.ts

## Common commands

| Command | What |
|---|---|
| `make frontend` | one-shot production build to `src/toolcrate/web/static/` |
| `make frontend-dev` | Vite dev server at `:5173` (set `TOOLCRATE_ENV=dev` for backend CORS) |
| `make frontend-test` | lint + typecheck + vitest + build |
| `npm run gen:api` | regenerate `src/api/types.ts` from a running backend's `/api/openapi.json` |

## Auth

The SPA uses cookie auth; no token is ever exposed to JS. The cookie is set by the
backend's `/app` route on first hit. SSE works because `EventSource` is same-origin.
The same `api_token_auth` dep accepts either `Authorization: Bearer <token>` or
`Cookie: tc_session=<token>` (header takes precedence).

## SSE event handling

`useSseInvalidation` opens one `EventSource` to `/api/v1/events`, dispatches each
event through `dispatchSseEvent` (which invalidates the right TanStack Query keys),
and feeds `log.append` events to per-job listeners registered via `subscribeJobLog`.
```

- [ ] **Step 6: Spec coverage self-check**

Open the spec file `docs/superpowers/specs/2026-04-30-phase-2-web-ui-design.md` side-by-side with this plan. Walk every section in the spec and confirm a task implements it:

- §3 row "Phase 2 page set" → Tasks 12, 14, 15, 16, 17.
- §3 row "Auth in browser" → Tasks 1, 2.
- §3 row "Build/ship" → Task 5.
- §3 row "Frontend location" → Task 6.
- §3 row "Dev workflow" → Task 4 + Task 6 (vite proxy) + Task 19 README.
- §3 row "API typing" → Task 8 (gen:api script + types).
- §3 row "Server state" → Task 11.
- §3 row "Live log tail" → Task 9 (SSE) + Task 16 (`JobLogPane`).
- §3 row "E2E tests" → explicitly deferred; no task.
- §4.1 directory layout → Tasks 6, 7, 8, 9, 10, 11–17.
- §4.2 stack → Task 6 deps + Task 7 shadcn primitives.
- §4.3 auth flow → Tasks 1, 2.
- §4.4 SSE → query invalidation → Task 9.
- §4.5 new backend endpoint → Task 3.
- §4.6 add-list flow → Task 13.
- §4.7 pages → Tasks 12 (Dashboard), 14 (SpotifyLists), 15 + 16 (ListDetail tabs), 17 (Jobs).
- §4.8 build hook details → Task 5 (hook) + Task 18 (CI verifies).
- §4.9 backend `/app` serving → Task 2.
- §4.10 dev CORS → Task 4.
- §4.11 tests → Task 1 (auth cookie), Task 2 (app static), Task 3 (preview), Task 4 (CORS), Task 8 (client), Task 9 (sse), Task 13 (AddListDialog), Task 15 (TrackTable), Task 17 (Jobs).
- §6 risks → addressed by the hatch hook fallback (Task 5), CI generated-types check (Task 18), cookie security flags (Task 2), CORS gating (Task 4), virtualization left as a future polish item (still acceptable for P2 since pagination caps responses at 2000).

If any row in the spec has no matching task, add a follow-up task here before handoff.

- [ ] **Step 7: Commit docs**

```bash
git add README.md docs/FRONTEND.md
git commit -m "docs(frontend): readme + FRONTEND.md after phase 2 UI ships"
```

- [ ] **Step 8: Open the PR**

```bash
git push -u origin claude/exciting-swirles-545342
gh pr create --title "Phase 2 — Web UI v1: paste-URL Spotify + queue end-to-end" --body "$(cat <<'EOF'
## Summary

- React/TS SPA at `/app`, pages: Dashboard, Spotify lists, list detail (Tracks/History/Settings), Jobs.
- Cookie-based auth via the new `/app` route (no login screen).
- New `POST /api/v1/lists/preview` autofills the Add-list dialog.
- Hatch build hook compiles the SPA during `pip install` when Node 20+ is on PATH; falls back to a stub HTML otherwise.
- SSE-driven TanStack Query invalidation for live UI updates.

## Test plan

- [ ] `pytest tests/web/`
- [ ] `make frontend-test`
- [ ] `toolcrate serve` then visit `/app/`, add a public Spotify playlist, watch it sync to completion.
- [ ] Cancel a running job + retry a failed one from the Jobs page.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

---

## Self-Review (executed at plan-write time)

Reviewed against `docs/superpowers/specs/2026-04-30-phase-2-web-ui-design.md`:

- **Spec coverage:** every row in §3 and every subsection in §4 maps to at least one task (see Task 19 Step 6 for the mapping). E2E tests are explicitly deferred per spec §4.11.
- **Placeholder scan:** no `TBD`, `TODO`, `implement later`, or "similar to Task N" patterns. Each task carries the actual code.
- **Type consistency:** `apiFetch`, `ApiError`, `dispatchSseEvent`, `subscribeJobLog`, `useLists`, `usePatchList`, `useTriggerSync`, `useTracks`, `useRetryTrack`, `useSkipTrack`, `useJobs`, `useCancelJob`, `useRetryJob`, `usePreviewMutation`, `StatusPill`, `TrackTable`, `ListMasterTable`, `JobLogPane`, `AddListDialog`, `LiveBadge`, `Sidebar`, `Layout` — each name appears identically across the tasks that define and consume it. Resource shapes (`SourceList`, `TrackEntry`, `Job`, `Page<T>`, `ListPreview`) come from `@/api/resources` and are referenced consistently.
- **Backend symbols:** `api_token_auth` (Task 1), `build_router` for `auth_app` (Task 2), `ListPreviewIn`/`ListPreviewOut` (Task 3), `dev_cors_origins` on `AppDeps` (Task 4), `FrontendBuildHook` (Task 5). The `routers/lists.py` import update in Task 3 includes the two new schemas.
- **Known sharp edges flagged inline:** Task 3 Step 4 warns that `_spotify_credentials` may not yet exist as a method, and instructs the engineer to either match the existing `SpotifyClient` instantiation pattern or break the credential extraction into its own preceding refactor commit. Task 8 Step 2 has a fallback path when the backend is not running locally. Task 18 Step 2 covers single-file vs split-file CI layouts.

