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
from dataclasses import dataclass, field
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
