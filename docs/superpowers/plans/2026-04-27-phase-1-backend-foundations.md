# Phase 1 — Backend Foundations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the headless backend (DB, services, FastAPI app, job worker, scheduler, migration CLI) for the toolcrate music manager. No frontend in this phase. Existing CLI behavior preserved.

**Architecture:** Single FastAPI daemon (`toolcrate serve`) hosts API + APScheduler + asyncio worker + SSE bus in one process, talking to SQLite via SQLAlchemy 2.x. Domain logic lives in `core/`, web glue in `web/`, persistence in `db/`. Existing CLI commands keep working unchanged.

**Tech Stack:** Python 3.10+, FastAPI, SQLAlchemy 2.x, Alembic, APScheduler, Pydantic v2, sse-starlette, httpx, mutagen, pytest, respx, uv.

**Companion spec:** [docs/superpowers/specs/2026-04-27-frontend-music-manager-design.md](../specs/2026-04-27-frontend-music-manager-design.md)

---

## File Structure

This phase creates and modifies the following files. Each file has one clear responsibility.

```
src/toolcrate/db/
  __init__.py          - re-exports
  models.py            - SQLAlchemy 2.x ORM models (source_list, track_entry,
                         download, job, oauth_account, library_file, setting)
  session.py           - engine + sessionmaker, get_session() helpers
  alembic/
    env.py             - Alembic env (offline + online)
    script.py.mako     - boilerplate
    versions/
      0001_initial.py  - initial schema migration

src/toolcrate/core/
  __init__.py
  events.py            - EventBus (asyncio pub/sub)
  jobs.py              - JobQueue, Worker, JobType enum
  worker_handlers.py   - JobType -> service handler dispatch
  source_lists.py      - SourceListService (CRUD, path templating, URL parsing)
  sync.py              - SyncService (sldl playlist run + reconcile + status updates)
  downloads.py         - DownloadService (single-track sldl + reconcile)
  spotify.py           - SpotifyClient (public client_credentials)
  sldl_adapter.py      - subprocess wrapper, log line parser, index file parser
  reconcile.py         - match sldl index entries -> track_entry rows
  exceptions.py        - domain exceptions (NotFound, Conflict, ...)
  config.py            - settings table reader/writer with typed accessors

# NOTE: youtube.py, recognition.py, library.py are introduced in later
# phase plans (P4 for recognition, P5 for library). YouTube parsing in
# Phase 1 is just URL-id extraction, kept inline in source_lists.py.

src/toolcrate/web/
  __init__.py
  app.py               - FastAPI factory create_app()
  deps.py              - shared deps: api_token_auth, get_db_session, get_event_bus
  middleware.py        - Origin/Host guard middleware
  problem.py           - RFC 7807 helpers
  schemas/
    __init__.py
    common.py          - ProblemDetail, PaginatedResponse, Error codes
    lists.py           - SourceListIn, SourceListOut, SourceListPatch
    tracks.py          - TrackEntryOut
    jobs.py            - JobOut, JobLogPage
  routers/
    __init__.py
    health.py          - /health, /info
    lists.py           - /lists CRUD + /lists/{id}/sync
    tracks.py          - /lists/{id}/tracks + per-track actions
    jobs.py            - /jobs read, cancel, retry, log
    events.py          - /events SSE stream

src/toolcrate/cli/
  serve.py             - new: `toolcrate serve` click command
  migrate.py           - new: `toolcrate migrate` click command
  main.py              - register serve and migrate commands (modify)

tests/
  conftest.py          - shared fixtures: tmp_db, app_factory, mocked_sldl
  fixtures/
    sldl_index_sample.csv     - canned sldl --print index output
    sldl_stdout_sample.txt    - canned sldl progress lines
    spotify_playlist.json     - canned Spotify Web API response
  unit/
    core/
      test_events.py
      test_sldl_adapter.py
      test_reconcile.py
      test_source_lists.py
      test_jobs.py
      test_spotify_client.py
    web/
      test_middleware.py
      test_auth.py
  integration/
    test_lists_api.py
    test_jobs_api.py
    test_events_sse.py
    test_health.py
    test_migrate.py

pyproject.toml         - add deps, bump pydantic
alembic.ini            - alembic config (created at repo root)
```

---

## Conventions Used Throughout the Plan

- **Worktree path:** the working tree is at the repo root the agent runs from. All paths are relative to that root.
- **uv:** the project uses uv. Use `uv run pytest`, `uv add`, `uv sync`. Do NOT use pip directly.
- **Test runner:** `uv run pytest` (configured in pyproject.toml).
- **Format/lint:** `uv run ruff format <files>` then `uv run ruff check <files> --fix`. Type check with `uv run mypy <files>` after major work.
- **Commits:** conventional commits (`feat:`, `test:`, `refactor:`, `docs:`, `chore:`). Commit after each green test cycle.
- **Async style:** FastAPI handlers async. Services that do I/O are async. SQLAlchemy uses async session for DB.
- **TDD:** for every behavior-bearing module, write the failing test first.

---

## Task 0: Branch hygiene and baseline

**Files:**
- Modify: none (sanity check only)

- [ ] **Step 1: Confirm clean working tree**

```bash
git status
```
Expected: `nothing to commit, working tree clean` on the worktree branch.

- [ ] **Step 2: Confirm tests currently pass**

```bash
uv sync
uv run pytest -x -q
```
Expected: existing test suite green. If any test is already broken, stop and fix that first (the plan assumes a green baseline).

- [ ] **Step 3: Create a TODO baseline commit if needed (skip if already clean)**

No-op if tree is clean.

---

## Task 1: Add new dependencies

**Files:**
- Modify: `pyproject.toml`

**Why:** every later task imports from these. Get them installed first so subsequent tests run.

- [ ] **Step 1: Bump pydantic and add new runtime deps**

```bash
uv add 'pydantic>=2.6,<3' fastapi uvicorn 'sqlalchemy>=2.0,<3' alembic apscheduler 'sse-starlette>=2,<3' httpx mutagen aiosqlite 'greenlet>=3'
```

This updates `pyproject.toml` and `uv.lock`.

- [ ] **Step 2: Add dev deps**

```bash
uv add --dev respx 'pytest-asyncio>=0.23' freezegun
```

- [ ] **Step 3: Verify install**

```bash
uv sync
uv run python -c "import fastapi, sqlalchemy, alembic, apscheduler, pydantic; print(pydantic.VERSION, sqlalchemy.__version__)"
```
Expected: pydantic 2.x, sqlalchemy 2.x.

- [ ] **Step 4: Run existing tests to confirm pydantic v2 bump didn't break anything**

