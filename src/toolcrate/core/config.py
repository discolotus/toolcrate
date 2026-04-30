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
