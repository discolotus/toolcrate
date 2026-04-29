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
        deadline = time.time() + 30
        last_err = None
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/v1/health", timeout=1
                ) as resp:
                    assert resp.status == 200
                    return
            except Exception as e:
                last_err = e
                time.sleep(0.3)
        pytest.fail(f"server didn't come up: {last_err}")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
