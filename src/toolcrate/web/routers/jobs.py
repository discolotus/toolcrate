"""Job listing, fetch, log, cancel, retry."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from toolcrate.core.jobs import JobQueue
from toolcrate.db.models import Job
from toolcrate.web.deps import api_token_auth
from toolcrate.web.schemas.common import Page
from toolcrate.web.schemas.jobs import JobOut, JobLogPage


def build_router(
    *,
    queue: JobQueue,
    session_factory: async_sessionmaker[AsyncSession],
    token_hash: str,
) -> APIRouter:
    auth = Depends(api_token_auth(token_hash=token_hash))
    router = APIRouter(prefix="/api/v1/jobs", dependencies=[auth])

    @router.get("", response_model=Page[JobOut])
    async def list_jobs(
        state: str | None = None,
        type: str | None = None,
        list_id: int | None = None,
        limit: int = Query(default=100, le=1000),
        offset: int = 0,
    ) -> Page:
        async with session_factory() as session:
            stmt = select(Job)
            if state is not None:
                stmt = stmt.where(Job.state == state)
            if type is not None:
                stmt = stmt.where(Job.type == type)
            if list_id is not None:
                stmt = stmt.where(Job.source_list_id == list_id)
            stmt = stmt.order_by(Job.id.desc()).offset(offset).limit(limit)
            rows = (await session.execute(stmt)).scalars().all()
            return Page(
                items=[JobOut.model_validate(r) for r in rows],
                total=len(rows),
                limit=limit,
                offset=offset,
            )

    @router.get("/{job_id}", response_model=JobOut)
    async def get_job(job_id: int) -> JobOut:
        async with session_factory() as session:
            row = await session.get(Job, job_id)
            if row is None:
                raise HTTPException(status_code=404, detail="job not found")
            return JobOut.model_validate(row)

    @router.get("/{job_id}/log", response_model=JobLogPage)
    async def get_job_log(
        job_id: int, offset: int = 0, limit: int = 1000
    ) -> JobLogPage:
        async with session_factory() as session:
            row = await session.get(Job, job_id)
            if row is None:
                raise HTTPException(status_code=404, detail="job not found")
        if not row.log_path:
            return JobLogPage(job_id=job_id, lines=[], next_offset=None)
        try:
            with open(row.log_path) as f:
                all_lines = f.readlines()
        except FileNotFoundError:
            return JobLogPage(job_id=job_id, lines=[], next_offset=None)
        slice_ = all_lines[offset : offset + limit]
        next_offset = (
            offset + len(slice_) if (offset + limit) < len(all_lines) else None
        )
        return JobLogPage(
            job_id=job_id,
            lines=[s.rstrip("\n") for s in slice_],
            next_offset=next_offset,
        )

    @router.post("/{job_id}/cancel", response_model=JobOut)
    async def cancel(job_id: int) -> JobOut:
        async with session_factory() as session:
            row = await session.get(Job, job_id)
            if row is None:
                raise HTTPException(status_code=404, detail="job not found")
        await queue.cancel(job_id)
        async with session_factory() as session:
            row = await session.get(Job, job_id)
            return JobOut.model_validate(row)

    @router.post("/{job_id}/retry", response_model=JobOut)
    async def retry(job_id: int) -> JobOut:
        async with session_factory() as session:
            row = await session.get(Job, job_id)
            if row is None:
                raise HTTPException(status_code=404, detail="job not found")
            row.state = "pending"
            row.scheduled_for = datetime.now(timezone.utc)
            row.attempts = 0
            row.error = None
            row.finished_at = None
            await session.commit()
            await session.refresh(row)
            return JobOut.model_validate(row)

    return router
