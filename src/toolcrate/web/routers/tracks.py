"""Track list and per-track actions."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from toolcrate.core.exceptions import NotFound
from toolcrate.core.jobs import JobQueue, JobType
from toolcrate.core.source_lists import SourceListService
from toolcrate.db.models import TrackEntry
from toolcrate.web.deps import api_token_auth
from toolcrate.web.schemas.common import Page
from toolcrate.web.schemas.tracks import TrackEntryOut


def build_router(
    *,
    src: SourceListService,
    session_factory: async_sessionmaker[AsyncSession],
    queue: JobQueue,
    token_hash: str,
) -> APIRouter:
    auth = Depends(api_token_auth(token_hash=token_hash))
    router = APIRouter(prefix="/api/v1/lists", dependencies=[auth])

    @router.get("/{list_id}/tracks", response_model=Page[TrackEntryOut])
    async def list_tracks(
        list_id: int,
        status: str | None = None,
        limit: int = Query(default=200, le=2000),
        offset: int = 0,
    ) -> Page:
        try:
            await src.get(list_id)
        except NotFound:
            raise HTTPException(status_code=404, detail="list not found")
        async with session_factory() as session:
            stmt = select(TrackEntry).where(TrackEntry.source_list_id == list_id)
            if status is not None:
                stmt = stmt.where(TrackEntry.download_status == status)
            stmt = stmt.order_by(TrackEntry.position).offset(offset).limit(limit)
            rows = (await session.execute(stmt)).scalars().all()
            return Page(
                items=[TrackEntryOut.model_validate(r) for r in rows],
                total=len(rows),
                limit=limit,
                offset=offset,
            )

    @router.post("/{list_id}/tracks/{track_id}/skip", response_model=TrackEntryOut)
    async def skip_track(list_id: int, track_id: int) -> TrackEntryOut:
        async with session_factory() as session:
            row = await session.get(TrackEntry, track_id)
            if row is None or row.source_list_id != list_id:
                raise HTTPException(status_code=404, detail="track not found")
            row.download_status = "skipped"
            await session.commit()
            await session.refresh(row)
            return TrackEntryOut.model_validate(row)

    @router.post("/{list_id}/tracks/{track_id}/download", status_code=202)
    async def trigger_track_download(list_id: int, track_id: int) -> dict:
        async with session_factory() as session:
            row = await session.get(TrackEntry, track_id)
            if row is None or row.source_list_id != list_id:
                raise HTTPException(status_code=404, detail="track not found")
        job = await queue.enqueue(
            JobType.DOWNLOAD_TRACK,
            payload={"track_id": track_id, "list_id": list_id},
            source_list_id=list_id,
        )
        return {"job_id": job.id}

    return router
