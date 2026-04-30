import pytest
from sqlalchemy import text

from toolcrate.db.session import create_engine_for_url, get_async_session_factory


@pytest.mark.asyncio
async def test_session_can_execute_against_in_memory_sqlite():
    engine = create_engine_for_url("sqlite+aiosqlite:///:memory:")
    factory = get_async_session_factory(engine)
    async with factory() as session:
        result = await session.execute(text("SELECT 1 AS n"))
        row = result.one()
        assert row.n == 1
    await engine.dispose()
