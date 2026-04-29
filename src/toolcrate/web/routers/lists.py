"""Source list CRUD + sync trigger."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from toolcrate.core.exceptions import NotFound, ValidationError
from toolcrate.core.jobs import JobQueue, JobType
from toolcrate.core.source_lists import SourceListService
from toolcrate.web.deps import api_token_auth
from toolcrate.web.schemas.common import Page
from toolcrate.web.schemas.lists import SourceListIn, SourceListOut, SourceListPatch


def build_router(*, src: SourceListService, queue: JobQueue, token_hash: str) -> APIRouter:
    auth = Depends(api_token_auth(token_hash=token_hash))
    router = APIRouter(prefix="/api/v1/lists", dependencies=[auth])

    @router.get("", response_model=Page[SourceListOut])
    async def list_all(source_type: str | None = None, enabled: bool | None = None) -> Page:
        rows = await src.list(source_type=source_type, enabled=enabled)
        return Page(items=[SourceListOut.model_validate(r) for r in rows],
                    total=len(rows), limit=len(rows), offset=0)

    @router.post("", response_model=SourceListOut, status_code=status.HTTP_201_CREATED)
    async def create(payload: SourceListIn) -> SourceListOut:
        try:
            row = await src.create(
                name=payload.name,
                source_url=payload.source_url,
                source_type=payload.source_type,
                download_path=payload.download_path,
                sync_interval=payload.sync_interval,
                oauth_account_id=payload.oauth_account_id,
            )
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        return SourceListOut.model_validate(row)

    @router.get("/{list_id}", response_model=SourceListOut)
    async def get_one(list_id: int) -> SourceListOut:
        try:
            row = await src.get(list_id)
        except NotFound:
            raise HTTPException(status_code=404, detail="list not found")
        return SourceListOut.model_validate(row)

    @router.patch("/{list_id}", response_model=SourceListOut)
    async def patch(list_id: int, payload: SourceListPatch) -> SourceListOut:
        fields = {k: v for k, v in payload.model_dump(exclude_unset=True).items()}
        try:
            row = await src.update(list_id, fields)
        except NotFound:
            raise HTTPException(status_code=404, detail="list not found")
        return SourceListOut.model_validate(row)

    @router.delete("/{list_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete(list_id: int) -> None:
        try:
            await src.delete(list_id)
        except NotFound:
            raise HTTPException(status_code=404, detail="list not found")

    @router.post("/{list_id}/sync", status_code=status.HTTP_202_ACCEPTED)
    async def trigger_sync(list_id: int) -> dict:
        try:
            await src.get(list_id)
        except NotFound:
            raise HTTPException(status_code=404, detail="list not found")
        job = await queue.enqueue(JobType.SYNC_LIST, payload={"list_id": list_id},
                                  source_list_id=list_id)
        return {"job_id": job.id}

    return router
