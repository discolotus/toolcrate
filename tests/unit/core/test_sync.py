# tests/unit/core/test_sync.py
import os
from pathlib import Path

import pytest

from toolcrate.core.events import EventBus
from toolcrate.core.source_lists import SourceListService
from toolcrate.core.sync import SyncService
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

    The stub looks for `--index-path <p>` in argv and writes there.
    """
    script = tmp_path / "fake-sldl"
    # NB: literal string (no dedent) — the EOF heredoc body is unindented and
    # would defeat textwrap.dedent, leaving the shebang indented and exec-broken.
    script.write_text(
        '#!/usr/bin/env bash\n'
        'set -eu\n'
        'idx=""\n'
        'next_is_idx=0\n'
        'for arg in "$@"; do\n'
        '  if [ "$next_is_idx" = "1" ]; then idx="$arg"; next_is_idx=0; continue; fi\n'
        '  if [ "$arg" = "--index-path" ]; then next_is_idx=1; fi\n'
        'done\n'
        'echo "Searching: Daft Punk - One More Time"\n'
        'echo "Downloading: Daft Punk - One More Time -- u@h (5 MB)"\n'
        'echo "Succeeded: Daft Punk - One More Time"\n'
        'echo "Searching: Daft Punk - Around the World"\n'
        'echo "Failed: Daft Punk - Around the World -- NoSuitableFileFound"\n'
        'echo "Done. 1 succeeded, 1 failed."\n'
        'if [ -n "$idx" ]; then\n'
        '  mkdir -p "$(dirname "$idx")"\n'
        '  cat > "$idx" <<EOF\n'
        '/m/x/01.mp3,Daft Punk,One More Time,320,1,1,\n'
        ',Daft Punk,Around the World,440,1,2,NoSuitableFileFound\n'
        'EOF\n'
        'fi\n'
    )
    os.chmod(script, 0o755)
    return script


async def test_run_for_list_invokes_sldl_and_updates_tracks(env, fake_sldl, tmp_path):
    src = SourceListService(env, music_root=str(tmp_path / "m"))
    sl = await src.create(name="Late Night",
                          source_url="https://open.spotify.com/playlist/abc")
    # seed tracks (in real flow, SyncService.refresh_metadata does this)
    async with env() as session:
        session.add_all([
            TrackEntry(source_list_id=sl.id, position=1, artist="Daft Punk", title="One More Time"),
            TrackEntry(source_list_id=sl.id, position=2, artist="Daft Punk", title="Around the World"),
        ])
        await session.commit()

    bus = EventBus()
    sync = SyncService(env, bus=bus, sldl_path=str(fake_sldl),
                       sldl_extra_args=[], src_service=src)
    job_id = 42
    await sync.run_for_list(sl.id, job_id=job_id, log_path=str(tmp_path / "log.txt"))

    async with env() as session:
        from sqlalchemy import select
        rows = (await session.execute(
            select(TrackEntry).where(TrackEntry.source_list_id == sl.id)
                              .order_by(TrackEntry.position)
        )).scalars().all()
        assert rows[0].download_status == "done"
        assert rows[1].download_status == "failed"

    log = (tmp_path / "log.txt").read_text()
    assert "Succeeded: Daft Punk - One More Time" in log
