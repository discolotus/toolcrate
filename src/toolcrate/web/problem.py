"""RFC 7807 problem+json helpers."""

from __future__ import annotations

from fastapi.responses import JSONResponse


def problem(*, status: int, code: str, title: str, detail: str = "") -> JSONResponse:
    return JSONResponse(
        status_code=status,
        media_type="application/problem+json",
        content={"type": f"about:blank#{code}", "title": title,
                 "status": status, "detail": detail, "code": code},
    )
