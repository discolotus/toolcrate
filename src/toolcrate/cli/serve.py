"""`toolcrate serve` — boot the FastAPI daemon."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import secrets
from pathlib import Path

import click
import uvicorn

from toolcrate.core.config import SettingsStore
from toolcrate.core.downloads import DownloadService
from toolcrate.core.events import EventBus
from toolcrate.core.jobs import JobQueue, Worker
from toolcrate.core.source_lists import SourceListService
from toolcrate.core.sync import SyncService
from toolcrate.core.worker_handlers import build_handlers
from toolcrate.db.session import create_engine_for_url, get_async_session_factory
from toolcrate.web.app import AppDeps, create_app
from toolcrate.web.routers.events import build_router as build_events
from toolcrate.web.routers.health import build_router as build_health
from toolcrate.web.routers.jobs import build_router as build_jobs
from toolcrate.web.routers.lists import build_router as build_lists
from toolcrate.web.routers.tracks import build_router as build_tracks


logger = logging.getLogger("toolcrate.serve")


def _toolcrate_home() -> Path:
    return Path(os.environ.get("TOOLCRATE_HOME") or os.path.expanduser("~/.local/share/toolcrate"))


def _config_dir() -> Path:
    if (override := os.environ.get("TOOLCRATE_CONFIG_DIR")):
        return Path(override)
    return Path(os.path.expanduser("~/.config/toolcrate"))


def _ensure_api_token(config_dir: Path) -> str:
    token_file = config_dir / "api-token"
    config_dir.mkdir(parents=True, exist_ok=True)
    if token_file.exists():
        return token_file.read_text().strip()
    token = secrets.token_urlsafe(32)
    token_file.write_text(token)
    os.chmod(token_file, 0o600)
    return token


def _find_sldl() -> str:
    from toolcrate.cli import binary_manager  # existing
    try:
        return str(binary_manager.get_binary_path("sldl"))
    except Exception:
        return "sldl"


@click.command()
@click.option("--host", default="127.0.0.1", show_default=True)
@click.option("--port", default=48721, type=int, show_default=True)
@click.option("--reload/--no-reload", default=False)
def serve(host: str, port: int, reload: bool) -> None:
    """Run the toolcrate web/API daemon."""
    home = _toolcrate_home()
    home.mkdir(parents=True, exist_ok=True)
    db_path = home / "toolcrate.db"

    config_dir = _config_dir()
    api_token = _ensure_api_token(config_dir)
    api_token_hash = hashlib.sha256(api_token.encode()).hexdigest()

    db_url = f"sqlite+aiosqlite:///{db_path}"
    sync_db_url = f"sqlite:///{db_path}"

    # Apply migrations using the sync URL (Alembic doesn't speak aiosqlite).
    from alembic import command as alembic_command
    from alembic.config import Config as AlembicConfig
    cfg = AlembicConfig(str(Path(__file__).resolve().parents[3] / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", sync_db_url)
    alembic_command.upgrade(cfg, "head")

    engine = create_engine_for_url(db_url)
    sf = get_async_session_factory(engine)

    settings = SettingsStore(sf)
    asyncio.run(settings.seed_defaults({
        "music_root": os.path.expanduser("~/Music/toolcrate"),
        "server_port": port,
        "sldl_extra_args": [],
    }))

    music_root = asyncio.run(
        settings.get("music_root", default=os.path.expanduser("~/Music/toolcrate"))
    )
    sldl_extra_args = asyncio.run(
        settings.get("sldl_extra_args", default=[])
    )

    bus = EventBus()
    src = SourceListService(sf, music_root=str(music_root))
    queue = JobQueue(sf)
    sldl_path = _find_sldl()
    sync_service = SyncService(sf, bus=bus, sldl_path=sldl_path,
                               sldl_extra_args=sldl_extra_args, src_service=src)
    download_service = DownloadService(sf, bus=bus, sldl_path=sldl_path,
                                       sldl_extra_args=sldl_extra_args)

    handlers = build_handlers(session_factory=sf, bus=bus,
                              sync_service=sync_service,
                              recognition_service=None,
                              download_service=download_service,
                              library_service=None)
    worker = Worker(sf, queue, bus, handlers=handlers)

    deps = AppDeps(
        api_token_hash=api_token_hash,
        allowed_hosts={"localhost", "127.0.0.1"},
        routers=[
            build_health(version="0.1.0", token_hash=api_token_hash),
            build_lists(src=src, queue=queue, token_hash=api_token_hash),
            build_tracks(src=src, session_factory=sf, queue=queue, token_hash=api_token_hash),
            build_jobs(queue=queue, session_factory=sf, token_hash=api_token_hash),
            build_events(bus=bus, token_hash=api_token_hash),
        ],
    )
    app = create_app(deps)

    @app.on_event("startup")
    async def _start_worker():
        app.state.worker_task = asyncio.create_task(worker.run())

    @app.on_event("shutdown")
    async def _stop_worker():
        worker.stop()
        if hasattr(app.state, "worker_task"):
            try:
                await asyncio.wait_for(app.state.worker_task, timeout=5)
            except asyncio.TimeoutError:
                pass

    click.echo(f"toolcrate serving at http://{host}:{port}")
    click.echo(f"API token: {api_token}")
    uvicorn.run(app, host=host, port=port, reload=reload, log_level="info")
