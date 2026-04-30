"""Hatch build hook that compiles the React SPA into src/toolcrate/web/static/.

Skips gracefully when:
  - TOOLCRATE_SKIP_FRONTEND_BUILD=1 in the environment (CI lint/test stages)
  - npm is not on PATH (writes a stub index.html with install instructions)

When `npm` is available, runs `npm ci && npm run build` from the frontend
package directory; Vite is configured to emit into the static dir.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

STUB_HTML = """\
<!doctype html>
<html><head><title>toolcrate</title></head><body style="font-family:sans-serif;padding:2em">
<h1>toolcrate web UI not built</h1>
<p>Node 20+ was not on PATH when this package was built. The CLI still works.</p>
<p>To build the UI, install Node 20+ and run <code>make frontend</code> from the source tree.</p>
</body></html>
"""


class FrontendBuildHook(BuildHookInterface):
    PLUGIN_NAME = "frontend"

    def initialize(self, version: str, build_data: dict) -> None:
        root = Path(self.root)
        frontend_dir = root / "src" / "toolcrate" / "web" / "frontend"
        static_dir = root / "src" / "toolcrate" / "web" / "static"

        if os.environ.get("TOOLCRATE_SKIP_FRONTEND_BUILD") == "1":
            self.app.display_info("[frontend] TOOLCRATE_SKIP_FRONTEND_BUILD=1, skipping")
            self._ensure_stub(static_dir)
            return

        if not frontend_dir.exists():
            self.app.display_warning(f"[frontend] {frontend_dir} not found, skipping")
            self._ensure_stub(static_dir)
            return

        npm = shutil.which("npm")
        if npm is None:
            self.app.display_warning("[frontend] npm not on PATH; writing stub index.html")
            self._ensure_stub(static_dir)
            return

        static_dir.mkdir(parents=True, exist_ok=True)
        self.app.display_info("[frontend] running npm ci")
        subprocess.run([npm, "ci"], cwd=frontend_dir, check=True)
        self.app.display_info("[frontend] running npm run build")
        subprocess.run([npm, "run", "build"], cwd=frontend_dir, check=True)

        if not (static_dir / "index.html").exists():
            self.app.abort("[frontend] build finished but no index.html in static_dir")
            sys.exit(1)

    def _ensure_stub(self, static_dir: Path) -> None:
        static_dir.mkdir(parents=True, exist_ok=True)
        index = static_dir / "index.html"
        if not index.exists():
            index.write_text(STUB_HTML)
