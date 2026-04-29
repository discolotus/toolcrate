from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict


class TrackEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    source_list_id: int
    position: int
    artist: str | None
    title: str | None
    album: str | None
    duration_sec: int | None
    isrc: str | None
    spotify_track_id: str | None
    yt_timestamp_sec: int | None
    recognition_confidence: float | None
    download_status: str
    download_id: int | None
    first_seen_at: datetime
    last_seen_at: datetime
    removed_at: datetime | None
