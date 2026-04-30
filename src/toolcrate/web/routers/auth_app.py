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

from toolcrate.web.deps import COOKIE_NAME
INSTALL_HINT_HTML = """\
<!doctype html>
<html><head><title>toolcrate</title></head><body style="font-family:sans-serif;padding:2em">
<h1>Frontend not built</h1>
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
        except OSError:
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
