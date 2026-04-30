"""DownloadService: single-track sldl invocation + reconcile."""

from __future__ import annotations

import logging
import tempfile
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from toolcrate.db.models import Download, SourceList, TrackEntry

from .events import Event, EventBus
from .reconcile import match_index_to_tracks
from .sldl_adapter import (
    build_command,
    parse_index_csv,
    parse_progress_line,
    stream_sldl,
)

logger = logging.getLogger(__name__)


_INDEX_TO_TRACK_STATUS = {
    "downloaded": "done",
    "already_exists": "done",
    "failed": "failed",
    "not_found_last_time": "failed",
    "not_processed": "pending",
    "unknown": "pending",
}


class DownloadService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        bus: EventBus,
        sldl_path: str,
        sldl_extra_args: Iterable[str],
    ) -> None:
        self._sf = session_factory
        self._bus = bus
        self._sldl = sldl_path
        self._extra = list(sldl_extra_args)

    async def run_single_track(self, track_id: int, *, job_id: int | None = None,
                               log_path: str | None = None) -> None:
        async with self._sf() as session:
            track = await session.get(TrackEntry, track_id)
            if track is None:
                raise ValueError(f"track {track_id} not found")
            sl = await session.get(SourceList, track.source_list_id)
        query = f"{track.artist} - {track.title}"

        if log_path:
            log_file = Path(log_path)
        else:
            tmp = tempfile.NamedTemporaryFile(prefix="sldl-track-", suffix=".log", delete=False)
            tmp.close()
            log_file = Path(tmp.name)
        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = str(Path(tmpdir) / "index.sldl")
            cmd = build_command(
                sldl_path=self._sldl, input_arg=query,
                download_path=sl.download_path, index_path=index_path,
                extra_args=[*self._extra, "--input-type", "string"],
            )
            with log_file.open("w") as logf:
                first = True
                async for _proc, line in stream_sldl(cmd):
                    if first:
                        first = False
                        continue
                    if not line:
                        continue
                    logf.write(line + "\n")
                    if parse_progress_line(line) is not None:
                        await self._bus.publish(Event(
                            name="log.append", topic="jobs",
                            data={"job_id": job_id, "lines": [line]},
                        ))
            try:
                index_text = Path(index_path).read_text()
            except FileNotFoundError:
                index_text = ""
            index = parse_index_csv(index_text)

        async with self._sf() as session:
            tracks = (await session.execute(
                select(TrackEntry).where(TrackEntry.id == track_id)
            )).scalars().all()
            results = match_index_to_tracks(index, tracks)
            for r in results:
                if r.track_id is None:
                    continue
                new_status = _INDEX_TO_TRACK_STATUS.get(r.state, "pending")
                d = Download(
                    track_entry_id=r.track_id, job_id=job_id,
                    status=new_status, file_path=r.file_path or None,
                    sldl_match_path=r.file_path or None,
                    error=r.failure_reason or None,
                    finished_at=datetime.now(timezone.utc),
                )
                session.add(d)
                await session.flush()
                await session.execute(update(TrackEntry)
                                      .where(TrackEntry.id == r.track_id)
                                      .values(download_status=new_status, download_id=d.id))
            await session.commit()
