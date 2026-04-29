from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SourceType = Literal["spotify_playlist", "youtube_djset", "manual"]


class SourceListIn(BaseModel):
    name: str = Field(min_length=1, max_length=256)
    source_url: str = ""
    source_type: SourceType | None = None
    download_path: str | None = None
    sync_interval: str = "manual"
    oauth_account_id: int | None = None


class SourceListPatch(BaseModel):
    name: str | None = None
    download_path: str | None = None
    sync_interval: str | None = None
    enabled: bool | None = None


class SourceListOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    source_type: SourceType
    source_url: str
    external_id: str
    download_path: str
    enabled: bool
    sync_interval: str
    last_synced_at: datetime | None
    last_sync_status: str
    last_error: str | None
    oauth_account_id: int | None
    metadata_json: dict
    created_at: datetime
    updated_at: datetime
