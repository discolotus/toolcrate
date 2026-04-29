# tests/unit/core/test_source_lists.py
import pytest

from toolcrate.core.source_lists import SourceListService, slugify, default_download_path
from toolcrate.core.exceptions import NotFound, ValidationError
from toolcrate.db.models import Base
from toolcrate.db.session import create_engine_for_url, get_async_session_factory


@pytest.fixture
async def svc():
    engine = create_engine_for_url("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = get_async_session_factory(engine)
    yield SourceListService(factory, music_root="/m")
    await engine.dispose()


def test_slugify_basic():
    assert slugify("Late Night Vibes!!") == "late-night-vibes"
    assert slugify("  Multiple   Spaces  ") == "multiple-spaces"
    assert slugify("Café Sessions") == "cafe-sessions"


def test_default_download_path():
    assert default_download_path("/m", "spotify_playlist", "Late Night") == "/m/spotify/late-night"
    assert default_download_path("/m", "youtube_djset", "Boiler Room — DJ X") == "/m/dj-sets/boiler-room-dj-x"


async def test_create_with_explicit_url_detects_spotify(svc: SourceListService):
    sl = await svc.create(name="Late Night",
                          source_url="https://open.spotify.com/playlist/abc123")
    assert sl.source_type == "spotify_playlist"
    assert sl.external_id == "abc123"
    assert sl.download_path == "/m/spotify/late-night"


async def test_create_youtube_djset(svc: SourceListService):
    sl = await svc.create(name="Boiler Room",
                          source_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                          source_type="youtube_djset")
    assert sl.source_type == "youtube_djset"
    assert sl.external_id == "dQw4w9WgXcQ"


async def test_create_manual_with_no_url(svc: SourceListService):
    sl = await svc.create(name="Wishlist", source_type="manual")
    assert sl.source_type == "manual"
    assert sl.source_url == ""


async def test_create_rejects_unknown_url(svc: SourceListService):
    with pytest.raises(ValidationError):
        await svc.create(name="x", source_url="https://example.com/whatever")


async def test_get_returns_existing(svc: SourceListService):
    sl = await svc.create(name="x", source_type="manual")
    fetched = await svc.get(sl.id)
    assert fetched.id == sl.id


async def test_get_missing_raises_not_found(svc: SourceListService):
    with pytest.raises(NotFound):
        await svc.get(999)


async def test_list_filters_by_type(svc: SourceListService):
    await svc.create(name="a", source_url="https://open.spotify.com/playlist/A")
    await svc.create(name="b", source_type="manual")
    spotify_only = await svc.list(source_type="spotify_playlist")
    assert len(spotify_only) == 1


async def test_update_overrides_path(svc: SourceListService):
    sl = await svc.create(name="x", source_type="manual")
    updated = await svc.update(sl.id, {"download_path": "/m/custom"})
    assert updated.download_path == "/m/custom"


async def test_delete_removes_row(svc: SourceListService):
    sl = await svc.create(name="x", source_type="manual")
    await svc.delete(sl.id)
    with pytest.raises(NotFound):
        await svc.get(sl.id)
