"""DB-backed job queue and async worker.

Single worker drains the table serially. Job handlers are registered by
JobType. Failed jobs retry with exponential backoff up to max_attempts.
The worker is started/stopped by the FastAPI lifespan; tests exercise it
directly.

Note: `with_for_update(skip_locked=True)` is a no-op on SQLite (no
row-level locking). This is acceptable for single-worker phase 1; the
worker is the only consumer.
"""

from __future__ import annotations

import asyncio
import enum
import logging
from collections.abc import Awaitable, Callable, Mapping
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from toolcrate.db.models import Job

from .events import Event, EventBus

logger = logging.getLogger(__name__)


class JobType(str, enum.Enum):
    SYNC_LIST = "sync_list"
    RECOGNIZE_DJSET = "recognize_djset"
    DOWNLOAD_TRACK = "download_track"
    LIBRARY_SCAN = "library_scan"


HandlerCtx = dict[str, Any]
Handler = Callable[[Job], Awaitable[None]]


class JobQueue:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._sf = session_factory

    async def enqueue(
        self,
        type: JobType,
        *,
        payload: dict[str, Any],
        priority: int = 100,
        max_attempts: int = 3,
        source_list_id: int | None = None,
        scheduled_for: datetime | None = None,
    ) -> Job:
        async with self._sf() as session:
            j = Job(
                type=type.value,
                payload_json=payload,
                priority=priority,
                max_attempts=max_attempts,
                source_list_id=source_list_id,
                scheduled_for=scheduled_for or datetime.now(timezone.utc),
            )
            session.add(j)
            await session.commit()
            await session.refresh(j)
            return j

    async def cancel(self, job_id: int) -> None:
        async with self._sf() as session:
            await session.execute(
                update(Job).where(Job.id == job_id).values(state="cancelled",
                                                          finished_at=datetime.now(timezone.utc))
            )
            await session.commit()

    async def claim_next(self, *, now: datetime | None = None) -> Job | None:
        now = now or datetime.now(timezone.utc)
        async with self._sf() as session:
            stmt = (
                select(Job)
                .where(Job.state == "pending", Job.scheduled_for <= now)
                .order_by(Job.priority.asc(), Job.scheduled_for.asc())
                .limit(1)
                .with_for_update(skip_locked=True)
            )
            row = (await session.execute(stmt)).scalar_one_or_none()
            if row is None:
                return None
            row.state = "running"
            row.started_at = now
            row.attempts = (row.attempts or 0) + 1
            await session.commit()
            await session.refresh(row)
            return row


class Worker:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        queue: JobQueue,
        bus: EventBus,
        *,
        handlers: Mapping[JobType, Callable[..., Awaitable[None]]],
        poll_interval: float = 1.0,
        backoff_base_seconds: float = 60.0,
    ) -> None:
        self._sf = session_factory
        self._queue = queue
        self._bus = bus
        self._handlers = handlers
        self._poll = poll_interval
        self._backoff = backoff_base_seconds
        self._stop = asyncio.Event()

    def stop(self) -> None:
        self._stop.set()

    async def run(self) -> None:
        while not self._stop.is_set():
            job = await self._queue.claim_next()
            if job is None:
                try:
                    await asyncio.wait_for(self._stop.wait(), timeout=self._poll)
                except asyncio.TimeoutError:
                    pass
                continue
            await self._dispatch(job)

    async def _dispatch(self, job: Job) -> None:
        handler = self._handlers.get(JobType(job.type))
        if handler is None:
            await self._mark_failed(job, f"no handler for {job.type}")
            return
        await self._bus.publish(Event(name="job.update", topic="jobs",
                                      data={"id": job.id, "state": "running"}))
        try:
            await handler(job)
        except Exception as exc:  # noqa: BLE001
            logger.exception("job %s failed: %s", job.id, exc)
            await self._on_failure(job, exc)
            return
        async with self._sf() as session:
            row = await session.get(Job, job.id)
            row.state = "success"
            row.finished_at = datetime.now(timezone.utc)
            await session.commit()
        await self._bus.publish(Event(name="job.update", topic="jobs",
                                      data={"id": job.id, "state": "success"}))

    async def _on_failure(self, job: Job, exc: Exception) -> None:
        async with self._sf() as session:
            row = await session.get(Job, job.id)
            if row.attempts < row.max_attempts:
                row.state = "pending"
                delay = self._backoff * (2 ** (row.attempts - 1))
                row.scheduled_for = datetime.now(timezone.utc) + timedelta(seconds=delay)
                row.error = str(exc)
            else:
                row.state = "failed"
                row.finished_at = datetime.now(timezone.utc)
                row.error = str(exc)
            await session.commit()
        await self._bus.publish(Event(name="job.update", topic="jobs",
                                      data={"id": job.id, "state": row.state}))

    async def _mark_failed(self, job: Job, error: str) -> None:
        async with self._sf() as session:
            row = await session.get(Job, job.id)
            row.state = "failed"
            row.finished_at = datetime.now(timezone.utc)
            row.error = error
            await session.commit()
        await self._bus.publish(Event(name="job.update", topic="jobs",
                                      data={"id": job.id, "state": "failed"}))
