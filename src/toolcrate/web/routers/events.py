"""Server-Sent Events stream multiplexed across topics."""

from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator

from fastapi import APIRouter, Depends, Query
from sse_starlette.sse import EventSourceResponse

from toolcrate.core.events import EventBus
from toolcrate.web.deps import api_token_auth


def build_router(*, bus: EventBus, token_hash: str) -> APIRouter:
    auth = Depends(api_token_auth(token_hash=token_hash))
    router = APIRouter(prefix="/api/v1", dependencies=[auth])

    @router.get("/events")
    async def events(topics: str | None = Query(default=None)):
        topic_set = set(topics.split(",")) if topics else None
        sub = bus.subscribe(topics=topic_set)

        async def gen() -> AsyncIterator[dict]:
            try:
                async for event in sub:
                    yield {"event": event.name, "data": json.dumps(event.data)}
            finally:
                await bus.unsubscribe(sub)

        return EventSourceResponse(gen(), ping=15)

    return router
