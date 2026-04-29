"""HTTP middleware: Origin/Host guard for DNS-rebinding defense.

Local-only deployment trusts only requests whose Host header is one of the
allowed local hostnames. When an Origin header is present (browser request),
it must also be a localhost variant.
"""

from __future__ import annotations

from urllib.parse import urlparse

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class OriginHostGuardMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, allowed_hosts: set[str]) -> None:
        super().__init__(app)
        self._hosts = {h.lower() for h in allowed_hosts}

    async def dispatch(self, request, call_next):
        host = (request.headers.get("host") or "").split(":")[0].lower()
        if host not in self._hosts:
            return JSONResponse(status_code=403, content={"detail": "host not allowed"})
        origin = request.headers.get("origin")
        if origin:
            ohost = (urlparse(origin).hostname or "").lower()
            if ohost not in self._hosts:
                return JSONResponse(status_code=403, content={"detail": "origin not allowed"})
        return await call_next(request)
