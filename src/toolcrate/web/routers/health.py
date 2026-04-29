"""Health and info endpoints. Health is unauthenticated; info is auth'd."""

from __future__ import annotations

from fastapi import APIRouter


def build_router(*, version: str) -> APIRouter:
    router = APIRouter(prefix="/api/v1")

    @router.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @router.get("/info")
    def info() -> dict:
        return {"version": version}

    return router
