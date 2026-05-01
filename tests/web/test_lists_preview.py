"""POST /api/v1/lists/preview — autofill helper for the Add-list dialog."""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from toolcrate.core.spotify import SpotifyPlaylist, SpotifyTrack
from toolcrate.web.app import AppDeps, create_app
from toolcrate.web.routers.lists import build_router as build_lists


class _StubSrc:
    """Stand-in for SourceListService that only needs preview_url to work."""

    def __init__(self) -> None:
        self.preview_url = AsyncMock()


@pytest.fixture()
def stub_src() -> _StubSrc:
    return _StubSrc()


@pytest.fixture()
def stub_queue() -> object:
    class _Q:  # noqa: D401
        async def enqueue(self, *_a, **_kw):
            raise AssertionError("not used in preview tests")
    return _Q()


@pytest.fixture()
def client(stub_src: _StubSrc, stub_queue: object) -> Iterator[TestClient]:
    token = "tok-1"
    th = hashlib.sha256(token.encode()).hexdigest()
    deps = AppDeps(
        api_token_hash=th,
        allowed_hosts={"localhost", "testserver", "127.0.0.1"},
        routers=[build_lists(src=stub_src, queue=stub_queue, token_hash=th)],  # type: ignore[arg-type]
    )
    c = TestClient(create_app(deps))
    yield c


@pytest.fixture()
def auth() -> dict:
    return {"Authorization": "Bearer tok-1"}


def test_preview_spotify_playlist_returns_metadata(
    client: TestClient, stub_src: _StubSrc, auth: dict
) -> None:
    stub_src.preview_url.return_value = SpotifyPlaylist(
        id="abc123",
        name="Daft Punk Essentials",
        owner="spotify",
        image_url="https://i.scdn.co/x.jpg",
        tracks=[
            SpotifyTrack("t1", "Daft Punk", "One More Time", "Discovery", "GBARL0001234", 320),
            SpotifyTrack("t2", "Daft Punk", "Aerodynamic", "Discovery", "GBARL0001235", 213),
        ],
    )
    resp = client.post(
        "/api/v1/lists/preview",
        json={"source_url": "https://open.spotify.com/playlist/abc123"},
        headers=auth,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body == {
        "source_type": "spotify_playlist",
        "external_id": "abc123",
        "name": "Daft Punk Essentials",
        "owner": "spotify",
        "total_tracks": 2,
        "art_url": "https://i.scdn.co/x.jpg",
    }
    stub_src.preview_url.assert_awaited_once_with("https://open.spotify.com/playlist/abc123")


def test_preview_unrecognized_url_returns_400(
    client: TestClient, stub_src: _StubSrc, auth: dict
) -> None:
    from toolcrate.core.exceptions import ValidationError

    stub_src.preview_url.side_effect = ValidationError("unsupported source url")
    resp = client.post(
        "/api/v1/lists/preview",
        json={"source_url": "https://not-spotify.example/foo"},
        headers=auth,
    )
    assert resp.status_code == 400
    assert "unsupported" in resp.json()["detail"].lower()


def test_preview_remote_404_returns_404(
    client: TestClient, stub_src: _StubSrc, auth: dict
) -> None:
    from toolcrate.core.exceptions import NotFound

    stub_src.preview_url.side_effect = NotFound("playlist missing")
    resp = client.post(
        "/api/v1/lists/preview",
        json={"source_url": "https://open.spotify.com/playlist/zzz"},
        headers=auth,
    )
    assert resp.status_code == 404


def test_preview_requires_auth(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/lists/preview",
        json={"source_url": "https://open.spotify.com/playlist/abc"},
    )
    assert resp.status_code == 401
