"""SQLAlchemy 2.x declarative models for toolcrate."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class SourceList(Base):
    __tablename__ = "source_list"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(256))
    source_type: Mapped[str] = mapped_column(String(32))  # spotify_playlist | youtube_djset | manual
    source_url: Mapped[str] = mapped_column(Text, default="")
    external_id: Mapped[str] = mapped_column(String(128), default="")
    download_path: Mapped[str] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    sync_interval: Mapped[str] = mapped_column(String(64), default="manual")
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sync_status: Mapped[str] = mapped_column(String(16), default="never")
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    oauth_account_id: Mapped[int | None] = mapped_column(ForeignKey("oauth_account.id"), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    tracks: Mapped[list[TrackEntry]] = relationship(back_populates="source_list", cascade="all,delete-orphan")


class TrackEntry(Base):
    __tablename__ = "track_entry"
    __table_args__ = (
        Index("ix_track_entry_list_position", "source_list_id", "position"),
        # NOTE: SQLite treats NULL != NULL in UNIQUE, so this constraint
        # behaves as a partial unique. If we ever port to Postgres, replace
        # with `Index(..., unique=True, sqlite_where=isrc.is_not(None))` or
        # an equivalent partial index, otherwise multiple NULL ISRCs
        # within a single source_list would conflict.
        UniqueConstraint("source_list_id", "isrc", name="uq_track_list_isrc"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_list_id: Mapped[int] = mapped_column(ForeignKey("source_list.id", ondelete="CASCADE"))
    position: Mapped[int] = mapped_column(Integer, default=0)
    artist: Mapped[str | None] = mapped_column(String(512), nullable=True)
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    album: Mapped[str | None] = mapped_column(String(512), nullable=True)
    duration_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    isrc: Mapped[str | None] = mapped_column(String(32), nullable=True)
    spotify_track_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    yt_timestamp_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    recognition_confidence: Mapped[float | None] = mapped_column(nullable=True)
    download_status: Mapped[str] = mapped_column(String(16), default="pending")
    download_id: Mapped[int | None] = mapped_column(ForeignKey("download.id"), nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    source_list: Mapped[SourceList] = relationship(back_populates="tracks", foreign_keys=[source_list_id])


class Download(Base):
    __tablename__ = "download"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    track_entry_id: Mapped[int] = mapped_column(ForeignKey("track_entry.id", ondelete="CASCADE"))
    job_id: Mapped[int | None] = mapped_column(ForeignKey("job.id"), nullable=True)
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(16))
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sldl_match_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Job(Base):
    __tablename__ = "job"
    __table_args__ = (
        Index("ix_job_state_sched_pri", "state", "scheduled_for", "priority"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[str] = mapped_column(String(32))
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    state: Mapped[str] = mapped_column(String(16), default="pending")
    priority: Mapped[int] = mapped_column(Integer, default=100)
    source_list_id: Mapped[int | None] = mapped_column(ForeignKey("source_list.id"), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    log_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    progress_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    pid: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class OAuthAccount(Base):
    __tablename__ = "oauth_account"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String(32))
    account_label: Mapped[str] = mapped_column(String(128))
    access_token_enc: Mapped[bytes] = mapped_column(LargeBinary)
    refresh_token_enc: Mapped[bytes] = mapped_column(LargeBinary)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    scopes: Mapped[str] = mapped_column(Text, default="")
    remote_user_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    remote_display: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class LibraryFile(Base):
    __tablename__ = "library_file"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    path: Mapped[str] = mapped_column(Text, unique=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mtime: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    artist: Mapped[str | None] = mapped_column(String(512), nullable=True)
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    album: Mapped[str | None] = mapped_column(String(512), nullable=True)
    duration_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    acoustid_fp: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_list_id: Mapped[int | None] = mapped_column(ForeignKey("source_list.id"), nullable=True)
    matched_track_id: Mapped[int | None] = mapped_column(ForeignKey("track_entry.id"), nullable=True)


class Setting(Base):
    __tablename__ = "setting"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value_json: Mapped[Any] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
