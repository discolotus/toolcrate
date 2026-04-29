# tests/unit/core/test_spotify_client.py
import json
from pathlib import Path

import httpx
import pytest
import respx

from toolcrate.core.spotify import SpotifyClient, parse_playlist_url

FIX = Path(__file__).resolve().parents[2] / "fixtures"


def test_parse_playlist_url_classic():
    assert parse_playlist_url("https://open.spotify.com/playlist/abc123") == "abc123"


def test_parse_playlist_url_with_query():
    assert parse_playlist_url("https://open.spotify.com/playlist/abc123?si=foo") == "abc123"


def test_parse_playlist_url_invalid():
    assert parse_playlist_url("https://example.com/foo") is None


@respx.mock
async def test_fetch_playlist_returns_normalized_tracks():
    respx.post("https://accounts.spotify.com/api/token").mock(
        return_value=httpx.Response(200, json={"access_token": "tk", "expires_in": 3600})
    )
    payload = json.loads((FIX / "spotify_playlist.json").read_text())
    respx.get("https://api.spotify.com/v1/playlists/abc123").mock(
        return_value=httpx.Response(200, json=payload)
    )

    client = SpotifyClient(client_id="cid", client_secret="csec")
    result = await client.fetch_playlist("abc123")
    await client.aclose()

    assert result.id == "abc123"
    assert result.name == "Late Night"
    assert len(result.tracks) == 2
    assert result.tracks[0].artist == "Daft Punk"
    assert result.tracks[0].isrc == "FR0010100001"
    assert result.tracks[0].duration_sec == 320
