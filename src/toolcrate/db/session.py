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
