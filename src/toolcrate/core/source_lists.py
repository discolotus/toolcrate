"""SourceListService: CRUD over the source_list table with URL detection.

URL detection rules (Phase 1):
  - URL matches open.spotify.com/playlist/<id>  -> source_type=spotify_playlist
  - URL matches youtube.com/watch?v=<id> or youtu.be/<id>  -> source_type=youtube_djset
  - source_type='manual' is allowed without a URL
  - Anything else -> ValidationError

The service does NOT contact Spotify/YouTube here; it only parses and
persists. SyncService and RecognitionService do the network work.
"""

from __future__ import annotations

import os
import re
import unicodedata
from typing import Any
from urllib.parse import parse_qs, urlparse

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from toolcrate.db.models import SourceList

from .exceptions import IntegrationError, NotFound, ValidationError
from .spotify import SpotifyPlaylist, parse_playlist_url

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(name: str) -> str:
    n = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    return _SLUG_RE.sub("-", n).strip("-")


_SOURCE_DIR = {
    "spotify_playlist": "spotify",
    "youtube_djset": "dj-sets",
    "manual": "manual",
}


def default_download_path(music_root: str, source_type: str, name: str) -> str:
    return f"{music_root.rstrip('/')}/{_SOURCE_DIR[source_type]}/{slugify(name)}"


def _read_spotify_credentials() -> tuple[str, str]:
    cid = os.environ.get("SPOTIFY_CLIENT_ID", "")
    csec = os.environ.get("SPOTIFY_CLIENT_SECRET", "")
    if not cid or not csec:
        raise IntegrationError(
            "spotify credentials not configured: set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET"
        )
    return cid, csec


def _detect_source_type(url: str) -> tuple[str, str]:
    """Return (source_type, external_id) or raise ValidationError."""
    if pid := parse_playlist_url(url):
        return "spotify_playlist", pid
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host in {"www.youtube.com", "youtube.com", "m.youtube.com"}:
        vid = parse_qs(parsed.query).get("v", [None])[0]
        if vid:
            return "youtube_djset", vid
    if host == "youtu.be":
        vid = parsed.path.lstrip("/")
        if vid:
            return "youtube_djset", vid
    raise ValidationError(f"unrecognized source URL: {url!r}")


class SourceListService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        music_root: str,
    ) -> None:
        self._sf = session_factory
        self._music_root = music_root

    async def create(
        self,
        *,
        name: str,
        source_url: str = "",
        source_type: str | None = None,
        download_path: str | None = None,
        sync_interval: str = "manual",
        oauth_account_id: int | None = None,
    ) -> SourceList:
        if source_type is None:
            if not source_url:
                raise ValidationError("source_type or source_url required")
            source_type, external_id = _detect_source_type(source_url)
        else:
            if source_type not in _SOURCE_DIR:
                raise ValidationError(f"unknown source_type: {source_type!r}")
            external_id = ""
            if source_url:
                _, external_id = _detect_source_type(source_url)
        path = download_path or default_download_path(self._music_root, source_type, name)
        async with self._sf() as session:
            row = SourceList(
                name=name,
                source_type=source_type,
                source_url=source_url,
                external_id=external_id,
                download_path=path,
                sync_interval=sync_interval,
                oauth_account_id=oauth_account_id,
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return row

    async def get(self, list_id: int) -> SourceList:
        async with self._sf() as session:
            row = await session.get(SourceList, list_id)
            if row is None:
                raise NotFound(f"source_list {list_id}")
            return row

    async def list(
        self, *, source_type: str | None = None, enabled: bool | None = None,
    ) -> list[SourceList]:
        async with self._sf() as session:
            stmt = select(SourceList)
            if source_type is not None:
                stmt = stmt.where(SourceList.source_type == source_type)
            if enabled is not None:
                stmt = stmt.where(SourceList.enabled == enabled)
            return list((await session.execute(stmt)).scalars())

    async def update(self, list_id: int, fields: dict[str, Any]) -> SourceList:
        allowed = {"name", "download_path", "sync_interval", "enabled",
                   "oauth_account_id", "metadata_json", "last_sync_status",
                   "last_synced_at", "last_error"}
        invalid = set(fields) - allowed
        if invalid:
            raise ValidationError(f"unknown fields: {sorted(invalid)}")
        async with self._sf() as session:
            row = await session.get(SourceList, list_id)
            if row is None:
                raise NotFound(f"source_list {list_id}")
            for k, v in fields.items():
                setattr(row, k, v)
            await session.commit()
            await session.refresh(row)
            return row

    async def delete(self, list_id: int) -> None:
        async with self._sf() as session:
            row = await session.get(SourceList, list_id)
            if row is None:
                raise NotFound(f"source_list {list_id}")
            await session.delete(row)
            await session.commit()

    async def preview_url(self, url: str) -> SpotifyPlaylist:
        """Fetch playlist metadata for the Add-list autofill UI without persisting.

        Raises ValidationError if the URL doesn't match a supported source type.
        Raises NotFound if the remote refuses (404 / no such playlist).
        """
        from toolcrate.core.spotify import SpotifyClient

        playlist_id = parse_playlist_url(url)
        if playlist_id is None:
            raise ValidationError("unsupported source url")
        client_id, client_secret = _read_spotify_credentials()
        sp = SpotifyClient(client_id=client_id, client_secret=client_secret)
        try:
            return await sp.fetch_playlist(playlist_id)
        except IntegrationError as e:
            msg = str(e).lower()
            if "404" in msg:
                raise NotFound("playlist not found on remote") from e
            raise
        finally:
            await sp.aclose()
