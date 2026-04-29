"""FastAPI app factory.

create_app builds an application instance from explicit dependencies so
tests can construct one with stubs. The CLI's `serve` command builds the
real graph and calls into this factory.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from fastapi import FastAPI

from .middleware import OriginHostGuardMiddleware


@dataclass
class AppDeps:
    api_token_hash: str
    allowed_hosts: set[str]
    routers: Iterable = ()


def create_app(deps: AppDeps) -> FastAPI:
    app = FastAPI(title="toolcrate", version="0.1.0", docs_url="/api/docs",
                  redoc_url=None, openapi_url="/api/openapi.json")
    app.add_middleware(OriginHostGuardMiddleware, allowed_hosts=deps.allowed_hosts)
    for router in deps.routers:
        app.include_router(router)
    return app
