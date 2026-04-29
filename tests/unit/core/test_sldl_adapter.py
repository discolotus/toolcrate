# tests/unit/core/test_sldl_adapter.py
from pathlib import Path

from toolcrate.core.sldl_adapter import (
    parse_index_csv,
    parse_progress_line,
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
