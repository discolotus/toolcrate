import os
from pathlib import Path
import pytest
from sqlalchemy import select

from toolcrate.core.events import EventBus
from toolcrate.core.downloads import DownloadService
from toolcrate.core.source_lists import SourceListService
from toolcrate.db.models import Base, TrackEntry
from toolcrate.db.session import create_engine_for_url, get_async_session_factory


@pytest.fixture
async def env():
    engine = create_engine_for_url("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = get_async_session_factory(engine)
    yield factory
    await engine.dispose()


@pytest.fixture
def fake_sldl(tmp_path: Path) -> Path:
    """Shell stub that emits canned progress and writes a canned index file.

    NOTE: literal string (not textwrap.dedent) — the EOF heredoc body is unindented
    and would defeat dedent, leaving the shebang indented and exec-broken.
    """
    script = tmp_path / "fake-sldl"
    script.write_text(
        '#!/usr/bin/env bash\n'
        'set -eu\n'
        'idx=""; next=0\n'
        'for a in "$@"; do\n'
        '  if [ "$next" = "1" ]; then idx="$a"; next=0; continue; fi\n'
        '  if [ "$a" = "--index-path" ]; then next=1; fi\n'
        'done\n'
        'echo "Searching: A - B"\n'
        'echo "Succeeded: A - B"\n'
        'if [ -n "$idx" ]; then\n'
        '  mkdir -p "$(dirname "$idx")"\n'
        '  echo "/m/x.mp3,A,B,200,1,1," > "$idx"\n'
        'fi\n'
    )
    os.chmod(script, 0o755)
    return script


async def test_run_single_track_marks_done(env, fake_sldl, tmp_path):
    src = SourceListService(env, music_root=str(tmp_path / "m"))
    sl = await src.create(name="x", source_type="manual")
    async with env() as session:
        t = TrackEntry(source_list_id=sl.id, position=1, artist="A", title="B")
        session.add(t)
        await session.commit()
        await session.refresh(t)
        track_id = t.id

    bus = EventBus()
    svc = DownloadService(env, bus=bus, sldl_path=str(fake_sldl), sldl_extra_args=[])
    await svc.run_single_track(track_id, log_path=str(tmp_path / "log.txt"))

    async with env() as session:
        row = (await session.execute(select(TrackEntry).where(TrackEntry.id == track_id)))\
            .scalar_one()
        assert row.download_status == "done"
