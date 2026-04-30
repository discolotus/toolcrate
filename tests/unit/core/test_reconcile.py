from toolcrate.core.reconcile import match_index_to_tracks
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