```bash
uv run pytest -x -q
```
Expected: all existing tests still pass. (Pydantic isn't imported in repo source — confirmed by grep — so no code changes needed.)

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore: add fastapi/sqlalchemy/alembic/apscheduler stack"
```

---

## Task 2: DB session module

**Files:**
- Create: `src/toolcrate/db/__init__.py`
- Create: `src/toolcrate/db/session.py`
- Create: `tests/unit/core/__init__.py`
- Create: `tests/unit/core/test_db_session.py`
- Create: `tests/__init__.py` (if missing)
- Create: `tests/unit/__init__.py` (if missing)

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/core/test_db_session.py
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/core/test_db_session.py -v
```
Expected: ImportError or AttributeError.

- [ ] **Step 3: Create `src/toolcrate/db/__init__.py`**

```python
"""Database persistence layer for toolcrate."""

from .session import create_engine_for_url, get_async_session_factory

__all__ = ["create_engine_for_url", "get_async_session_factory"]
```

- [ ] **Step 4: Create `src/toolcrate/db/session.py`**

```python
"""SQLAlchemy async engine + session factory.

Single source of truth for DB connection setup. Callers pass in a URL
(usually built from settings) and get back (engine, sessionmaker) pair.
WAL is enabled on file-backed SQLite for concurrent readers.
"""

from __future__ import annotations

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def create_engine_for_url(url: str, *, echo: bool = False) -> AsyncEngine:
    connect_args: dict[str, object] = {}
    if url.startswith("sqlite"):
        connect_args["timeout"] = 30
    engine = create_async_engine(url, echo=echo, future=True, connect_args=connect_args)

    if url.startswith("sqlite") and not url.endswith(":memory:"):
        @event.listens_for(engine.sync_engine, "connect")
        def _enable_wal(dbapi_conn, _record):  # noqa: ANN001
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.close()

    return engine


def get_async_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
```

- [ ] **Step 5: Run test to verify it passes**

```bash
uv run pytest tests/unit/core/test_db_session.py -v
```
Expected: PASS.

- [ ] **Step 6: Configure pytest-asyncio**

Add to `pyproject.toml` under `[tool.pytest.ini_options]`:

```toml
asyncio_mode = "auto"
```

Re-run all tests to confirm no regression: `uv run pytest -x -q`.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml src/toolcrate/db/ tests/unit/core/test_db_session.py tests/unit/__init__.py tests/unit/core/__init__.py tests/__init__.py
git commit -m "feat(db): async engine + session factory"
```

---

## Task 3: ORM models

**Files:**
- Create: `src/toolcrate/db/models.py`
- Modify: `src/toolcrate/db/__init__.py`
- Create: `tests/unit/core/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/core/test_models.py -v
```
Expected: ImportError on `toolcrate.db.models`.

- [ ] **Step 3: Create `src/toolcrate/db/models.py`**

```python
"""SQLAlchemy 2.x declarative models for toolcrate."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class SourceList(Base):
    __tablename__ = "source_list"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(256))
    source_type: Mapped[str] = mapped_column(String(32))  # spotify_playlist | youtube_djset | manual
    source_url: Mapped[str] = mapped_column(Text, default="")
    external_id: Mapped[str] = mapped_column(String(128), default="")
    download_path: Mapped[str] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    sync_interval: Mapped[str] = mapped_column(String(64), default="manual")
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sync_status: Mapped[str] = mapped_column(String(16), default="never")
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    oauth_account_id: Mapped[int | None] = mapped_column(ForeignKey("oauth_account.id"), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    tracks: Mapped[list["TrackEntry"]] = relationship(back_populates="source_list", cascade="all,delete-orphan")


class TrackEntry(Base):
    __tablename__ = "track_entry"
    __table_args__ = (
        Index("ix_track_entry_list_position", "source_list_id", "position"),
        UniqueConstraint("source_list_id", "isrc", name="uq_track_list_isrc"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_list_id: Mapped[int] = mapped_column(ForeignKey("source_list.id", ondelete="CASCADE"))
    position: Mapped[int] = mapped_column(Integer, default=0)
    artist: Mapped[str | None] = mapped_column(String(512), nullable=True)
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    album: Mapped[str | None] = mapped_column(String(512), nullable=True)
    duration_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    isrc: Mapped[str | None] = mapped_column(String(32), nullable=True)
    spotify_track_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    yt_timestamp_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    recognition_confidence: Mapped[float | None] = mapped_column(nullable=True)
    download_status: Mapped[str] = mapped_column(String(16), default="pending")
    download_id: Mapped[int | None] = mapped_column(ForeignKey("download.id"), nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    source_list: Mapped[SourceList] = relationship(back_populates="tracks", foreign_keys=[source_list_id])


class Download(Base):
    __tablename__ = "download"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    track_entry_id: Mapped[int] = mapped_column(ForeignKey("track_entry.id", ondelete="CASCADE"))
    job_id: Mapped[int | None] = mapped_column(ForeignKey("job.id"), nullable=True)
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(16))
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sldl_match_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Job(Base):
    __tablename__ = "job"
    __table_args__ = (
        Index("ix_job_state_sched_pri", "state", "scheduled_for", "priority"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[str] = mapped_column(String(32))
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    state: Mapped[str] = mapped_column(String(16), default="pending")
    priority: Mapped[int] = mapped_column(Integer, default=100)
    source_list_id: Mapped[int | None] = mapped_column(ForeignKey("source_list.id"), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    log_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    progress_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    pid: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class OAuthAccount(Base):
    __tablename__ = "oauth_account"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String(32))
    account_label: Mapped[str] = mapped_column(String(128))
    access_token_enc: Mapped[bytes] = mapped_column(LargeBinary)
    refresh_token_enc: Mapped[bytes] = mapped_column(LargeBinary)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    scopes: Mapped[str] = mapped_column(Text, default="")
    remote_user_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    remote_display: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class LibraryFile(Base):
    __tablename__ = "library_file"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    path: Mapped[str] = mapped_column(Text, unique=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mtime: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    artist: Mapped[str | None] = mapped_column(String(512), nullable=True)
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    album: Mapped[str | None] = mapped_column(String(512), nullable=True)
    duration_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    acoustid_fp: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_list_id: Mapped[int | None] = mapped_column(ForeignKey("source_list.id"), nullable=True)
    matched_track_id: Mapped[int | None] = mapped_column(ForeignKey("track_entry.id"), nullable=True)


class Setting(Base):
    __tablename__ = "setting"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value_json: Mapped[Any] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
```

- [ ] **Step 4: Update `src/toolcrate/db/__init__.py`**

```python
"""Database persistence layer for toolcrate."""

from .models import (
    Base,
    Download,
    Job,
    LibraryFile,
    OAuthAccount,
    Setting,
    SourceList,
    TrackEntry,
)
from .session import create_engine_for_url, get_async_session_factory

__all__ = [
    "Base",
    "Download",
    "Job",
    "LibraryFile",
    "OAuthAccount",
    "Setting",
    "SourceList",
    "TrackEntry",
    "create_engine_for_url",
    "get_async_session_factory",
]
```

- [ ] **Step 5: Run tests**

```bash
uv run pytest tests/unit/core/test_models.py -v
```
Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add src/toolcrate/db/ tests/unit/core/test_models.py
git commit -m "feat(db): add ORM models for source_list, track_entry, job, download, oauth, library, setting"
```

---

## Task 4: Alembic initial migration

**Files:**
- Create: `alembic.ini`
- Create: `src/toolcrate/db/alembic/env.py`
- Create: `src/toolcrate/db/alembic/script.py.mako`
- Create: `src/toolcrate/db/alembic/versions/0001_initial.py`
- Create: `tests/integration/__init__.py`
- Create: `tests/integration/test_alembic_migration.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/integration/test_alembic_migration.py
from pathlib import Path
import pytest
from alembic import command
from alembic.config import Config


def test_migration_to_head_creates_all_tables(tmp_path: Path):
    db_path = tmp_path / "test.db"
    cfg = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    command.upgrade(cfg, "head")

    import sqlite3
    conn = sqlite3.connect(db_path)
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    names = {r[0] for r in rows}
    for expected in {"source_list", "track_entry", "download", "job",
                     "oauth_account", "library_file", "setting"}:
        assert expected in names
    conn.close()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/integration/test_alembic_migration.py -v
```
Expected: FileNotFoundError on alembic.ini.

- [ ] **Step 3: Create `alembic.ini` at repo root**

```ini
[alembic]
script_location = src/toolcrate/db/alembic
prepend_sys_path = .

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
```

- [ ] **Step 4: Create `src/toolcrate/db/alembic/env.py`**

```python
"""Alembic environment for toolcrate (sync engine for migrations)."""

from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Make src/ importable when alembic is invoked from the repo root.
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from toolcrate.db.models import Base  # noqa: E402

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 5: Create `src/toolcrate/db/alembic/script.py.mako`**

```mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
"""
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

- [ ] **Step 6: Generate the initial revision**

Use Alembic's autogenerate to produce a revision matching the models, then move it to a stable filename `0001_initial.py`:

```bash
uv run alembic -c alembic.ini revision --autogenerate -m "initial"
```

Find the generated file in `src/toolcrate/db/alembic/versions/<hash>_initial.py`. Inspect it: confirm it creates all 7 tables. Rename to `0001_initial.py` and edit the `revision = ...` line to `revision = "0001"`. Set `down_revision = None`.

(Manual step: tweak the file to use a stable revision id and filename so the plan's tests find it deterministically.)

- [ ] **Step 7: Run the migration test**

```bash
uv run pytest tests/integration/test_alembic_migration.py -v
```
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add alembic.ini src/toolcrate/db/alembic/ tests/integration/ tests/integration/__init__.py
git commit -m "feat(db): alembic config + initial migration"
```

---

## Task 5: Settings table accessor

**Files:**
- Create: `src/toolcrate/core/__init__.py`
- Create: `src/toolcrate/core/config.py`
- Create: `tests/unit/core/test_config.py`

**Why:** all later modules read settings (api token, music root, server port, sldl defaults). Build the accessor first.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/core/test_config.py
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/core/test_config.py -v
```
Expected: ImportError.

- [ ] **Step 3: Create `src/toolcrate/core/__init__.py`**

```python
"""Core domain services for toolcrate."""
```

- [ ] **Step 4: Create `src/toolcrate/core/config.py`**

```python
"""Settings store: typed key/value persistence in the `setting` table."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from toolcrate.db.models import Setting

_MISSING = object()


class SettingsStore:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._sf = session_factory

    async def get(self, key: str, *, default: Any = _MISSING) -> Any:
        async with self._sf() as session:
            row = await session.get(Setting, key)
            if row is None:
                if default is _MISSING:
                    raise KeyError(key)
                return default
            return row.value_json

    async def set(self, key: str, value: Any) -> None:
        async with self._sf() as session:
            row = await session.get(Setting, key)
            if row is None:
                session.add(Setting(key=key, value_json=value))
            else:
                row.value_json = value
            await session.commit()

    async def seed_defaults(self, defaults: dict[str, Any]) -> None:
        """Insert any keys missing from the table; never overwrite."""
        async with self._sf() as session:
            existing = {
                k for (k,) in (await session.execute(select(Setting.key))).all()
            }
            for k, v in defaults.items():
                if k not in existing:
                    session.add(Setting(key=k, value_json=v))
            await session.commit()
```

- [ ] **Step 5: Run tests**

```bash
uv run pytest tests/unit/core/test_config.py -v
```
Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add src/toolcrate/core/__init__.py src/toolcrate/core/config.py tests/unit/core/test_config.py
git commit -m "feat(core): SettingsStore typed kv accessor"
```

---

## Task 6: EventBus

**Files:**
- Create: `src/toolcrate/core/events.py`
- Create: `tests/unit/core/test_events.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/core/test_events.py
import asyncio
import pytest
from toolcrate.core.events import EventBus, Event


async def test_subscriber_receives_published_event():
    bus = EventBus()
    sub = bus.subscribe()
    await bus.publish(Event(name="job.update", data={"id": 1, "state": "running"}))
    received = await asyncio.wait_for(anext(sub), timeout=1)
    assert received.name == "job.update"
    assert received.data["state"] == "running"
    await bus.unsubscribe(sub)


async def test_two_subscribers_each_receive_event():
    bus = EventBus()
    a = bus.subscribe()
    b = bus.subscribe()
    await bus.publish(Event(name="x", data={}))
    ra = await asyncio.wait_for(anext(a), timeout=1)
    rb = await asyncio.wait_for(anext(b), timeout=1)
    assert ra.name == rb.name == "x"


async def test_unsubscribe_stops_delivery():
    bus = EventBus()
    sub = bus.subscribe()
    await bus.unsubscribe(sub)
    # should be a no-op; publishing now must not raise
    await bus.publish(Event(name="x", data={}))


async def test_topic_filtering():
    bus = EventBus()
    sub = bus.subscribe(topics={"jobs"})
    await bus.publish(Event(name="lists.updated", data={}, topic="lists"))
    await bus.publish(Event(name="job.update", data={}, topic="jobs"))
    ev = await asyncio.wait_for(anext(sub), timeout=1)
    assert ev.topic == "jobs"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/core/test_events.py -v
```
Expected: ImportError.

- [ ] **Step 3: Create `src/toolcrate/core/events.py`**

```python
"""In-process pub/sub event bus.

Each subscriber gets an asyncio.Queue. Publishers fan out to all matching
queues. Used to bridge worker/service progress -> SSE handlers.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import AsyncIterator, Iterable


@dataclass(slots=True)
class Event:
    name: str
    data: dict
    topic: str = "default"


class _Subscription:
    def __init__(self, topics: set[str] | None) -> None:
        self.topics = topics
        self.queue: asyncio.Queue[Event] = asyncio.Queue(maxsize=1000)

    def __aiter__(self) -> AsyncIterator[Event]:
        return self

    async def __anext__(self) -> Event:
        return await self.queue.get()


class EventBus:
    def __init__(self) -> None:
        self._subs: list[_Subscription] = []
        self._lock = asyncio.Lock()

    def subscribe(self, *, topics: Iterable[str] | None = None) -> _Subscription:
        sub = _Subscription(set(topics) if topics else None)
        self._subs.append(sub)
        return sub

    async def unsubscribe(self, sub: _Subscription) -> None:
        async with self._lock:
            if sub in self._subs:
                self._subs.remove(sub)

    async def publish(self, event: Event) -> None:
        async with self._lock:
            targets = [s for s in self._subs if s.topics is None or event.topic in s.topics]
        for s in targets:
            try:
                s.queue.put_nowait(event)
            except asyncio.QueueFull:
                # slow consumer; drop oldest then enqueue
                _ = s.queue.get_nowait()
                s.queue.put_nowait(event)
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/unit/core/test_events.py -v
```
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add src/toolcrate/core/events.py tests/unit/core/test_events.py
git commit -m "feat(core): asyncio EventBus for SSE fan-out"
```

---

## Task 7: SldlAdapter — log + index parser

**Files:**
- Create: `src/toolcrate/core/sldl_adapter.py`
- Create: `tests/fixtures/sldl_index_sample.csv`
- Create: `tests/fixtures/sldl_stdout_sample.txt`
- Create: `tests/unit/core/test_sldl_adapter.py`

**Why:** the parsers are pure functions. Build them before wiring subprocess. Keeps tests fast.

- [ ] **Step 1: Inspect a real sldl index file**

Run sldl on a tiny throwaway list to see the index format. If sldl isn't installed:

```bash
uv run toolcrate tools status
```

If installed, generate a sample (no need for real downloads):

```bash
echo "Daft Punk - Around the World" > /tmp/q.txt
"$(uv run toolcrate tools status | grep sldl | awk '{print $NF}')" --input-type list --print json /tmp/q.txt > tests/fixtures/sldl_print_json_sample.json 2>&1 || true
```

If sldl isn't available, hand-write `tests/fixtures/sldl_index_sample.csv` based on this real format observed in slsk-batchdl/README.md (the index is CSV `filepath,artist,title,length,tracktype,state,failurereason`):

```csv
/tmp/music/Daft Punk/Discovery/01 - One More Time.mp3,Daft Punk,One More Time,320,1,1,
,Daft Punk,Around the World,440,1,2,NoSuitableFileFound
/tmp/music/Daft Punk/Discovery/03 - Digital Love.mp3,Daft Punk,Digital Love,301,1,1,
```

State values per slsk-batchdl source: 0=NotProcessed, 1=Downloaded, 2=Failed, 3=AlreadyExists, 4=NotFoundLastTime.

- [ ] **Step 2: Hand-write `tests/fixtures/sldl_stdout_sample.txt`**

```
Login...
Logged in
Searching: Daft Punk - One More Time
Downloading: Daft Punk - One More Time -- daft.punk@user (5 MB)
Succeeded: Daft Punk - One More Time
Searching: Daft Punk - Around the World
Failed: Daft Punk - Around the World -- NoSuitableFileFound
Searching: Daft Punk - Digital Love
Downloading: Daft Punk - Digital Love -- foo@user (4 MB)
Succeeded: Daft Punk - Digital Love
Done. 2 succeeded, 1 failed.
```

- [ ] **Step 3: Write the failing test**

```python
# tests/unit/core/test_sldl_adapter.py
from pathlib import Path
import pytest
from toolcrate.core.sldl_adapter import (
    parse_index_csv,
    parse_progress_line,
    SldlIndexEntry,
    SldlProgressEvent,
)

FIX = Path(__file__).resolve().parents[2] / "fixtures"


def test_parse_index_csv_returns_one_row_per_track():
    rows = parse_index_csv((FIX / "sldl_index_sample.csv").read_text())
    assert len(rows) == 3
    assert rows[0].state == "downloaded"
    assert rows[0].artist == "Daft Punk"
    assert rows[0].title == "One More Time"
    assert rows[0].file_path == "/tmp/music/Daft Punk/Discovery/01 - One More Time.mp3"
    assert rows[1].state == "failed"
    assert rows[1].failure_reason == "NoSuitableFileFound"


def test_parse_progress_line_searching():
    ev = parse_progress_line("Searching: Daft Punk - One More Time")
    assert ev is not None
    assert ev.kind == "searching"
    assert "One More Time" in ev.track_label


def test_parse_progress_line_downloading():
    ev = parse_progress_line("Downloading: Daft Punk - One More Time -- daft.punk@user (5 MB)")
    assert ev is not None
    assert ev.kind == "downloading"


def test_parse_progress_line_succeeded():
    ev = parse_progress_line("Succeeded: Daft Punk - One More Time")
    assert ev.kind == "succeeded"


def test_parse_progress_line_failed():
    ev = parse_progress_line("Failed: Daft Punk - Around the World -- NoSuitableFileFound")
    assert ev.kind == "failed"
    assert ev.detail == "NoSuitableFileFound"


def test_parse_progress_line_unknown_returns_none():
    assert parse_progress_line("Login...") is None


def test_parse_progress_line_summary_recognized():
    ev = parse_progress_line("Done. 2 succeeded, 1 failed.")
    assert ev.kind == "summary"
    assert ev.detail.startswith("2 succeeded")
```

- [ ] **Step 4: Run tests to verify they fail**

```bash
uv run pytest tests/unit/core/test_sldl_adapter.py -v
```
Expected: ImportError.

- [ ] **Step 5: Create `src/toolcrate/core/sldl_adapter.py`**

```python
"""Wrapper for the sldl (slsk-batchdl) subprocess.

Three responsibilities:
  1. Build sldl args from a SourceList + settings (`build_command`).
  2. Run sldl as a subprocess and stream its progress lines.
  3. Parse sldl's CSV index file into structured rows.

The line/index parsers are pure functions and tested independently of any
real sldl binary. The runner is integration-tested with a mock binary.
"""

from __future__ import annotations

import asyncio
import csv
import io
import os
import re
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncIterator


_STATE_MAP = {
    "0": "not_processed",
    "1": "downloaded",
    "2": "failed",
    "3": "already_exists",
    "4": "not_found_last_time",
}


@dataclass(slots=True)
class SldlIndexEntry:
    file_path: str
    artist: str
    title: str
    length_sec: int | None
    state: str
    failure_reason: str


@dataclass(slots=True)
class SldlProgressEvent:
    kind: str  # 'searching' | 'downloading' | 'succeeded' | 'failed' | 'summary'
    track_label: str
    detail: str = ""


def parse_index_csv(text: str) -> list[SldlIndexEntry]:
    rows: list[SldlIndexEntry] = []
    reader = csv.reader(io.StringIO(text))
    for row in reader:
        if not row or len(row) < 6:
            continue
        file_path = row[0].strip()
        artist = row[1].strip()
        title = row[2].strip()
        length_raw = row[3].strip()
        try:
            length = int(length_raw) if length_raw else None
        except ValueError:
            length = None
        state_raw = row[5].strip()
        state = _STATE_MAP.get(state_raw, "unknown")
        failure_reason = row[6].strip() if len(row) >= 7 else ""
        rows.append(SldlIndexEntry(file_path, artist, title, length, state, failure_reason))
    return rows


_SEARCHING = re.compile(r"^Searching:\s*(.+)$")
_DOWNLOADING = re.compile(r"^Downloading:\s*(.+?)(?:\s+--\s+(.+))?$")
_SUCCEEDED = re.compile(r"^Succeeded:\s*(.+)$")
_FAILED = re.compile(r"^Failed:\s*(.+?)(?:\s+--\s+(.+))?$")
_SUMMARY = re.compile(r"^Done\.\s*(.+)$")


def parse_progress_line(line: str) -> SldlProgressEvent | None:
    line = line.rstrip("\r\n")
    if m := _SEARCHING.match(line):
        return SldlProgressEvent(kind="searching", track_label=m.group(1).strip())
    if m := _DOWNLOADING.match(line):
        return SldlProgressEvent(kind="downloading", track_label=m.group(1).strip(),
                                 detail=(m.group(2) or "").strip())
    if m := _SUCCEEDED.match(line):
        return SldlProgressEvent(kind="succeeded", track_label=m.group(1).strip())
    if m := _FAILED.match(line):
        return SldlProgressEvent(kind="failed", track_label=m.group(1).strip(),
                                 detail=(m.group(2) or "").strip())
    if m := _SUMMARY.match(line):
        return SldlProgressEvent(kind="summary", track_label="", detail=m.group(1).strip())
    return None


def build_command(
    *,
    sldl_path: str,
    input_arg: str,
    download_path: str,
    index_path: str,
    extra_args: list[str] | None = None,
) -> list[str]:
    """Build the sldl argv list. Always uses argv list (no shell)."""
    cmd = [
        sldl_path,
        input_arg,
        "--path",
        download_path,
        "--index-path",
        index_path,
        "--no-progress",
    ]
    if extra_args:
        cmd.extend(extra_args)
    return cmd


async def stream_sldl(
    cmd: list[str],
    *,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
) -> AsyncIterator[tuple[asyncio.subprocess.Process, str]]:
    """Spawn sldl and yield (process, line) for each stdout line.

    The first yielded pair has the spawned process so callers can record pid
    and use it for cancellation. Subsequent yields are pure (process, line).
    """
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        cwd=cwd,
        env={**os.environ, **(env or {})},
    )
    assert proc.stdout is not None
    yield proc, ""  # caller can record pid before lines arrive
    while True:
        chunk = await proc.stdout.readline()
        if not chunk:
            break
        yield proc, chunk.decode("utf-8", errors="replace").rstrip("\n")
    await proc.wait()
```

- [ ] **Step 6: Run tests**

```bash
uv run pytest tests/unit/core/test_sldl_adapter.py -v
```
Expected: 7 passed.

- [ ] **Step 7: Commit**

```bash
git add src/toolcrate/core/sldl_adapter.py tests/fixtures/sldl_index_sample.csv tests/fixtures/sldl_stdout_sample.txt tests/unit/core/test_sldl_adapter.py
git commit -m "feat(core): SldlAdapter parsers (index csv + progress lines)"
```

---

## Task 8: Reconcile module

**Files:**
- Create: `src/toolcrate/core/reconcile.py`
- Create: `tests/unit/core/test_reconcile.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/core/test_reconcile.py
import pytest
from toolcrate.core.reconcile import match_index_to_tracks, MatchResult
from toolcrate.core.sldl_adapter import SldlIndexEntry
from toolcrate.db.models import TrackEntry


def _t(id, artist, title, isrc=None):
    return TrackEntry(id=id, source_list_id=1, position=id, artist=artist, title=title, isrc=isrc)


def test_isrc_match_preferred():
    tracks = [_t(1, "X", "Y", isrc="USRC12345")]
    idx = [SldlIndexEntry(file_path="/m/x.mp3", artist="X", title="Y", length_sec=200,
                          state="downloaded", failure_reason="")]
    # ISRC isn't in sldl index by default — fall through to artist+title
    out = match_index_to_tracks(idx, tracks)
    assert out[0].track_id == 1
    assert out[0].state == "downloaded"


def test_artist_title_fuzzy_match():
    tracks = [_t(1, "Daft Punk", "One More Time")]
    idx = [SldlIndexEntry(file_path="/m/o.mp3", artist="daft punk", title="one more time",
                          length_sec=320, state="downloaded", failure_reason="")]
    out = match_index_to_tracks(idx, tracks)
    assert out[0].track_id == 1


def test_failed_entry_records_failure():
    tracks = [_t(1, "A", "B")]
    idx = [SldlIndexEntry(file_path="", artist="A", title="B", length_sec=None,
                          state="failed", failure_reason="NoSuitableFileFound")]
    out = match_index_to_tracks(idx, tracks)
    assert out[0].track_id == 1
    assert out[0].state == "failed"
    assert out[0].failure_reason == "NoSuitableFileFound"


def test_unmatched_index_entry_returned_with_none_track():
    tracks = []
    idx = [SldlIndexEntry(file_path="", artist="Z", title="Q", length_sec=None,
                          state="downloaded", failure_reason="")]
    out = match_index_to_tracks(idx, tracks)
    assert out[0].track_id is None


def test_track_with_no_index_entry_omitted():
    tracks = [_t(1, "A", "B"), _t(2, "C", "D")]
    idx = [SldlIndexEntry(file_path="/m/a.mp3", artist="A", title="B", length_sec=200,
                          state="downloaded", failure_reason="")]
    out = match_index_to_tracks(idx, tracks)
    matched_ids = {r.track_id for r in out}
    assert matched_ids == {1}
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/core/test_reconcile.py -v
```
Expected: ImportError.

- [ ] **Step 3: Create `src/toolcrate/core/reconcile.py`**

```python
"""Match sldl index entries back to track_entry rows.

Strategy: prefer exact ISRC where present, then case-insensitive trimmed
artist+title equality, then a normalized form (strip non-alphanum) for
fuzziness. Anything we cannot match is returned with track_id=None so the
caller can log it without crashing the sync.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable

from toolcrate.core.sldl_adapter import SldlIndexEntry
from toolcrate.db.models import TrackEntry


@dataclass(slots=True)
class MatchResult:
    track_id: int | None
    state: str  # 'downloaded' | 'failed' | 'already_exists' | 'not_found_last_time' | 'unknown'
    file_path: str
    failure_reason: str


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).lower()
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    return s


def match_index_to_tracks(
    index: Iterable[SldlIndexEntry], tracks: Iterable[TrackEntry]
) -> list[MatchResult]:
    track_list = list(tracks)
    by_norm: dict[str, TrackEntry] = {}
    for t in track_list:
        if t.artist and t.title:
            by_norm[_norm(f"{t.artist} {t.title}")] = t

    results: list[MatchResult] = []
    for entry in index:
        norm = _norm(f"{entry.artist} {entry.title}")
        match = by_norm.get(norm)
        results.append(MatchResult(
            track_id=match.id if match else None,
            state=entry.state,
            file_path=entry.file_path,
            failure_reason=entry.failure_reason,
        ))
    return results
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/unit/core/test_reconcile.py -v
```
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add src/toolcrate/core/reconcile.py tests/unit/core/test_reconcile.py
git commit -m "feat(core): reconcile sldl index back to track_entry rows"
```

---

## Task 9: Domain exceptions

**Files:**
- Create: `src/toolcrate/core/exceptions.py`

- [ ] **Step 1: Create the file**

```python
"""Domain exceptions used across services and converted to RFC 7807 in web layer."""

from __future__ import annotations


class ToolcrateError(Exception):
    code: str = "toolcrate.error"


class NotFound(ToolcrateError):
    code = "not_found"


class Conflict(ToolcrateError):
    code = "conflict"


class ValidationError(ToolcrateError):
    code = "validation_error"


class IntegrationError(ToolcrateError):
    code = "integration_error"
```

- [ ] **Step 2: Commit**

```bash
git add src/toolcrate/core/exceptions.py
git commit -m "feat(core): domain exceptions"
```

---

## Task 10: SpotifyClient (public client_credentials)

**Files:**
- Create: `src/toolcrate/core/spotify.py`
- Create: `tests/fixtures/spotify_playlist.json`
- Create: `tests/unit/core/test_spotify_client.py`

**Why:** Phase 1 only needs anonymous public-API access (paste-URL flow). OAuth-bound private playlist fetching arrives in Phase 3.

- [ ] **Step 1: Create `tests/fixtures/spotify_playlist.json`**

A trimmed real-shape Spotify Web API response for a playlist + tracks:

```json
{
  "id": "abc123",
  "name": "Late Night",
  "owner": {"display_name": "tester"},
  "images": [{"url": "https://i.example/cover.jpg", "height": 640, "width": 640}],
  "tracks": {
    "total": 2,
    "items": [
      {
        "track": {
          "id": "T1",
          "name": "One More Time",
          "duration_ms": 320000,
          "external_ids": {"isrc": "FR0010100001"},
          "artists": [{"name": "Daft Punk"}],
          "album": {"name": "Discovery"}
        }
      },
      {
        "track": {
          "id": "T2",
          "name": "Around the World",
          "duration_ms": 440000,
          "external_ids": {"isrc": "FR0010100002"},
          "artists": [{"name": "Daft Punk"}],
          "album": {"name": "Discovery"}
        }
      }
    ],
    "next": null
  }
}
```

- [ ] **Step 2: Write the failing test**

```python
# tests/unit/core/test_spotify_client.py
import json
from pathlib import Path

import httpx
import pytest
import respx

from toolcrate.core.spotify import SpotifyClient, parse_playlist_url

FIX = Path(__file__).resolve().parents[2] / "fixtures"


def test_parse_playlist_url_classic():
    assert parse_playlist_url("https://open.spotify.com/playlist/abc123") == "abc123"


def test_parse_playlist_url_with_query():
    assert parse_playlist_url("https://open.spotify.com/playlist/abc123?si=foo") == "abc123"


def test_parse_playlist_url_invalid():
    assert parse_playlist_url("https://example.com/foo") is None


@respx.mock
async def test_fetch_playlist_returns_normalized_tracks():
    respx.post("https://accounts.spotify.com/api/token").mock(
        return_value=httpx.Response(200, json={"access_token": "tk", "expires_in": 3600})
    )
    payload = json.loads((FIX / "spotify_playlist.json").read_text())
    respx.get("https://api.spotify.com/v1/playlists/abc123").mock(
        return_value=httpx.Response(200, json=payload)
    )

    client = SpotifyClient(client_id="cid", client_secret="csec")
    result = await client.fetch_playlist("abc123")
    await client.aclose()

    assert result.id == "abc123"
    assert result.name == "Late Night"
    assert len(result.tracks) == 2
    assert result.tracks[0].artist == "Daft Punk"
    assert result.tracks[0].isrc == "FR0010100001"
    assert result.tracks[0].duration_sec == 320
```

- [ ] **Step 3: Run test to verify it fails**

```bash
uv run pytest tests/unit/core/test_spotify_client.py -v
```
Expected: ImportError.

- [ ] **Step 4: Create `src/toolcrate/core/spotify.py`**

```python
"""Spotify Web API client (public client_credentials).

Only what Phase 1 needs: parse a playlist URL to id, fetch playlist and
tracks anonymously. OAuth-bound user-context calls land in Phase 3 — same
class will gain a `with_token(...)` constructor then.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

import httpx

from .exceptions import IntegrationError, ValidationError


_PLAYLIST_RE = re.compile(r"open\.spotify\.com/playlist/([A-Za-z0-9]+)")


def parse_playlist_url(url: str) -> str | None:
    m = _PLAYLIST_RE.search(url)
    return m.group(1) if m else None


@dataclass(slots=True)
class SpotifyTrack:
    spotify_track_id: str
    artist: str
    title: str
    album: str
    isrc: str | None
    duration_sec: int


@dataclass(slots=True)
class SpotifyPlaylist:
    id: str
    name: str
    owner: str
    image_url: str | None
    tracks: list[SpotifyTrack]


class SpotifyClient:
    AUTH_URL = "https://accounts.spotify.com/api/token"
    API_BASE = "https://api.spotify.com/v1"

    def __init__(self, *, client_id: str, client_secret: str,
                 http: httpx.AsyncClient | None = None) -> None:
        if not client_id or not client_secret:
            raise ValidationError("client_id/client_secret required")
        self._cid = client_id
        self._csec = client_secret
        self._http = http or httpx.AsyncClient(timeout=30)
        self._token: str | None = None

    async def aclose(self) -> None:
        await self._http.aclose()

    async def _ensure_token(self) -> str:
        if self._token:
            return self._token
        resp = await self._http.post(
            self.AUTH_URL,
            data={"grant_type": "client_credentials"},
            auth=(self._cid, self._csec),
        )
        if resp.status_code != 200:
            raise IntegrationError(f"spotify auth failed: {resp.status_code} {resp.text}")
        self._token = resp.json()["access_token"]
        return self._token

    async def fetch_playlist(self, playlist_id: str) -> SpotifyPlaylist:
        token = await self._ensure_token()
        resp = await self._http.get(
            f"{self.API_BASE}/playlists/{playlist_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        if resp.status_code != 200:
            raise IntegrationError(f"spotify fetch_playlist {playlist_id}: {resp.status_code}")
        payload = resp.json()
        items = payload.get("tracks", {}).get("items", [])
        tracks = [_normalize(it["track"]) for it in items if it.get("track")]
        # NOTE: pagination via tracks.next is handled in Phase 3 once OAuth lands;
        # public Phase-1 path tolerates first-page-only for typical playlists.
        return SpotifyPlaylist(
            id=payload["id"],
            name=payload["name"],
            owner=(payload.get("owner") or {}).get("display_name", ""),
            image_url=(payload.get("images") or [{}])[0].get("url"),
            tracks=tracks,
        )


def _normalize(track: dict) -> SpotifyTrack:
    artists: Iterable[dict] = track.get("artists") or []
    artist_names = ", ".join(a.get("name", "") for a in artists if a.get("name"))
    return SpotifyTrack(
        spotify_track_id=track.get("id", ""),
        artist=artist_names,
        title=track.get("name", ""),
        album=(track.get("album") or {}).get("name", ""),
        isrc=(track.get("external_ids") or {}).get("isrc"),
        duration_sec=int((track.get("duration_ms") or 0) / 1000),
    )
```

- [ ] **Step 5: Run tests**

```bash
uv run pytest tests/unit/core/test_spotify_client.py -v
```
Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add src/toolcrate/core/spotify.py tests/fixtures/spotify_playlist.json tests/unit/core/test_spotify_client.py
git commit -m "feat(core): SpotifyClient (public client_credentials, paste-URL flow)"
```

---

## Task 11: SourceListService

**Files:**
- Create: `src/toolcrate/core/source_lists.py`
- Create: `tests/unit/core/test_source_lists.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/core/test_source_lists.py -v
```
Expected: ImportError.

- [ ] **Step 3: Create `src/toolcrate/core/source_lists.py`**

```python
"""SourceListService: CRUD over the source_list table with URL detection.

URL detection rules (Phase 1):
  - URL matches open.spotify.com/playlist/<id>  -> source_type=spotify_playlist
  - URL matches youtube.com/watch?v=<id> or youtu.be/<id>  -> source_type=youtube_djset
  - source_type='manual' is allowed without a URL
  - Anything else -> ValidationError

The service does NOT contact Spotify/YouTube here; it only parses and
persists. SyncService and RecognitionService do the network work.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any
from urllib.parse import parse_qs, urlparse

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .exceptions import NotFound, ValidationError
from .spotify import parse_playlist_url
from toolcrate.db.models import SourceList


_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(name: str) -> str:
    n = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    return _SLUG_RE.sub("-", n).strip("-")


_SOURCE_DIR = {
    "spotify_playlist": "spotify",
    "youtube_djset": "dj-sets",
    "manual": "manual",
}


def default_download_path(music_root: str, source_type: str, name: str) -> str:
    return f"{music_root.rstrip('/')}/{_SOURCE_DIR[source_type]}/{slugify(name)}"


def _detect_source_type(url: str) -> tuple[str, str]:
    """Return (source_type, external_id) or raise ValidationError."""
    if pid := parse_playlist_url(url):
        return "spotify_playlist", pid
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host in {"www.youtube.com", "youtube.com", "m.youtube.com"}:
        vid = parse_qs(parsed.query).get("v", [None])[0]
        if vid:
            return "youtube_djset", vid
    if host == "youtu.be":
        vid = parsed.path.lstrip("/")
        if vid:
            return "youtube_djset", vid
    raise ValidationError(f"unrecognized source URL: {url!r}")


class SourceListService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        music_root: str,
    ) -> None:
        self._sf = session_factory
        self._music_root = music_root

    async def create(
        self,
        *,
        name: str,
        source_url: str = "",
        source_type: str | None = None,
        download_path: str | None = None,
        sync_interval: str = "manual",
        oauth_account_id: int | None = None,
    ) -> SourceList:
        if source_type is None:
            if not source_url:
                raise ValidationError("source_type or source_url required")
            source_type, external_id = _detect_source_type(source_url)
        else:
            if source_type not in _SOURCE_DIR:
                raise ValidationError(f"unknown source_type: {source_type!r}")
            external_id = ""
            if source_url:
                _, external_id = _detect_source_type(source_url)
        path = download_path or default_download_path(self._music_root, source_type, name)
        async with self._sf() as session:
            row = SourceList(
                name=name,
                source_type=source_type,
                source_url=source_url,
                external_id=external_id,
                download_path=path,
                sync_interval=sync_interval,
                oauth_account_id=oauth_account_id,
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return row

    async def get(self, list_id: int) -> SourceList:
        async with self._sf() as session:
            row = await session.get(SourceList, list_id)
            if row is None:
                raise NotFound(f"source_list {list_id}")
            return row

    async def list(
        self, *, source_type: str | None = None, enabled: bool | None = None,
    ) -> list[SourceList]:
        async with self._sf() as session:
            stmt = select(SourceList)
            if source_type is not None:
                stmt = stmt.where(SourceList.source_type == source_type)
            if enabled is not None:
                stmt = stmt.where(SourceList.enabled == enabled)
            return list((await session.execute(stmt)).scalars())

    async def update(self, list_id: int, fields: dict[str, Any]) -> SourceList:
        allowed = {"name", "download_path", "sync_interval", "enabled",
                   "oauth_account_id", "metadata_json", "last_sync_status",
                   "last_synced_at", "last_error"}
        invalid = set(fields) - allowed
        if invalid:
            raise ValidationError(f"unknown fields: {sorted(invalid)}")
        async with self._sf() as session:
            row = await session.get(SourceList, list_id)
            if row is None:
                raise NotFound(f"source_list {list_id}")
            for k, v in fields.items():
                setattr(row, k, v)
            await session.commit()
            await session.refresh(row)
            return row

    async def delete(self, list_id: int) -> None:
        async with self._sf() as session:
            row = await session.get(SourceList, list_id)
            if row is None:
                raise NotFound(f"source_list {list_id}")
            await session.delete(row)
            await session.commit()
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/unit/core/test_source_lists.py -v
```
Expected: 11 passed.

- [ ] **Step 5: Commit**

```bash
git add src/toolcrate/core/source_lists.py tests/unit/core/test_source_lists.py
git commit -m "feat(core): SourceListService CRUD + URL detection + path templating"
```

---

## Task 12: JobQueue and Worker

**Files:**
- Create: `src/toolcrate/core/jobs.py`
- Create: `tests/unit/core/test_jobs.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/core/test_jobs.py
import asyncio
import pytest

from toolcrate.core.events import EventBus
from toolcrate.core.jobs import JobQueue, Worker, JobType
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

    async def handler(job: Job, *, ctx) -> None:
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

    async def handler(job: Job, *, ctx) -> None:
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/core/test_jobs.py -v
```
Expected: ImportError.

- [ ] **Step 3: Create `src/toolcrate/core/jobs.py`**

```python
"""DB-backed job queue and async worker.

Single worker drains the table serially. Job handlers are registered by
JobType. Failed jobs retry with exponential backoff up to max_attempts.
The worker is started/stopped by the FastAPI lifespan; tests exercise it
directly.
"""

from __future__ import annotations

import asyncio
import enum
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Awaitable, Callable, Mapping

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .events import Event, EventBus
from toolcrate.db.models import Job


logger = logging.getLogger(__name__)


class JobType(str, enum.Enum):
    SYNC_LIST = "sync_list"
    RECOGNIZE_DJSET = "recognize_djset"
    DOWNLOAD_TRACK = "download_track"
    LIBRARY_SCAN = "library_scan"


HandlerCtx = dict[str, Any]
Handler = Callable[[Job], Awaitable[None]]


class JobQueue:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._sf = session_factory

    async def enqueue(
        self,
        type: JobType,
        *,
        payload: dict[str, Any],
        priority: int = 100,
        max_attempts: int = 3,
        source_list_id: int | None = None,
        scheduled_for: datetime | None = None,
    ) -> Job:
        async with self._sf() as session:
            j = Job(
                type=type.value,
                payload_json=payload,
                priority=priority,
                max_attempts=max_attempts,
                source_list_id=source_list_id,
                scheduled_for=scheduled_for or datetime.now(timezone.utc),
            )
            session.add(j)
            await session.commit()
            await session.refresh(j)
            return j

    async def cancel(self, job_id: int) -> None:
        async with self._sf() as session:
            await session.execute(
                update(Job).where(Job.id == job_id).values(state="cancelled",
                                                          finished_at=datetime.now(timezone.utc))
            )
            await session.commit()

    async def claim_next(self, *, now: datetime | None = None) -> Job | None:
        now = now or datetime.now(timezone.utc)
        async with self._sf() as session:
            stmt = (
                select(Job)
                .where(Job.state == "pending", Job.scheduled_for <= now)
                .order_by(Job.priority.asc(), Job.scheduled_for.asc())
                .limit(1)
                .with_for_update(skip_locked=True)
            )
            row = (await session.execute(stmt)).scalar_one_or_none()
            if row is None:
                return None
            row.state = "running"
            row.started_at = now
            row.attempts = (row.attempts or 0) + 1
            await session.commit()
            await session.refresh(row)
            return row


class Worker:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        queue: JobQueue,
        bus: EventBus,
        *,
        handlers: Mapping[JobType, Callable[..., Awaitable[None]]],
        poll_interval: float = 1.0,
        backoff_base_seconds: float = 60.0,
    ) -> None:
        self._sf = session_factory
        self._queue = queue
        self._bus = bus
        self._handlers = handlers
        self._poll = poll_interval
        self._backoff = backoff_base_seconds
        self._stop = asyncio.Event()

    def stop(self) -> None:
        self._stop.set()

    async def run(self) -> None:
        while not self._stop.is_set():
            job = await self._queue.claim_next()
            if job is None:
                try:
                    await asyncio.wait_for(self._stop.wait(), timeout=self._poll)
                except asyncio.TimeoutError:
                    pass
                continue
            await self._dispatch(job)

    async def _dispatch(self, job: Job) -> None:
        handler = self._handlers.get(JobType(job.type))
        if handler is None:
            await self._mark_failed(job, f"no handler for {job.type}")
            return
        await self._bus.publish(Event(name="job.update", topic="jobs",
                                      data={"id": job.id, "state": "running"}))
        try:
            await handler(job)
        except Exception as exc:  # noqa: BLE001
            logger.exception("job %s failed: %s", job.id, exc)
            await self._on_failure(job, exc)
            return
        async with self._sf() as session:
            row = await session.get(Job, job.id)
            row.state = "success"
            row.finished_at = datetime.now(timezone.utc)
            await session.commit()
        await self._bus.publish(Event(name="job.update", topic="jobs",
                                      data={"id": job.id, "state": "success"}))

    async def _on_failure(self, job: Job, exc: Exception) -> None:
        async with self._sf() as session:
            row = await session.get(Job, job.id)
            if row.attempts < row.max_attempts:
                row.state = "pending"
                delay = self._backoff * (2 ** (row.attempts - 1))
                row.scheduled_for = datetime.now(timezone.utc) + timedelta(seconds=delay)
                row.error = str(exc)
            else:
                row.state = "failed"
                row.finished_at = datetime.now(timezone.utc)
                row.error = str(exc)
            await session.commit()
        await self._bus.publish(Event(name="job.update", topic="jobs",
                                      data={"id": job.id, "state": row.state}))

    async def _mark_failed(self, job: Job, error: str) -> None:
        async with self._sf() as session:
            row = await session.get(Job, job.id)
            row.state = "failed"
            row.finished_at = datetime.now(timezone.utc)
            row.error = error
            await session.commit()
        await self._bus.publish(Event(name="job.update", topic="jobs",
                                      data={"id": job.id, "state": "failed"}))
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/unit/core/test_jobs.py -v
```
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add src/toolcrate/core/jobs.py tests/unit/core/test_jobs.py
git commit -m "feat(core): DB-backed JobQueue + async Worker with retry/backoff"
```

---

## Task 13: SyncService (orchestrate sldl + reconcile)

**Files:**
- Create: `src/toolcrate/core/sync.py`
- Create: `tests/unit/core/test_sync.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/core/test_sync.py
import os
from pathlib import Path
import textwrap

import pytest

from toolcrate.core.events import EventBus
from toolcrate.core.sync import SyncService
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

    The stub looks for `--index-path <p>` in argv and writes there.
    """
    script = tmp_path / "fake-sldl"
    script.write_text(textwrap.dedent("""\
        #!/usr/bin/env bash
        set -eu
        idx=""
        next_is_idx=0
        for arg in "$@"; do
          if [ "$next_is_idx" = "1" ]; then idx="$arg"; next_is_idx=0; continue; fi
          if [ "$arg" = "--index-path" ]; then next_is_idx=1; fi
        done
        echo "Searching: Daft Punk - One More Time"
        echo "Downloading: Daft Punk - One More Time -- u@h (5 MB)"
        echo "Succeeded: Daft Punk - One More Time"
        echo "Searching: Daft Punk - Around the World"
        echo "Failed: Daft Punk - Around the World -- NoSuitableFileFound"
        echo "Done. 1 succeeded, 1 failed."
        if [ -n "$idx" ]; then
          mkdir -p "$(dirname "$idx")"
          cat > "$idx" <<EOF
/m/x/01.mp3,Daft Punk,One More Time,320,1,1,
,Daft Punk,Around the World,440,1,2,NoSuitableFileFound
EOF
        fi
    """))
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/core/test_sync.py -v
```
Expected: ImportError.

- [ ] **Step 3: Create `src/toolcrate/core/sync.py`**

```python
"""SyncService: orchestrate one sync run for a source_list.

Steps for a Spotify or YouTube playlist source:
  1. (Caller has already populated track_entry rows from metadata.)
  2. Build an sldl command pointed at list.source_url and download_path.
  3. Stream stdout, append to log, fan out progress events.
  4. After exit, parse the index file and reconcile to track_entry rows.
  5. Update list.last_synced_at / last_sync_status.
"""

from __future__ import annotations

import logging
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from .events import Event, EventBus
from .reconcile import match_index_to_tracks
from .sldl_adapter import build_command, parse_index_csv, parse_progress_line, stream_sldl
from .source_lists import SourceListService
from toolcrate.db.models import Download, Job, TrackEntry


logger = logging.getLogger(__name__)


_INDEX_TO_TRACK_STATUS = {
    "downloaded": "done",
    "already_exists": "done",
    "failed": "failed",
    "not_found_last_time": "failed",
    "not_processed": "pending",
    "unknown": "pending",
}


class SyncService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        bus: EventBus,
        sldl_path: str,
        sldl_extra_args: Iterable[str],
        src_service: SourceListService,
    ) -> None:
        self._sf = session_factory
        self._bus = bus
        self._sldl = sldl_path
        self._extra = list(sldl_extra_args)
        self._src = src_service

    async def run_for_list(
        self, list_id: int, *, job_id: int | None = None, log_path: str | None = None
    ) -> None:
        sl = await self._src.get(list_id)
        if not sl.source_url and sl.source_type != "manual":
            raise ValueError(f"list {list_id} has no source_url")

        log_file = Path(log_path) if log_path else Path(tempfile.mktemp(prefix="sldl-", suffix=".log"))
        log_file.parent.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = str(Path(tmpdir) / "index.sldl")
            cmd = build_command(
                sldl_path=self._sldl,
                input_arg=sl.source_url or "",
                download_path=sl.download_path,
                index_path=index_path,
                extra_args=self._extra,
            )
            with log_file.open("w") as logf:
                proc_holder: dict = {}
                async for proc, line in stream_sldl(cmd):
                    if not proc_holder:
                        proc_holder["pid"] = proc.pid
                        if job_id is not None:
                            await self._record_pid(job_id, proc.pid)
                        continue
                    if not line:
                        continue
                    logf.write(line + "\n")
                    logf.flush()
                    ev = parse_progress_line(line)
                    if ev is not None:
                        await self._bus.publish(Event(
                            name="log.append", topic="jobs",
                            data={"job_id": job_id, "lines": [line]},
                        ))
                        await self._bus.publish(Event(
                            name="job.update", topic="jobs",
                            data={"id": job_id, "progress": {"message": ev.kind, "track": ev.track_label}},
                        ))

            try:
                index_text = Path(index_path).read_text()
            except FileNotFoundError:
                index_text = ""
            index = parse_index_csv(index_text)

        # Reconcile: load tracks for this list and match.
        async with self._sf() as session:
            tracks = (await session.execute(
                select(TrackEntry).where(TrackEntry.source_list_id == list_id)
            )).scalars().all()
            results = match_index_to_tracks(index, tracks)
            for r in results:
                if r.track_id is None:
                    continue
                new_status = _INDEX_TO_TRACK_STATUS.get(r.state, "pending")
                d = Download(
                    track_entry_id=r.track_id,
                    job_id=job_id,
                    status=new_status if new_status in {"done", "failed"} else "partial",
                    file_path=r.file_path or None,
                    sldl_match_path=r.file_path or None,
                    error=r.failure_reason or None,
                    finished_at=datetime.now(timezone.utc),
                )
                session.add(d)
                await session.flush()
                await session.execute(
                    update(TrackEntry)
                    .where(TrackEntry.id == r.track_id)
                    .values(download_status=new_status, download_id=d.id)
                )
            await session.commit()

        await self._src.update(list_id, {
            "last_synced_at": datetime.now(timezone.utc),
            "last_sync_status": "ok",
            "last_error": None,
        })
        await self._bus.publish(Event(
            name="list.updated", topic="lists",
            data={"id": list_id, "last_synced_at": "now"},
        ))

    async def _record_pid(self, job_id: int, pid: int) -> None:
        async with self._sf() as session:
            await session.execute(update(Job).where(Job.id == job_id).values(pid=pid))
            await session.commit()
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/unit/core/test_sync.py -v
```
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add src/toolcrate/core/sync.py tests/unit/core/test_sync.py
git commit -m "feat(core): SyncService orchestrates sldl + reconcile + status updates"
```

