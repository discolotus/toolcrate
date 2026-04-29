"""Wire each JobType to the right service call.

A handler entry is omitted entirely if its service is None. The Worker's
unknown-type fallback then marks such jobs failed cleanly.
"""

from __future__ import annotations

import logging
import tempfile
from collections.abc import Awaitable, Callable

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from toolcrate.db.models import Job

from .events import EventBus
from .jobs import JobType

logger = logging.getLogger(__name__)


Handler = Callable[[Job], Awaitable[None]]


def _make_log_path(job: Job) -> str:
    return tempfile.mktemp(prefix=f"toolcrate-job-{job.id}-", suffix=".log")


def build_handlers(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    bus: EventBus,
    sync_service,
    recognition_service,
    download_service,
    library_service,
) -> dict[JobType, Handler]:
    handlers: dict[JobType, Handler] = {}

    if sync_service is not None:
        async def _sync(job: Job) -> None:
            payload = job.payload_json or {}
            list_id = int(payload["list_id"])
            log_path = _make_log_path(job)
            async with session_factory() as session:
                await session.execute(update(Job).where(Job.id == job.id)
                                      .values(log_path=log_path))
                await session.commit()
            await sync_service.run_for_list(list_id, job_id=job.id, log_path=log_path)

        handlers[JobType.SYNC_LIST] = _sync

    if download_service is not None:
        async def _download(job: Job) -> None:
            payload = job.payload_json or {}
            track_id = int(payload["track_id"])
            log_path = _make_log_path(job)
            async with session_factory() as session:
                await session.execute(update(Job).where(Job.id == job.id)
                                      .values(log_path=log_path))
                await session.commit()
            await download_service.run_single_track(track_id, job_id=job.id, log_path=log_path)

        handlers[JobType.DOWNLOAD_TRACK] = _download

    if recognition_service is not None:
        async def _recognize(job: Job) -> None:
            payload = job.payload_json or {}
            list_id = int(payload["list_id"])
            await recognition_service.run_for_list(list_id, job_id=job.id)

        handlers[JobType.RECOGNIZE_DJSET] = _recognize

    if library_service is not None:
        async def _scan(job: Job) -> None:
            await library_service.scan(job_id=job.id)

        handlers[JobType.LIBRARY_SCAN] = _scan

    return handlers
