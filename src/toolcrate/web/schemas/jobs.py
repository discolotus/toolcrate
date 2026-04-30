from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    type: str
    state: str
    priority: int
    source_list_id: int | None
    attempts: int
    max_attempts: int
    scheduled_for: datetime
    started_at: datetime | None
    finished_at: datetime | None
    progress_json: dict
    error: str | None


class JobLogPage(BaseModel):
    job_id: int
    lines: list[str]
    next_offset: int | None