---

## Task 14: FastAPI app factory + middleware + auth dep

**Files:**
- Create: `src/toolcrate/web/__init__.py`
- Create: `src/toolcrate/web/app.py`
- Create: `src/toolcrate/web/deps.py`
- Create: `src/toolcrate/web/middleware.py`
- Create: `src/toolcrate/web/problem.py`
- Create: `tests/unit/web/__init__.py`
- Create: `tests/unit/web/test_middleware.py`
- Create: `tests/unit/web/test_auth.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/web/test_middleware.py
from fastapi import FastAPI
from fastapi.testclient import TestClient
from toolcrate.web.middleware import OriginHostGuardMiddleware


def _build_app():
    app = FastAPI()
    app.add_middleware(OriginHostGuardMiddleware,
                       allowed_hosts={"localhost", "127.0.0.1"})

    @app.get("/x")
    def x():
        return {"ok": True}

    return app


def test_localhost_host_allowed():
    c = TestClient(_build_app())
    r = c.get("/x", headers={"Host": "localhost"})
    assert r.status_code == 200


def test_evil_host_rejected():
    c = TestClient(_build_app())
    r = c.get("/x", headers={"Host": "evil.example"})
    assert r.status_code == 403


def test_origin_must_be_localhost_when_present():
    c = TestClient(_build_app())
    r = c.get("/x", headers={"Host": "localhost", "Origin": "https://evil.example"})
    assert r.status_code == 403


def test_origin_localhost_allowed():
    c = TestClient(_build_app())
    r = c.get("/x", headers={"Host": "localhost", "Origin": "http://localhost:48721"})
    assert r.status_code == 200
```

