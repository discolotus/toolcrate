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
