"""In-process pub/sub event bus.

Each subscriber gets an asyncio.Queue. Publishers fan out to all matching
queues. Used to bridge worker/service progress -> SSE handlers.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import AsyncIterator, Iterable


@dataclass(slots=True)
class Event:
    name: str
    data: dict
    topic: str = "default"


class _Subscription:
    def __init__(self, topics: set[str] | None) -> None:
        self.topics = topics
        self.queue: asyncio.Queue[Event] = asyncio.Queue(maxsize=1000)

    def __aiter__(self) -> AsyncIterator[Event]:
        return self

    async def __anext__(self) -> Event:
        return await self.queue.get()


class EventBus:
    def __init__(self) -> None:
        self._subs: list[_Subscription] = []
        self._lock = asyncio.Lock()

    def subscribe(self, *, topics: Iterable[str] | None = None) -> _Subscription:
        sub = _Subscription(set(topics) if topics else None)
        self._subs.append(sub)
        return sub

    async def unsubscribe(self, sub: _Subscription) -> None:
        async with self._lock:
            if sub in self._subs:
                self._subs.remove(sub)

    async def publish(self, event: Event) -> None:
        async with self._lock:
            targets = [s for s in self._subs if s.topics is None or event.topic in s.topics]
        for s in targets:
            try:
                s.queue.put_nowait(event)
            except asyncio.QueueFull:
                # slow consumer; drop oldest then enqueue
                _ = s.queue.get_nowait()
                s.queue.put_nowait(event)