```python
# tests/unit/web/test_auth.py
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from toolcrate.web.deps import api_token_auth


def _build_app(token_hash: str):
    app = FastAPI()

    @app.get("/x")
    def x(_=Depends(api_token_auth(token_hash=token_hash))):
        return {"ok": True}

    return app


def test_missing_token_rejected():
    import hashlib
    h = hashlib.sha256(b"secret").hexdigest()
    c = TestClient(_build_app(h))
    assert c.get("/x").status_code == 401


def test_wrong_token_rejected():
    import hashlib
    h = hashlib.sha256(b"secret").hexdigest()
    c = TestClient(_build_app(h))
    assert c.get("/x", headers={"Authorization": "Bearer wrong"}).status_code == 401


def test_correct_token_passes():
    import hashlib
    h = hashlib.sha256(b"secret").hexdigest()
    c = TestClient(_build_app(h))
    r = c.get("/x", headers={"Authorization": "Bearer secret"})
    assert r.status_code == 200
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/unit/web/ -v
```
Expected: ImportError.

- [ ] **Step 3: Create `src/toolcrate/web/__init__.py`**

```python
"""HTTP API layer for toolcrate."""
```

- [ ] **Step 4: Create `src/toolcrate/web/middleware.py`**

```python
"""HTTP middleware: Origin/Host guard for DNS-rebinding defense.

Local-only deployment trusts only requests whose Host header is one of the
allowed local hostnames. When an Origin header is present (browser request),
it must also be a localhost variant.
"""

from __future__ import annotations

from urllib.parse import urlparse

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class OriginHostGuardMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, allowed_hosts: set[str]) -> None:
        super().__init__(app)
        self._hosts = {h.lower() for h in allowed_hosts}

    async def dispatch(self, request, call_next):
        host = (request.headers.get("host") or "").split(":")[0].lower()
        if host not in self._hosts:
            return JSONResponse(status_code=403, content={"detail": "host not allowed"})
        origin = request.headers.get("origin")
        if origin:
            ohost = (urlparse(origin).hostname or "").lower()
            if ohost not in self._hosts:
                return JSONResponse(status_code=403, content={"detail": "origin not allowed"})
        return await call_next(request)
```

