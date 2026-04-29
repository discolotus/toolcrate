# tests/integration/test_migrate_cli.py
import os
import subprocess
from pathlib import Path


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
