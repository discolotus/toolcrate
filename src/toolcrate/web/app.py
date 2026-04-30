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
