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
