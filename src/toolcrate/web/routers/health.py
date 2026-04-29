"""Health and info endpoints. Health is unauthenticated; info is auth'd."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from toolcrate.web.deps import api_token_auth


def build_router(*, version: str, token_hash: str | None = None) -> APIRouter:
    router = APIRouter(prefix="/api/v1")

    @router.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    info_deps = []
    if token_hash:
        info_deps.append(Depends(api_token_auth(token_hash=token_hash)))

    @router.get("/info", dependencies=info_deps)
    def info() -> dict:
        return {"version": version}

    return router