- [ ] **Step 5: Create `src/toolcrate/web/problem.py`**

```python
"""RFC 7807 problem+json helpers."""

from __future__ import annotations

from fastapi.responses import JSONResponse


def problem(*, status: int, code: str, title: str, detail: str = "") -> JSONResponse:
    return JSONResponse(
        status_code=status,
        media_type="application/problem+json",
        content={"type": f"about:blank#{code}", "title": title,
                 "status": status, "detail": detail, "code": code},
    )
```

- [ ] **Step 6: Create `src/toolcrate/web/deps.py`**

```python
"""Shared FastAPI dependencies."""

from __future__ import annotations

import hashlib
import hmac

from fastapi import Header, HTTPException, status


def api_token_auth(*, token_hash: str):
    """Build a dependency that compares Authorization: Bearer <token> against a sha256 hash."""

    expected = token_hash.lower()

    def _dep(authorization: str | None = Header(default=None)) -> None:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing bearer token")
        token = authorization[len("Bearer "):]
        got = hashlib.sha256(token.encode("utf-8")).hexdigest()
        if not hmac.compare_digest(got, expected):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token")

    return _dep
```

- [ ] **Step 7: Create `src/toolcrate/web/app.py`**

```python
"""FastAPI app factory.

create_app builds an application instance from explicit dependencies so
tests can construct one with stubs. The CLI's `serve` command builds the
real graph and calls into this factory.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from fastapi import FastAPI

from .middleware import OriginHostGuardMiddleware


@dataclass
class AppDeps:
    api_token_hash: str
    allowed_hosts: set[str]
    routers: Iterable = ()


def create_app(deps: AppDeps) -> FastAPI:
    app = FastAPI(title="toolcrate", version="0.1.0", docs_url="/api/docs",
                  redoc_url=None, openapi_url="/api/openapi.json")
    app.add_middleware(OriginHostGuardMiddleware, allowed_hosts=deps.allowed_hosts)
    for router in deps.routers:
        app.include_router(router)
    return app
```

- [ ] **Step 8: Run tests**

```bash
uv run pytest tests/unit/web/ -v
```
Expected: 7 passed.

- [ ] **Step 9: Commit**

```bash
git add src/toolcrate/web/ tests/unit/web/
git commit -m "feat(web): app factory + Origin/Host guard + bearer token auth"
```

---

## Task 15: Pydantic schemas

**Files:**
- Create: `src/toolcrate/web/schemas/__init__.py`
- Create: `src/toolcrate/web/schemas/common.py`
- Create: `src/toolcrate/web/schemas/lists.py`
- Create: `src/toolcrate/web/schemas/tracks.py`
- Create: `src/toolcrate/web/schemas/jobs.py`

- [ ] **Step 1: Create the schema files**

```python
# src/toolcrate/web/schemas/__init__.py
"""Pydantic v2 request/response schemas for the toolcrate API."""
```

```python
# src/toolcrate/web/schemas/common.py
from __future__ import annotations

from typing import Generic, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int


class ProblemDetail(BaseModel):
    type: str = "about:blank"
    title: str
    status: int
    detail: str = ""
    code: str = ""
```

```python
# src/toolcrate/web/schemas/lists.py
from __future__ import annotations

from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict


SourceType = Literal["spotify_playlist", "youtube_djset", "manual"]


class SourceListIn(BaseModel):
    name: str = Field(min_length=1, max_length=256)
    source_url: str = ""
    source_type: SourceType | None = None
    download_path: str | None = None
    sync_interval: str = "manual"
    oauth_account_id: int | None = None


class SourceListPatch(BaseModel):
    name: str | None = None
    download_path: str | None = None
    sync_interval: str | None = None
    enabled: bool | None = None


class SourceListOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    source_type: SourceType
    source_url: str
    external_id: str
    download_path: str
    enabled: bool
    sync_interval: str
    last_synced_at: datetime | None
    last_sync_status: str
    last_error: str | None
    oauth_account_id: int | None
    metadata_json: dict
    created_at: datetime
    updated_at: datetime
```

```python
# src/toolcrate/web/schemas/tracks.py
from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict


class TrackEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    source_list_id: int
    position: int
    artist: str | None
    title: str | None
    album: str | None
    duration_sec: int | None
    isrc: str | None
    spotify_track_id: str | None
    yt_timestamp_sec: int | None
    recognition_confidence: float | None
    download_status: str
    download_id: int | None
    first_seen_at: datetime
    last_seen_at: datetime
    removed_at: datetime | None
```

```python
# src/toolcrate/web/schemas/jobs.py
from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    type: str
    state: str
    priority: int
    source_list_id: int | None
    attempts: int
    max_attempts: int
    scheduled_for: datetime
    started_at: datetime | None
    finished_at: datetime | None
    progress_json: dict
    error: str | None


class JobLogPage(BaseModel):
    job_id: int
    lines: list[str]
    next_offset: int | None
```

- [ ] **Step 2: Sanity-import in REPL**

```bash
uv run python -c "from toolcrate.web.schemas.lists import SourceListIn; print(SourceListIn(name='x'))"
```
Expected: prints a valid model instance.

- [ ] **Step 3: Commit**

```bash
git add src/toolcrate/web/schemas/
git commit -m "feat(web): pydantic v2 schemas for lists/tracks/jobs"
```

---

## Task 16: Routers — health + info + lists CRUD

**Files:**
- Create: `src/toolcrate/web/routers/__init__.py`
- Create: `src/toolcrate/web/routers/health.py`
- Create: `src/toolcrate/web/routers/lists.py`
- Create: `tests/integration/test_health_api.py`
- Create: `tests/integration/test_lists_api.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create test infrastructure (`tests/conftest.py`)**

```python
"""Shared pytest fixtures: in-memory app + DB + dependency override."""

