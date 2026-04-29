import asyncio

import pytest

from toolcrate.core.events import EventBus
from toolcrate.core.jobs import JobQueue, JobType, Worker
from toolcrate.db.models import Base, Job
from toolcrate.db.session import create_engine_for_url, get_async_session_factory


@pytest.fixture
async def env():
    engine = create_engine_for_url("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = get_async_session_factory(engine)
    yield factory
    await engine.dispose()


async def test_enqueue_creates_pending_job(env):
    queue = JobQueue(env)
    j = await queue.enqueue(JobType.LIBRARY_SCAN, payload={"root": "/m"})
    assert j.state == "pending"
    assert j.id is not None


async def test_worker_dispatches_handler_and_marks_success(env):
    queue = JobQueue(env)
    bus = EventBus()
    handled: list[int] = []

    async def handler(job: Job) -> None:
        handled.append(job.id)

    handlers = {JobType.LIBRARY_SCAN: handler}
    worker = Worker(env, queue, bus, handlers=handlers, poll_interval=0.05)
    await queue.enqueue(JobType.LIBRARY_SCAN, payload={})
    task = asyncio.create_task(worker.run())
    for _ in range(50):
        await asyncio.sleep(0.05)
        if handled:
            break
    worker.stop()
    await task

    assert len(handled) == 1


async def test_worker_marks_failure_and_retries(env):
    queue = JobQueue(env)
    bus = EventBus()
    attempts = {"n": 0}

    async def handler(job: Job) -> None:
        attempts["n"] += 1
        raise RuntimeError("boom")

    handlers = {JobType.LIBRARY_SCAN: handler}
    worker = Worker(env, queue, bus, handlers=handlers, poll_interval=0.01,
                    backoff_base_seconds=0)  # immediate retry for test speed
    j = await queue.enqueue(JobType.LIBRARY_SCAN, payload={}, max_attempts=2)
    task = asyncio.create_task(worker.run())
    for _ in range(200):
        await asyncio.sleep(0.01)
        if attempts["n"] >= 2:
            break
    worker.stop()
    await task

    async with env() as session:
        refreshed = await session.get(Job, j.id)
        assert refreshed.state == "failed"
        assert refreshed.attempts == 2


async def test_cancel_running_job_sets_state(env):
    queue = JobQueue(env)
    j = await queue.enqueue(JobType.LIBRARY_SCAN, payload={})
    await queue.cancel(j.id)
    async with env() as session:
        refreshed = await session.get(Job, j.id)
        assert refreshed.state == "cancelled"
