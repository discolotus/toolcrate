# tests/unit/core/test_models.py
import pytest
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from toolcrate.db.models import Base, SourceList, TrackEntry, Job
from toolcrate.db.session import create_engine_for_url, get_async_session_factory


@pytest.fixture
async def session():
    engine = create_engine_for_url("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = get_async_session_factory(engine)
    async with factory() as s:
        yield s
    await engine.dispose()


async def test_source_list_round_trip(session: AsyncSession):
    sl = SourceList(
        name="Late Night",
        source_type="spotify_playlist",
        source_url="https://open.spotify.com/playlist/abc",
        external_id="abc",
        download_path="/tmp/music/spotify/late-night",
        sync_interval="manual",
    )
    session.add(sl)
    await session.commit()
    await session.refresh(sl)
    assert sl.id is not None
    assert sl.enabled is True
    assert sl.created_at is not None


async def test_track_entry_links_to_source_list(session: AsyncSession):
    sl = SourceList(name="x", source_type="manual", source_url="", external_id="",
                    download_path="/tmp/x", sync_interval="manual")
    session.add(sl)
    await session.flush()
    t = TrackEntry(source_list_id=sl.id, position=1, artist="A", title="B")
    session.add(t)
    await session.commit()
    await session.refresh(t)
    assert t.download_status == "pending"
    assert t.first_seen_at is not None


async def test_job_defaults(session: AsyncSession):
    j = Job(type="sync_list", payload_json={"list_id": 1})
    session.add(j)
    await session.commit()
    await session.refresh(j)
    assert j.state == "pending"
    assert j.attempts == 0
    assert j.max_attempts == 3
    assert j.scheduled_for is not None
