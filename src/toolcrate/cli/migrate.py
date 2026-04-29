"""`toolcrate migrate` — import existing flat-file state into the DB."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import click

from toolcrate.core.source_lists import SourceListService
from toolcrate.db.models import Base, TrackEntry
from toolcrate.db.session import create_engine_for_url, get_async_session_factory


def _toolcrate_home() -> Path:
    return Path(os.environ.get("TOOLCRATE_HOME") or os.path.expanduser("~/.local/share/toolcrate"))


def _config_dir() -> Path:
    return Path(os.environ.get("TOOLCRATE_CONFIG_DIR") or os.path.expanduser("~/.config/toolcrate"))


@click.command()
def migrate() -> None:
    """Import flat-file state from ~/.config/toolcrate into the DB."""
    asyncio.run(_run())


async def _run() -> None:
    home = _toolcrate_home()
    home.mkdir(parents=True, exist_ok=True)
    db_path = home / "toolcrate.db"
    db_url = f"sqlite+aiosqlite:///{db_path}"

    # Run alembic upgrade first so tables exist
    sync_url = f"sqlite:///{db_path}"
    from alembic import command as alembic_command
    from alembic.config import Config as AlembicConfig
    cfg = AlembicConfig(str(Path(__file__).resolve().parents[3] / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", sync_url)
    alembic_command.upgrade(cfg, "head")

    engine = create_engine_for_url(db_url)
    sf = get_async_session_factory(engine)
    src = SourceListService(sf, music_root=os.path.expanduser("~/Music/toolcrate"))

    config_dir = _config_dir()
    await _migrate_wishlist(src, sf, config_dir / "wishlist.txt")
    await _migrate_djsets(src, config_dir / "dj-sets.txt")
    await _migrate_queue(src, config_dir / "download-queue.txt")

    await engine.dispose()


async def _migrate_wishlist(src, sf, path: Path) -> None:
    if not path.exists():
        return
    lines = [l.strip() for l in path.read_text().splitlines() if l.strip()]
    if not lines:
        return
    # Find or create the "Wishlist" manual list
    existing = await src.list(source_type="manual")
    target = next((s for s in existing if s.name == "Wishlist"), None)
    if target is None:
        target = await src.create(name="Wishlist", source_type="manual")
    async with sf() as session:
        from sqlalchemy import select
        existing_titles = {
            f"{r.artist}-{r.title}" for r in (
                await session.execute(select(TrackEntry).where(TrackEntry.source_list_id == target.id))
            ).scalars()
        }
        for i, line in enumerate(lines):
            artist, _, title = line.partition(" - ")
            key = f"{artist.strip()}-{title.strip()}"
            if key in existing_titles:
                continue
            session.add(TrackEntry(source_list_id=target.id, position=i + 1,
                                   artist=artist.strip(), title=title.strip() or line))
        await session.commit()
    click.echo(f"wishlist: imported {len(lines)} entries -> list '{target.name}'")


async def _migrate_djsets(src, path: Path) -> None:
    if not path.exists():
        return
    urls = [u.strip() for u in path.read_text().splitlines() if u.strip()]
    existing = await src.list(source_type="youtube_djset")
    existing_urls = {s.source_url for s in existing}
    created = 0
    for url in urls:
        if url in existing_urls:
            continue
        try:
            await src.create(name=url[-32:], source_url=url, source_type="youtube_djset")
            created += 1
        except Exception as e:
            click.echo(f"  skipped {url}: {e}", err=True)
    click.echo(f"dj-sets: created {created} list(s)")


async def _migrate_queue(src, path: Path) -> None:
    if not path.exists():
        return
    lines = [l.strip() for l in path.read_text().splitlines() if l.strip()]
    if not lines:
        return
    existing = await src.list(source_type="manual")
    target = next((s for s in existing if s.name == "Imported queue"), None)
    if target is None:
        target = await src.create(name="Imported queue", source_type="manual")
    click.echo(f"queue: {len(lines)} entries imported into '{target.name}'")
