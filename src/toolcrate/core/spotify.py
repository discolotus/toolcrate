"""Spotify Web API client (public client_credentials).

Only what Phase 1 needs: parse a playlist URL to id, fetch playlist and
tracks anonymously. OAuth-bound user-context calls land in Phase 3 — same
class will gain a `with_token(...)` constructor then.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

import httpx

from .exceptions import IntegrationError, ValidationError

_PLAYLIST_RE = re.compile(r"open\.spotify\.com/playlist/([A-Za-z0-9]+)")


def parse_playlist_url(url: str) -> str | None:
    m = _PLAYLIST_RE.search(url)
    return m.group(1) if m else None


@dataclass(slots=True)
class SpotifyTrack:
    spotify_track_id: str
    artist: str
    title: str
    album: str
    isrc: str | None
    duration_sec: int


@dataclass(slots=True)
class SpotifyPlaylist:
    id: str
    name: str
    owner: str
    image_url: str | None
    tracks: list[SpotifyTrack]


class SpotifyClient:
    AUTH_URL = "https://accounts.spotify.com/api/token"
    API_BASE = "https://api.spotify.com/v1"

    def __init__(self, *, client_id: str, client_secret: str,
                 http: httpx.AsyncClient | None = None) -> None:
        if not client_id or not client_secret:
            raise ValidationError("client_id/client_secret required")
        self._cid = client_id
        self._csec = client_secret
        self._http = http or httpx.AsyncClient(timeout=30)
        self._token: str | None = None

    async def aclose(self) -> None:
        await self._http.aclose()

    async def _ensure_token(self) -> str:
        if self._token:
            return self._token
        resp = await self._http.post(
            self.AUTH_URL,
            data={"grant_type": "client_credentials"},
            auth=(self._cid, self._csec),
        )
        if resp.status_code != 200:
            raise IntegrationError(f"spotify auth failed: {resp.status_code} {resp.text}")
        self._token = resp.json()["access_token"]
        return self._token

    async def fetch_playlist(self, playlist_id: str) -> SpotifyPlaylist:
        token = await self._ensure_token()
        resp = await self._http.get(
            f"{self.API_BASE}/playlists/{playlist_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        if resp.status_code != 200:
            raise IntegrationError(f"spotify fetch_playlist {playlist_id}: {resp.status_code}")
        payload = resp.json()
        items = payload.get("tracks", {}).get("items", [])
        tracks = [_normalize(it["track"]) for it in items if it.get("track")]
        # NOTE: pagination via tracks.next is handled in Phase 3 once OAuth lands;
        # public Phase-1 path tolerates first-page-only for typical playlists.
        return SpotifyPlaylist(
            id=payload["id"],
            name=payload["name"],
            owner=(payload.get("owner") or {}).get("display_name", ""),
            image_url=(payload.get("images") or [{}])[0].get("url"),
            tracks=tracks,
        )


def _normalize(track: dict) -> SpotifyTrack:
    artists: Iterable[dict] = track.get("artists") or []
    artist_names = ", ".join(a.get("name", "") for a in artists if a.get("name"))
    return SpotifyTrack(
        spotify_track_id=track.get("id", ""),
        artist=artist_names,
        title=track.get("name", ""),
        album=(track.get("album") or {}).get("name", ""),
        isrc=(track.get("external_ids") or {}).get("isrc"),
        duration_sec=int((track.get("duration_ms") or 0) / 1000),
    )
