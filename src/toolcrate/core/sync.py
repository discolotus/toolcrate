"""SyncService: orchestrate one sync run for a source_list.

Steps for a Spotify or YouTube playlist source:
  1. (Caller has already populated track_entry rows from metadata.)
  2. Build an sldl command pointed at list.source_url and download_path.
  3. Stream stdout, append to log, fan out progress events.
  4. After exit, parse the index file and reconcile to track_entry rows.
  5. Update list.last_synced_at / last_sync_status.
"""

from __future__ import annotations

import logging
import tempfile
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from toolcrate.db.models import Download, Job, TrackEntry

from .events import Event, EventBus
from .reconcile import match_index_to_tracks
from .sldl_adapter import (
    build_command,
    parse_index_csv,
    parse_progress_line,
    stream_sldl,
)
from .source_lists import SourceListService

logger = logging.getLogger(__name__)


_INDEX_TO_TRACK_STATUS = {
    "downloaded": "done",
    "already_exists": "done",
    "failed": "failed",
    "not_found_last_time": "failed",
    "not_processed": "pending",
    "unknown": "pending",
}


class SyncService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        bus: EventBus,
        sldl_path: str,
        sldl_extra_args: Iterable[str],
        src_service: SourceListService,
    ) -> None:
        self._sf = session_factory
        self._bus = bus
        self._sldl = sldl_path
        self._extra = list(sldl_extra_args)
        self._src = src_service

    async def run_for_list(
        self, list_id: int, *, job_id: int | None = None, log_path: str | None = None
    ) -> None:
        sl = await self._src.get(list_id)
        if not sl.source_url and sl.source_type != "manual":
            raise ValueError(f"list {list_id} has no source_url")

        if log_path:
            log_file = Path(log_path)
        else:
            # NamedTemporaryFile avoids the deprecated mktemp TOCTOU window.
            tmp = tempfile.NamedTemporaryFile(prefix="sldl-", suffix=".log", delete=False)
            tmp.close()
            log_file = Path(tmp.name)
        log_file.parent.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = str(Path(tmpdir) / "index.sldl")
            cmd = build_command(
                sldl_path=self._sldl,
                input_arg=sl.source_url or "",
                download_path=sl.download_path,
                index_path=index_path,
                extra_args=self._extra,
            )
            with log_file.open("w") as logf:
                proc_holder: dict = {}
                async for proc, line in stream_sldl(cmd):
                    if not proc_holder:
                        proc_holder["pid"] = proc.pid
                        if job_id is not None:
                            await self._record_pid(job_id, proc.pid)
                        continue
                    if not line:
                        continue
                    logf.write(line + "\n")
                    logf.flush()
                    ev = parse_progress_line(line)
                    if ev is not None:
                        await self._bus.publish(Event(
                            name="log.append", topic="jobs",
                            data={"job_id": job_id, "lines": [line]},
                        ))
                        await self._bus.publish(Event(
                            name="job.update", topic="jobs",
                            data={"id": job_id, "progress": {"message": ev.kind, "track": ev.track_label}},
                        ))

            try:
                index_text = Path(index_path).read_text()
            except FileNotFoundError:
                index_text = ""
            index = parse_index_csv(index_text)

        # Reconcile: load tracks for this list and match.
        async with self._sf() as session:
            tracks = (await session.execute(
                select(TrackEntry).where(TrackEntry.source_list_id == list_id)
            )).scalars().all()
            results = match_index_to_tracks(index, tracks)
            for r in results:
                if r.track_id is None:
                    continue
                new_status = _INDEX_TO_TRACK_STATUS.get(r.state, "pending")
                d = Download(
                    track_entry_id=r.track_id,
                    job_id=job_id,
                    status=new_status if new_status in {"done", "failed"} else "partial",
                    file_path=r.file_path or None,
                    sldl_match_path=r.file_path or None,
                    error=r.failure_reason or None,
                    finished_at=datetime.now(timezone.utc),
                )
                session.add(d)
                await session.flush()
                await session.execute(
                    update(TrackEntry)
                    .where(TrackEntry.id == r.track_id)
                    .values(download_status=new_status, download_id=d.id)
                )
            await session.commit()

        await self._src.update(list_id, {
            "last_synced_at": datetime.now(timezone.utc),
            "last_sync_status": "ok",
            "last_error": None,
        })
        await self._bus.publish(Event(
            name="list.updated", topic="lists",
            data={"id": list_id, "last_synced_at": "now"},
        ))

    async def _record_pid(self, job_id: int, pid: int) -> None:
        async with self._sf() as session:
            await session.execute(update(Job).where(Job.id == job_id).values(pid=pid))
            await session.commit()
