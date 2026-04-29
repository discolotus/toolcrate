import pytest
from toolcrate.core.config import SettingsStore
from toolcrate.db.models import Base
from toolcrate.db.session import create_engine_for_url, get_async_session_factory


@pytest.fixture
async def store():
    engine = create_engine_for_url("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = get_async_session_factory(engine)
    yield SettingsStore(factory)
    await engine.dispose()


async def test_get_default_when_unset(store: SettingsStore):
    assert await store.get("music_root", default="/x") == "/x"


async def test_set_then_get(store: SettingsStore):
    await store.set("music_root", "/Users/me/Music")
    assert await store.get("music_root") == "/Users/me/Music"


async def test_set_dict_value(store: SettingsStore):
    await store.set("sldl_defaults", {"listen-port": 50300, "fast-search": True})
    assert (await store.get("sldl_defaults"))["fast-search"] is True


async def test_seed_defaults_idempotent(store: SettingsStore):
    await store.seed_defaults({"music_root": "/m", "server_port": 48721})
    await store.set("music_root", "/changed")
    await store.seed_defaults({"music_root": "/m", "server_port": 48721})
    # seed must not overwrite existing values
    assert await store.get("music_root") == "/changed"
    assert await store.get("server_port") == 48721
