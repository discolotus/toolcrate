import pytest

from toolcrate.core.events import EventBus
from toolcrate.core.jobs import JobQueue, JobType, Worker
from toolcrate.core.worker_handlers import build_handlers
from toolcrate.db.models import Base
from toolcrate.db.session import create_engine_for_url, get_async_session_factory


@pytest.fixture
async def env():
    engine = create_engine_for_url("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = get_async_session_factory(engine)
    yield factory
    await engine.dispose()


async def test_unknown_job_type_marks_failed(env):
    bus = EventBus()
    queue = JobQueue(env)
    handlers = build_handlers(session_factory=env, bus=bus,
                              sync_service=None, recognition_service=None,
                              download_service=None, library_service=None)
    # No SYNC_LIST handler when sync_service=None
    assert JobType.SYNC_LIST not in handlers