from __future__ import annotations

import hashlib
import os
from typing import AsyncIterator

import pytest
from fastapi.testclient import TestClient

from toolcrate.core.config import SettingsStore
from toolcrate.core.events import EventBus
from toolcrate.core.jobs import JobQueue, Worker, JobType
from toolcrate.core.source_lists import SourceListService
from toolcrate.db.models import Base
from toolcrate.db.session import create_engine_for_url, get_async_session_factory


TEST_TOKEN = "test-token"
TEST_TOKEN_HASH = hashlib.sha256(TEST_TOKEN.encode()).hexdigest()


@pytest.fixture
async def session_factory():
    engine = create_engine_for_url("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = get_async_session_factory(engine)
    yield factory
    await engine.dispose()


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {TEST_TOKEN}", "Host": "localhost"}


@pytest.fixture
async def app(session_factory):
    """Build a wired FastAPI app for integration tests."""
    from toolcrate.web.app import create_app, AppDeps
    from toolcrate.web.routers.health import build_router as build_health
    from toolcrate.web.routers.lists import build_router as build_lists

    bus = EventBus()
    src = SourceListService(session_factory, music_root="/tmp/m")
    queue = JobQueue(session_factory)

    deps = AppDeps(
        api_token_hash=TEST_TOKEN_HASH,
        allowed_hosts={"localhost", "127.0.0.1", "testserver"},
        routers=[
            build_health(version="0.1.0-test"),
            build_lists(src=src, queue=queue, token_hash=TEST_TOKEN_HASH),
        ],
    )
    return create_app(deps)


@pytest.fixture
def client(app) -> TestClient:
    return TestClient(app)
```

Add to `tests/__init__.py` if not present (empty file is fine).

- [ ] **Step 2: Write the failing test**

```python
# tests/integration/test_health_api.py
def test_health_no_auth_required(client, auth_headers):
    r = client.get("/api/v1/health", headers={"Host": "localhost"})
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_info_returns_version(client, auth_headers):
    r = client.get("/api/v1/info", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["version"] == "0.1.0-test"
```

```python
# tests/integration/test_lists_api.py
def test_create_spotify_list_via_paste_url(client, auth_headers):
    r = client.post("/api/v1/lists",
                    headers=auth_headers,
                    json={"name": "Late Night",
                          "source_url": "https://open.spotify.com/playlist/abc123"})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["source_type"] == "spotify_playlist"
    assert body["external_id"] == "abc123"


def test_list_returns_created(client, auth_headers):
    client.post("/api/v1/lists", headers=auth_headers,
                json={"name": "x", "source_type": "manual"})
    r = client.get("/api/v1/lists", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()["items"]) == 1


def test_get_missing_returns_404(client, auth_headers):
    r = client.get("/api/v1/lists/9999", headers=auth_headers)
    assert r.status_code == 404


def test_patch_updates_field(client, auth_headers):
    create = client.post("/api/v1/lists", headers=auth_headers,
                         json={"name": "x", "source_type": "manual"}).json()
    r = client.patch(f"/api/v1/lists/{create['id']}", headers=auth_headers,
                     json={"name": "renamed"})
    assert r.status_code == 200
    assert r.json()["name"] == "renamed"


def test_delete_removes_list(client, auth_headers):
    create = client.post("/api/v1/lists", headers=auth_headers,
                         json={"name": "x", "source_type": "manual"}).json()
    r = client.delete(f"/api/v1/lists/{create['id']}", headers=auth_headers)
    assert r.status_code == 204
    r = client.get(f"/api/v1/lists/{create['id']}", headers=auth_headers)
    assert r.status_code == 404


def test_unauthorized_request_rejected(client):
    r = client.get("/api/v1/lists", headers={"Host": "localhost"})
    assert r.status_code == 401
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
uv run pytest tests/integration/test_lists_api.py tests/integration/test_health_api.py -v
```
Expected: ImportError on routers.

- [ ] **Step 4: Create `src/toolcrate/web/routers/__init__.py`** (empty docstring)

```python
"""HTTP routers."""
```

- [ ] **Step 5: Create `src/toolcrate/web/routers/health.py`**

```python
"""Health and info endpoints. Health is unauthenticated; info is auth'd."""

from __future__ import annotations

from fastapi import APIRouter, Depends


def build_router(*, version: str) -> APIRouter:
    router = APIRouter(prefix="/api/v1")

    @router.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @router.get("/info")
    def info() -> dict:
        return {"version": version}

    return router
```

- [ ] **Step 6: Create `src/toolcrate/web/routers/lists.py`**

```python
"""Source list CRUD + sync trigger."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from toolcrate.core.exceptions import NotFound, ValidationError
from toolcrate.core.jobs import JobQueue, JobType
from toolcrate.core.source_lists import SourceListService
from toolcrate.web.deps import api_token_auth
from toolcrate.web.schemas.common import Page
from toolcrate.web.schemas.lists import SourceListIn, SourceListOut, SourceListPatch


def build_router(*, src: SourceListService, queue: JobQueue, token_hash: str) -> APIRouter:
    auth = Depends(api_token_auth(token_hash=token_hash))
    router = APIRouter(prefix="/api/v1/lists", dependencies=[auth])

    @router.get("", response_model=Page[SourceListOut])
    async def list_all(source_type: str | None = None, enabled: bool | None = None) -> Page:
        rows = await src.list(source_type=source_type, enabled=enabled)
        return Page(items=[SourceListOut.model_validate(r) for r in rows],
                    total=len(rows), limit=len(rows), offset=0)

    @router.post("", response_model=SourceListOut, status_code=status.HTTP_201_CREATED)
    async def create(payload: SourceListIn) -> SourceListOut:
        try:
            row = await src.create(
                name=payload.name,
                source_url=payload.source_url,
                source_type=payload.source_type,
                download_path=payload.download_path,
                sync_interval=payload.sync_interval,
                oauth_account_id=payload.oauth_account_id,
            )
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        return SourceListOut.model_validate(row)

    @router.get("/{list_id}", response_model=SourceListOut)
    async def get_one(list_id: int) -> SourceListOut:
        try:
            row = await src.get(list_id)
        except NotFound:
            raise HTTPException(status_code=404, detail="list not found")
        return SourceListOut.model_validate(row)

    @router.patch("/{list_id}", response_model=SourceListOut)
    async def patch(list_id: int, payload: SourceListPatch) -> SourceListOut:
        fields = {k: v for k, v in payload.model_dump(exclude_unset=True).items()}
        try:
            row = await src.update(list_id, fields)
        except NotFound:
            raise HTTPException(status_code=404, detail="list not found")
        return SourceListOut.model_validate(row)

    @router.delete("/{list_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete(list_id: int) -> None:
        try:
            await src.delete(list_id)
        except NotFound:
            raise HTTPException(status_code=404, detail="list not found")

    @router.post("/{list_id}/sync", status_code=status.HTTP_202_ACCEPTED)
    async def trigger_sync(list_id: int) -> dict:
        try:
            await src.get(list_id)
        except NotFound:
            raise HTTPException(status_code=404, detail="list not found")
        job = await queue.enqueue(JobType.SYNC_LIST, payload={"list_id": list_id},
                                  source_list_id=list_id)
        return {"job_id": job.id}

    return router
```

- [ ] **Step 7: Run tests**

```bash
uv run pytest tests/integration/test_health_api.py tests/integration/test_lists_api.py -v
```
Expected: 7 passed.

- [ ] **Step 8: Commit**

```bash
git add src/toolcrate/web/routers/ tests/conftest.py tests/integration/test_health_api.py tests/integration/test_lists_api.py
git commit -m "feat(web): /health, /info, /lists CRUD + sync trigger"
```

---

## Task 17: Routers — tracks + jobs

**Files:**
- Create: `src/toolcrate/web/routers/tracks.py`
- Create: `src/toolcrate/web/routers/jobs.py`
- Create: `tests/integration/test_tracks_api.py`
- Create: `tests/integration/test_jobs_api.py`
- Modify: `tests/conftest.py` (extend `app` fixture to include new routers)

- [ ] **Step 1: Extend conftest fixture**

In `tests/conftest.py`, modify the `app` fixture to also build and register the tracks and jobs routers:

```python
# inside the existing `app` fixture, before deps is constructed:
from toolcrate.web.routers.tracks import build_router as build_tracks
from toolcrate.web.routers.jobs import build_router as build_jobs

# After other routers, add to the routers list:
# build_tracks(src=src, session_factory=session_factory, token_hash=TEST_TOKEN_HASH),
# build_jobs(queue=queue, session_factory=session_factory, token_hash=TEST_TOKEN_HASH),
```

Show the full final conftest fixture to leave no ambiguity:

```python
@pytest.fixture
async def app(session_factory):
    from toolcrate.web.app import create_app, AppDeps
    from toolcrate.web.routers.health import build_router as build_health
    from toolcrate.web.routers.lists import build_router as build_lists
    from toolcrate.web.routers.tracks import build_router as build_tracks
    from toolcrate.web.routers.jobs import build_router as build_jobs

    bus = EventBus()
    src = SourceListService(session_factory, music_root="/tmp/m")
    queue = JobQueue(session_factory)

    deps = AppDeps(
        api_token_hash=TEST_TOKEN_HASH,
        allowed_hosts={"localhost", "127.0.0.1", "testserver"},
        routers=[
            build_health(version="0.1.0-test"),
            build_lists(src=src, queue=queue, token_hash=TEST_TOKEN_HASH),
            build_tracks(src=src, session_factory=session_factory, queue=queue, token_hash=TEST_TOKEN_HASH),
            build_jobs(queue=queue, session_factory=session_factory, token_hash=TEST_TOKEN_HASH),
        ],
    )
    return create_app(deps)
```

- [ ] **Step 2: Write failing tests**

```python
# tests/integration/test_tracks_api.py
def test_list_tracks_for_list(client, auth_headers, session_factory):
    r = client.post("/api/v1/lists", headers=auth_headers,
                    json={"name": "x", "source_type": "manual"})
    list_id = r.json()["id"]
    r = client.get(f"/api/v1/lists/{list_id}/tracks", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["items"] == []


def test_track_skip_marks_status(client, auth_headers, session_factory):
    import asyncio
    from toolcrate.db.models import TrackEntry

    create = client.post("/api/v1/lists", headers=auth_headers,
                         json={"name": "x", "source_type": "manual"}).json()
    async def seed():
        async with session_factory() as session:
            t = TrackEntry(source_list_id=create["id"], position=1, artist="A", title="B")
            session.add(t)
            await session.commit()
            await session.refresh(t)
            return t.id
    track_id = asyncio.get_event_loop().run_until_complete(seed())

    r = client.post(f"/api/v1/lists/{create['id']}/tracks/{track_id}/skip",
                    headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["download_status"] == "skipped"
```

```python
# tests/integration/test_jobs_api.py
def test_list_jobs_empty(client, auth_headers):
    r = client.get("/api/v1/jobs", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["items"] == []


def test_get_missing_job_404(client, auth_headers):
    r = client.get("/api/v1/jobs/9999", headers=auth_headers)
    assert r.status_code == 404


def test_cancel_job(client, auth_headers):
    list_create = client.post("/api/v1/lists", headers=auth_headers,
                              json={"name": "x", "source_type": "manual"}).json()
    sync = client.post(f"/api/v1/lists/{list_create['id']}/sync", headers=auth_headers)
    job_id = sync.json()["job_id"]
    r = client.post(f"/api/v1/jobs/{job_id}/cancel", headers=auth_headers)
    assert r.status_code == 200
    fetched = client.get(f"/api/v1/jobs/{job_id}", headers=auth_headers).json()
    assert fetched["state"] == "cancelled"
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
uv run pytest tests/integration/test_tracks_api.py tests/integration/test_jobs_api.py -v
```
Expected: ImportError.

- [ ] **Step 4: Create `src/toolcrate/web/routers/tracks.py`**

```python
"""Track list and per-track actions."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from toolcrate.core.exceptions import NotFound
from toolcrate.core.jobs import JobQueue, JobType
from toolcrate.core.source_lists import SourceListService
from toolcrate.db.models import TrackEntry
from toolcrate.web.deps import api_token_auth
from toolcrate.web.schemas.common import Page
from toolcrate.web.schemas.tracks import TrackEntryOut


def build_router(
    *, src: SourceListService,
    session_factory: async_sessionmaker[AsyncSession],
    queue: JobQueue,
    token_hash: str,
) -> APIRouter:
    auth = Depends(api_token_auth(token_hash=token_hash))
    router = APIRouter(prefix="/api/v1/lists", dependencies=[auth])

    @router.get("/{list_id}/tracks", response_model=Page[TrackEntryOut])
    async def list_tracks(
        list_id: int, status: str | None = None,
        limit: int = Query(default=200, le=2000), offset: int = 0,
    ) -> Page:
        try:
            await src.get(list_id)
        except NotFound:
            raise HTTPException(status_code=404, detail="list not found")
        async with session_factory() as session:
            stmt = select(TrackEntry).where(TrackEntry.source_list_id == list_id)
            if status is not None:
                stmt = stmt.where(TrackEntry.download_status == status)
            stmt = stmt.order_by(TrackEntry.position).offset(offset).limit(limit)
            rows = (await session.execute(stmt)).scalars().all()
            return Page(items=[TrackEntryOut.model_validate(r) for r in rows],
                        total=len(rows), limit=limit, offset=offset)

    @router.post("/{list_id}/tracks/{track_id}/skip", response_model=TrackEntryOut)
    async def skip_track(list_id: int, track_id: int) -> TrackEntryOut:
        async with session_factory() as session:
            row = await session.get(TrackEntry, track_id)
            if row is None or row.source_list_id != list_id:
                raise HTTPException(status_code=404, detail="track not found")
            row.download_status = "skipped"
            await session.commit()
            await session.refresh(row)
            return TrackEntryOut.model_validate(row)

    @router.post("/{list_id}/tracks/{track_id}/download", status_code=202)
    async def trigger_track_download(list_id: int, track_id: int) -> dict:
        async with session_factory() as session:
            row = await session.get(TrackEntry, track_id)
            if row is None or row.source_list_id != list_id:
                raise HTTPException(status_code=404, detail="track not found")
        job = await queue.enqueue(JobType.DOWNLOAD_TRACK,
                                  payload={"track_id": track_id, "list_id": list_id},
                                  source_list_id=list_id)
        return {"job_id": job.id}

    return router
```

- [ ] **Step 5: Create `src/toolcrate/web/routers/jobs.py`**

```python
"""Job listing, fetch, log, cancel, retry."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from toolcrate.core.jobs import JobQueue
from toolcrate.db.models import Job
from toolcrate.web.deps import api_token_auth
from toolcrate.web.schemas.common import Page
from toolcrate.web.schemas.jobs import JobOut, JobLogPage


def build_router(
    *, queue: JobQueue,
    session_factory: async_sessionmaker[AsyncSession],
    token_hash: str,
) -> APIRouter:
    auth = Depends(api_token_auth(token_hash=token_hash))
    router = APIRouter(prefix="/api/v1/jobs", dependencies=[auth])

    @router.get("", response_model=Page[JobOut])
    async def list_jobs(
        state: str | None = None, type: str | None = None,
        list_id: int | None = None,
        limit: int = Query(default=100, le=1000), offset: int = 0,
    ) -> Page:
        async with session_factory() as session:
            stmt = select(Job)
            if state is not None:
                stmt = stmt.where(Job.state == state)
            if type is not None:
                stmt = stmt.where(Job.type == type)
            if list_id is not None:
                stmt = stmt.where(Job.source_list_id == list_id)
            stmt = stmt.order_by(Job.id.desc()).offset(offset).limit(limit)
            rows = (await session.execute(stmt)).scalars().all()
            return Page(items=[JobOut.model_validate(r) for r in rows],
                        total=len(rows), limit=limit, offset=offset)

    @router.get("/{job_id}", response_model=JobOut)
    async def get_job(job_id: int) -> JobOut:
        async with session_factory() as session:
            row = await session.get(Job, job_id)
            if row is None:
                raise HTTPException(status_code=404, detail="job not found")
            return JobOut.model_validate(row)

    @router.get("/{job_id}/log", response_model=JobLogPage)
    async def get_job_log(job_id: int, offset: int = 0, limit: int = 1000) -> JobLogPage:
        async with session_factory() as session:
            row = await session.get(Job, job_id)
            if row is None:
                raise HTTPException(status_code=404, detail="job not found")
        if not row.log_path:
            return JobLogPage(job_id=job_id, lines=[], next_offset=None)
        try:
            with open(row.log_path) as f:
                all_lines = f.readlines()
        except FileNotFoundError:
            return JobLogPage(job_id=job_id, lines=[], next_offset=None)
        slice_ = all_lines[offset:offset + limit]
        next_offset = offset + len(slice_) if (offset + limit) < len(all_lines) else None
        return JobLogPage(job_id=job_id, lines=[s.rstrip("\n") for s in slice_], next_offset=next_offset)

    @router.post("/{job_id}/cancel", response_model=JobOut)
    async def cancel(job_id: int) -> JobOut:
        async with session_factory() as session:
            row = await session.get(Job, job_id)
            if row is None:
                raise HTTPException(status_code=404, detail="job not found")
        await queue.cancel(job_id)
        async with session_factory() as session:
            row = await session.get(Job, job_id)
            return JobOut.model_validate(row)

    @router.post("/{job_id}/retry", response_model=JobOut)
    async def retry(job_id: int) -> JobOut:
        async with session_factory() as session:
            row = await session.get(Job, job_id)
            if row is None:
                raise HTTPException(status_code=404, detail="job not found")
            row.state = "pending"
            row.scheduled_for = datetime.now(timezone.utc)
            row.attempts = 0
            row.error = None
            row.finished_at = None
            await session.commit()
            await session.refresh(row)
            return JobOut.model_validate(row)

    return router
```

- [ ] **Step 6: Run tests**

```bash
uv run pytest tests/integration/test_tracks_api.py tests/integration/test_jobs_api.py -v
```
Expected: tests pass.

- [ ] **Step 7: Commit**

```bash
git add src/toolcrate/web/routers/tracks.py src/toolcrate/web/routers/jobs.py tests/conftest.py tests/integration/test_tracks_api.py tests/integration/test_jobs_api.py
git commit -m "feat(web): tracks + jobs routers"
```

---

## Task 18: SSE events router

**Files:**
- Create: `src/toolcrate/web/routers/events.py`
- Create: `tests/integration/test_events_sse.py`
- Modify: `tests/conftest.py` (add events router + bus to fixture)

- [ ] **Step 1: Extend conftest fixture to wire bus + events router**

```python
# Update inside the `app` fixture in tests/conftest.py:
from toolcrate.web.routers.events import build_router as build_events
# ... after creating bus:
deps = AppDeps(
    ...,
    routers=[
        ...,
        build_events(bus=bus, token_hash=TEST_TOKEN_HASH),
    ],
)

# Also expose bus to tests:
return app, bus  # change return — and fixture consumers update
```

Adjust the fixture so it returns a small object exposing both `app` and `bus`:

```python
import dataclasses

@dataclasses.dataclass
class AppCtx:
    app: object
    bus: EventBus

@pytest.fixture
async def appctx(session_factory) -> AppCtx:
    # ... build everything ...
    return AppCtx(app=create_app(deps), bus=bus)


@pytest.fixture
def client(appctx) -> TestClient:
    return TestClient(appctx.app)
```

Update existing fixtures and tests to consume `client` from `appctx` (already do) and `appctx.bus` where needed. Run the existing tests to confirm nothing regresses:

```bash
uv run pytest tests/integration -x -q
```

Fix any tests that broke from the rename (`app` → `appctx`).

- [ ] **Step 2: Write the failing test**

```python
# tests/integration/test_events_sse.py
import asyncio
import pytest

from toolcrate.core.events import Event


def test_events_endpoint_streams_published_events(appctx, auth_headers):
    """Use httpx streaming client to read 1 SSE event then disconnect."""
    import httpx
    from threading import Thread
    import time

    received: list[str] = []

    async def consume():
        # Open the stream with the underlying app via TestClient pattern
        # We use httpx + ASGITransport for proper streaming
        transport = httpx.ASGITransport(app=appctx.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://localhost",
                                     timeout=5) as ac:
            async with ac.stream("GET", "/api/v1/events", headers=auth_headers) as resp:
                assert resp.status_code == 200
                async for chunk in resp.aiter_lines():
                    received.append(chunk)
                    if any(s.startswith("event:") for s in received):
                        break

    async def publisher():
        # Give consumer a moment to subscribe
        await asyncio.sleep(0.1)
        await appctx.bus.publish(Event(name="job.update", topic="jobs",
                                       data={"id": 1, "state": "running"}))

    async def both():
        await asyncio.gather(consume(), publisher())

    asyncio.get_event_loop().run_until_complete(both())
    assert any("event: job.update" in l or l.startswith("data:") for l in received)
```

- [ ] **Step 3: Run test to verify it fails**

```bash
uv run pytest tests/integration/test_events_sse.py -v
```
Expected: ImportError.

- [ ] **Step 4: Create `src/toolcrate/web/routers/events.py`**

```python
"""Server-Sent Events stream multiplexed across topics."""

from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator

from fastapi import APIRouter, Depends, Query
from sse_starlette.sse import EventSourceResponse

from toolcrate.core.events import EventBus
from toolcrate.web.deps import api_token_auth


def build_router(*, bus: EventBus, token_hash: str) -> APIRouter:
    auth = Depends(api_token_auth(token_hash=token_hash))
    router = APIRouter(prefix="/api/v1", dependencies=[auth])

    @router.get("/events")
    async def events(topics: str | None = Query(default=None)):
        topic_set = set(topics.split(",")) if topics else None
        sub = bus.subscribe(topics=topic_set)

        async def gen() -> AsyncIterator[dict]:
            try:
                async for event in sub:
                    yield {"event": event.name, "data": json.dumps(event.data)}
            finally:
                await bus.unsubscribe(sub)

        return EventSourceResponse(gen(), ping=15)

    return router
```

- [ ] **Step 5: Run tests**

```bash
uv run pytest tests/integration/test_events_sse.py -v
```
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/toolcrate/web/routers/events.py tests/conftest.py tests/integration/test_events_sse.py
git commit -m "feat(web): SSE events router via sse-starlette"
```

---

## Task 19: Worker job dispatch wiring

**Files:**
- Create: `src/toolcrate/core/worker_handlers.py`
- Create: `tests/unit/core/test_worker_handlers.py`

**Why:** map JobType → service call, with a per-job log path and event publishing.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/core/test_worker_handlers.py
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/core/test_worker_handlers.py -v
```
Expected: ImportError.

- [ ] **Step 3: Create `src/toolcrate/core/worker_handlers.py`**

```python
"""Wire each JobType to the right service call.

A handler entry is omitted entirely if its service is None. The Worker's
unknown-type fallback then marks such jobs failed cleanly.
"""

from __future__ import annotations

import logging
import tempfile
from typing import Any, Awaitable, Callable
from pathlib import Path

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .events import EventBus
from .jobs import JobType
from toolcrate.db.models import Job


logger = logging.getLogger(__name__)


Handler = Callable[[Job], Awaitable[None]]


def _make_log_path(job: Job) -> str:
    return tempfile.mktemp(prefix=f"toolcrate-job-{job.id}-", suffix=".log")


def build_handlers(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    bus: EventBus,
    sync_service,
    recognition_service,
    download_service,
    library_service,
) -> dict[JobType, Handler]:
    handlers: dict[JobType, Handler] = {}

    if sync_service is not None:
        async def _sync(job: Job) -> None:
            payload = job.payload_json or {}
            list_id = int(payload["list_id"])
            log_path = _make_log_path(job)
            async with session_factory() as session:
                await session.execute(update(Job).where(Job.id == job.id)
                                      .values(log_path=log_path))
                await session.commit()
            await sync_service.run_for_list(list_id, job_id=job.id, log_path=log_path)

        handlers[JobType.SYNC_LIST] = _sync

    if download_service is not None:
        async def _download(job: Job) -> None:
            payload = job.payload_json or {}
            track_id = int(payload["track_id"])
            log_path = _make_log_path(job)
            async with session_factory() as session:
                await session.execute(update(Job).where(Job.id == job.id)
                                      .values(log_path=log_path))
                await session.commit()
            await download_service.run_single_track(track_id, job_id=job.id, log_path=log_path)

        handlers[JobType.DOWNLOAD_TRACK] = _download

    if recognition_service is not None:
        async def _recognize(job: Job) -> None:
            payload = job.payload_json or {}
            list_id = int(payload["list_id"])
            await recognition_service.run_for_list(list_id, job_id=job.id)

        handlers[JobType.RECOGNIZE_DJSET] = _recognize

    if library_service is not None:
        async def _scan(job: Job) -> None:
            await library_service.scan(job_id=job.id)

        handlers[JobType.LIBRARY_SCAN] = _scan

    return handlers
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/unit/core/test_worker_handlers.py -v
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/toolcrate/core/worker_handlers.py tests/unit/core/test_worker_handlers.py
git commit -m "feat(core): wire JobType -> service handlers"
```

---

## Task 20: DownloadService (single-track sldl)

**Files:**
- Create: `src/toolcrate/core/downloads.py`
- Create: `tests/unit/core/test_downloads.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/core/test_downloads.py
import os
import textwrap
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
    script = tmp_path / "fake-sldl"
    script.write_text(textwrap.dedent("""\
        #!/usr/bin/env bash
        set -eu
        idx=""; next=0
        for a in "$@"; do
          if [ "$next" = "1" ]; then idx="$a"; next=0; continue; fi
          if [ "$a" = "--index-path" ]; then next=1; fi
        done
        echo "Searching: A - B"
        echo "Succeeded: A - B"
        if [ -n "$idx" ]; then
          mkdir -p "$(dirname "$idx")"
          echo "/m/x.mp3,A,B,200,1,1," > "$idx"
        fi
    """))
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/unit/core/test_downloads.py -v
```
Expected: ImportError.

- [ ] **Step 3: Create `src/toolcrate/core/downloads.py`**

```python
"""DownloadService: single-track sldl invocation + reconcile."""

from __future__ import annotations

import logging
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from .events import Event, EventBus
from .reconcile import match_index_to_tracks
from .sldl_adapter import build_command, parse_index_csv, parse_progress_line, stream_sldl
from toolcrate.db.models import Download, TrackEntry, SourceList


logger = logging.getLogger(__name__)


_INDEX_TO_TRACK_STATUS = {
    "downloaded": "done",
    "already_exists": "done",
    "failed": "failed",
    "not_found_last_time": "failed",
    "not_processed": "pending",
    "unknown": "pending",
}


class DownloadService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        bus: EventBus,
        sldl_path: str,
        sldl_extra_args: Iterable[str],
    ) -> None:
        self._sf = session_factory
        self._bus = bus
        self._sldl = sldl_path
        self._extra = list(sldl_extra_args)

    async def run_single_track(self, track_id: int, *, job_id: int | None = None,
                               log_path: str | None = None) -> None:
        async with self._sf() as session:
            track = await session.get(TrackEntry, track_id)
            if track is None:
                raise ValueError(f"track {track_id} not found")
            sl = await session.get(SourceList, track.source_list_id)
        query = f"{track.artist} - {track.title}"

        log_file = Path(log_path) if log_path else Path(tempfile.mktemp(suffix=".log"))
        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = str(Path(tmpdir) / "index.sldl")
            cmd = build_command(
                sldl_path=self._sldl, input_arg=query,
                download_path=sl.download_path, index_path=index_path,
                extra_args=[*self._extra, "--input-type", "string"],
            )
            with log_file.open("w") as logf:
                first = True
                async for proc, line in stream_sldl(cmd):
                    if first:
                        first = False
                        continue
                    if not line:
                        continue
                    logf.write(line + "\n")
                    if (ev := parse_progress_line(line)) is not None:
                        await self._bus.publish(Event(
                            name="log.append", topic="jobs",
                            data={"job_id": job_id, "lines": [line]},
                        ))
            try:
                index_text = Path(index_path).read_text()
            except FileNotFoundError:
                index_text = ""
            index = parse_index_csv(index_text)

        async with self._sf() as session:
            tracks = (await session.execute(
                select(TrackEntry).where(TrackEntry.id == track_id)
            )).scalars().all()
            results = match_index_to_tracks(index, tracks)
            for r in results:
                if r.track_id is None:
                    continue
                new_status = _INDEX_TO_TRACK_STATUS.get(r.state, "pending")
                d = Download(
                    track_entry_id=r.track_id, job_id=job_id,
                    status=new_status, file_path=r.file_path or None,
                    sldl_match_path=r.file_path or None,
                    error=r.failure_reason or None,
                    finished_at=datetime.now(timezone.utc),
                )
                session.add(d)
                await session.flush()
                await session.execute(update(TrackEntry)
                                      .where(TrackEntry.id == r.track_id)
                                      .values(download_status=new_status, download_id=d.id))
            await session.commit()
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/unit/core/test_downloads.py -v
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/toolcrate/core/downloads.py tests/unit/core/test_downloads.py
git commit -m "feat(core): DownloadService single-track sldl + reconcile"
```

---

## Task 21: CLI — `toolcrate serve`

**Files:**
- Create: `src/toolcrate/cli/serve.py`
- Modify: `src/toolcrate/cli/main.py`
- Create: `tests/integration/test_serve_cli.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/integration/test_serve_cli.py
import os
import time
import socket
import subprocess
import urllib.request
from pathlib import Path

import pytest


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def test_serve_responds_to_health(tmp_path: Path):
    """Boot `toolcrate serve` in a subprocess and hit /health."""
    env = os.environ.copy()
    env["TOOLCRATE_HOME"] = str(tmp_path)
    port = _free_port()
    proc = subprocess.Popen(
        ["uv", "run", "toolcrate", "serve", "--port", str(port), "--host", "127.0.0.1"],
        env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    try:
        deadline = time.time() + 20
        last_err = None
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/v1/health", timeout=1
                ) as resp:
                    assert resp.status == 200
                    return
            except Exception as e:  # noqa: BLE001
                last_err = e
                time.sleep(0.3)
        pytest.fail(f"server didn't come up: {last_err}")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/integration/test_serve_cli.py -v
```
Expected: command not found / `serve` doesn't exist.

- [ ] **Step 3: Create `src/toolcrate/cli/serve.py`**

```python
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
    asyncio.get_event_loop().run_until_complete(settings.seed_defaults({
        "music_root": os.path.expanduser("~/Music/toolcrate"),
        "server_port": port,
        "sldl_extra_args": [],
    }))

    music_root = asyncio.get_event_loop().run_until_complete(
        settings.get("music_root", default=os.path.expanduser("~/Music/toolcrate"))
    )
    sldl_extra_args = asyncio.get_event_loop().run_until_complete(
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
            build_health(version="0.1.0"),
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
```

- [ ] **Step 4: Wire into CLI**

Add to `src/toolcrate/cli/main.py`. Find the imports near the top and add:

```python
from .serve import serve as serve_cmd
```

Find the bottom of the file (after `main` group commands are registered) and add:

```python
main.add_command(serve_cmd)
```

If the existing main.py registers commands with `main.command(...)`, follow the same pattern. Use grep to confirm:

```bash
grep -n "main.command\|main.add_command\|main.group" src/toolcrate/cli/main.py | head
```

Add the registration line in a position consistent with existing commands.

- [ ] **Step 5: Run the integration test**

```bash
uv run pytest tests/integration/test_serve_cli.py -v
```
Expected: PASS (boots, hits /health, returns 200).

- [ ] **Step 6: Commit**

```bash
git add src/toolcrate/cli/serve.py src/toolcrate/cli/main.py tests/integration/test_serve_cli.py
git commit -m "feat(cli): add 'toolcrate serve' command (FastAPI daemon)"
```

---

## Task 22: CLI — `toolcrate migrate`

**Files:**
- Create: `src/toolcrate/cli/migrate.py`
- Modify: `src/toolcrate/cli/main.py`
- Create: `tests/integration/test_migrate_cli.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/integration/test_migrate_cli.py
import os
import subprocess
from pathlib import Path

import pytest


def test_migrate_imports_wishlist(tmp_path: Path):
    home = tmp_path / "home"
    config_dir = home / ".config" / "toolcrate"
    config_dir.mkdir(parents=True)
    (config_dir / "wishlist.txt").write_text("Daft Punk - One More Time\nDaft Punk - Around the World\n")
    (config_dir / "dj-sets.txt").write_text("https://www.youtube.com/watch?v=dQw4w9WgXcQ\n")
    (config_dir / "download-queue.txt").write_text("https://open.spotify.com/playlist/abc123\n")

    env = os.environ.copy()
    env["TOOLCRATE_HOME"] = str(home / "data")
    env["TOOLCRATE_CONFIG_DIR"] = str(config_dir)

    result = subprocess.run(["uv", "run", "toolcrate", "migrate"],
                            env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "wishlist" in result.stdout.lower()

    # Re-run: idempotent, no errors, no duplicate rows
    result2 = subprocess.run(["uv", "run", "toolcrate", "migrate"],
                             env=env, capture_output=True, text=True)
    assert result2.returncode == 0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/integration/test_migrate_cli.py -v
```
Expected: command not found.

- [ ] **Step 3: Create `src/toolcrate/cli/migrate.py`**

```python
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
        except Exception as e:  # noqa: BLE001
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
```

- [ ] **Step 4: Wire into CLI**

In `src/toolcrate/cli/main.py`:

```python
from .migrate import migrate as migrate_cmd
# ... and after main is defined:
main.add_command(migrate_cmd)
```

- [ ] **Step 5: Run the migration test**

```bash
uv run pytest tests/integration/test_migrate_cli.py -v
```
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/toolcrate/cli/migrate.py src/toolcrate/cli/main.py tests/integration/test_migrate_cli.py
git commit -m "feat(cli): add 'toolcrate migrate' for flat-file -> DB import"
```

---

## Task 23: Backward-compat — keep existing CLI behaviors green

**Files:**
- Modify: as needed in `src/toolcrate/cli/wrappers.py`, `src/toolcrate/queue/processor.py`
- Run: full existing test suite

**Why:** Phase 1 promise is "existing CLI keeps working." Confirm by running the suite.

- [ ] **Step 1: Run full test suite**

```bash
uv run pytest -x -q
```
Expected: all tests pass. If any old tests broke from imports/path changes, fix the imports (the new modules don't shadow old names — should be safe — but verify).

- [ ] **Step 2: Smoke test existing commands**

```bash
uv run toolcrate --help
uv run toolcrate info
uv run toolcrate sldl --help 2>&1 | head -5 || true
```
Expected: same output as before this branch.

- [ ] **Step 3: If any change is needed in old code, commit separately**

```bash
git add <fixed files>
git commit -m "fix: preserve existing CLI behavior alongside new daemon"
```

---

## Task 24: Documentation update

**Files:**
- Modify: `README.md`
- Create: `docs/SERVE.md`

- [ ] **Step 1: Add a new section to `README.md` after the Wishlist section**

```markdown
### Web/API daemon (Phase 1)

Toolcrate now ships a long-lived daemon that exposes a JSON API for
managing source lists and triggering downloads. No frontend yet — this
phase is backend only.

```bash
uv run toolcrate migrate         # one-time: import existing flat files
uv run toolcrate serve           # starts API on http://127.0.0.1:48721
```

The first launch generates an API token at `~/.config/toolcrate/api-token`.
Send `Authorization: Bearer <token>` on requests.

OpenAPI docs: <http://127.0.0.1:48721/api/docs>

See [docs/SERVE.md](docs/SERVE.md) for endpoint reference and tips.
```

- [ ] **Step 2: Create `docs/SERVE.md`**

```markdown
# toolcrate serve — backend daemon (Phase 1)

`toolcrate serve` runs a FastAPI app on localhost. It is the source of
truth for source lists, jobs, schedules, and downloads. It does NOT
replace the existing `toolcrate sldl`/`toolcrate shazam-tool` CLI commands
— those keep working as before.

## First-run

1. Migrate any existing flat-file state into the DB:
   ```bash
   uv run toolcrate migrate
   ```
2. Start the daemon:
   ```bash
   uv run toolcrate serve
   ```
3. Note the API token printed on first start. It is also saved to
   `~/.config/toolcrate/api-token` (mode 0600).

## Endpoints

All endpoints are under `/api/v1/`. Browse them at
`http://127.0.0.1:48721/api/docs`.

| Method | Path                                | Purpose                       |
|--------|-------------------------------------|-------------------------------|
| GET    | `/api/v1/health`                    | unauthenticated liveness      |
| GET    | `/api/v1/info`                      | version, paths                |
| GET    | `/api/v1/lists`                     | list all source lists         |
| POST   | `/api/v1/lists`                     | create from URL or manual     |
| PATCH  | `/api/v1/lists/{id}`                | update fields                 |
| DELETE | `/api/v1/lists/{id}`                | delete                        |
| POST   | `/api/v1/lists/{id}/sync`           | enqueue a sync_list job       |
| GET    | `/api/v1/lists/{id}/tracks`         | list tracks                   |
| POST   | `/api/v1/lists/{id}/tracks/{tid}/skip`     | mark track skipped     |
| POST   | `/api/v1/lists/{id}/tracks/{tid}/download` | enqueue a download_track job |
| GET    | `/api/v1/jobs`                      | list jobs                     |
| GET    | `/api/v1/jobs/{id}/log`             | paged log lines               |
| POST   | `/api/v1/jobs/{id}/cancel`          | cancel running/pending job    |
| POST   | `/api/v1/jobs/{id}/retry`           | reset a failed job            |
| GET    | `/api/v1/events`                    | SSE stream                    |

## Quick paste-URL example

```bash
TOKEN=$(cat ~/.config/toolcrate/api-token)
curl -X POST http://127.0.0.1:48721/api/v1/lists \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Late Night","source_url":"https://open.spotify.com/playlist/<id>"}'
```

## Limits in Phase 1

- No frontend UI; this phase is API-only.
- Spotify private playlists / Liked Songs require OAuth (Phase 3).
- DJ-set recognition is wired into the data model but not exposed as an API verb yet (Phase 4).
- Library scan runs only by manual job creation (Phase 5 adds dedicated endpoint).
```

- [ ] **Step 3: Commit**

```bash
git add README.md docs/SERVE.md
git commit -m "docs: add backend daemon section + SERVE.md endpoint reference"
```

---

## Task 25: Final verification

- [ ] **Step 1: Full test suite, fail-fast**

```bash
uv run pytest -x -q
```
Expected: all tests pass.

- [ ] **Step 2: Type-check the new packages**

```bash
uv run mypy src/toolcrate/db src/toolcrate/core src/toolcrate/web
```
Expected: type errors are addressed or explicitly ignored with comments. (If mypy isn't already strict in this repo, treat warnings as informational.)

- [ ] **Step 3: Lint and format**

```bash
uv run ruff format src/toolcrate tests
uv run ruff check src/toolcrate tests --fix
```

- [ ] **Step 4: Manual smoke**

```bash
uv run toolcrate migrate
uv run toolcrate serve --port 48721 &
SERVE_PID=$!
sleep 2
TOKEN=$(cat ~/.config/toolcrate/api-token)
curl -s -H "Host: localhost" http://127.0.0.1:48721/api/v1/health
curl -s -H "Authorization: Bearer $TOKEN" -H "Host: localhost" http://127.0.0.1:48721/api/v1/info
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Host: localhost" \
     -H "Content-Type: application/json" \
     -d '{"name":"smoke","source_type":"manual"}' \
     http://127.0.0.1:48721/api/v1/lists
kill $SERVE_PID
```
Expected: 200/201 responses; cleanup on exit.

- [ ] **Step 5: Commit any cleanup, push branch**

```bash
git status
git push -u origin <current-branch>
```

---

## Out of Scope for Phase 1 (covered by future plans)

- Spotify OAuth + private playlists (Phase 3)
- DJ-set audio recognition wired through Worker (Phase 4)
- Library scan service body + dedicated `/library/*` endpoints (Phase 5)
- Recurring `sync_interval` registration with APScheduler (planned for Phase 1.5 or rolled into Phase 2; currently sync triggers are manual via `POST /lists/{id}/sync`)
- Frontend (Phase 2)

If recurring schedules are needed before Phase 2 starts, add a small follow-up task: register APScheduler cron jobs at startup that call `queue.enqueue(SYNC_LIST, ...)` per `source_list.sync_interval` — straightforward extension of the existing `serve` command.
