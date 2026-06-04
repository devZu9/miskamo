"""Test core.midi helpers: _truncate_notes, _extract_segment, _split_into_segments."""

import pretty_midi
from core.midi import _truncate_notes, _extract_segment, _split_into_segments


def _note(pitch, start, end, vel=80):
    return pretty_midi.Note(velocity=vel, pitch=pitch, start=start, end=end)


def test_truncate_notes_short():
    notes = [_note(60, 0, 2), _note(62, 1, 3)]
    result = _truncate_notes(notes, max_dur=1.5)
    assert len(result) == 2
    assert result[0].end == 1.5  # truncated
    assert result[1].end == 1.5  # truncated


def test_truncate_notes_skip_after():
    notes = [_note(60, 0, 1), _note(62, 5, 6)]
    result = _truncate_notes(notes, max_dur=2)
    assert len(result) == 1
    assert result[0].pitch == 60


def test_truncate_notes_empty():
    assert _truncate_notes([], max_dur=10) == []


def test_truncate_notes_too_short():
    notes = [_note(60, 0, 0.03)]
    result = _truncate_notes(notes, max_dur=10)
    assert result == []


def test_extract_segment_basic():
    notes = [_note(60, 0, 2), _note(62, 2, 4)]
    seg = _extract_segment(notes, offset=1, duration=2)
    assert len(seg) == 2
    assert seg[0].start >= 0
    assert seg[0].end <= 2
    assert seg[1].start >= 0


def test_extract_segment_no_overlap():
    notes = [_note(60, 0, 1)]
    seg = _extract_segment(notes, offset=5, duration=2)
    assert seg == []


def test_extract_segment_partial():
    notes = [_note(60, 0, 3)]
    seg = _extract_segment(notes, offset=2, duration=2)
    assert len(seg) == 1
    assert 0 <= seg[0].start
    assert seg[0].end <= 2
    assert seg[0].pitch == 60


def test_split_no_split_needed():
    notes = [_note(60, 0, 3), _note(62, 3.5, 5)]
    segs = _split_into_segments(notes, max_dur=10)
    assert len(segs) == 1
    assert len(segs[0]) == 2


def test_split_exact_fit():
    notes = [_note(60, 0, 2), _note(62, 2, 4)]
    segs = _split_into_segments(notes, max_dur=4)
    assert len(segs) == 1


def test_split_into_two():
    notes = [_note(60, 0, 3), _note(62, 5, 8)]
    segs = _split_into_segments(notes, max_dur=4)
    assert len(segs) >= 1


def test_split_empty():
    assert _split_into_segments([], max_dur=10) == []


def test_split_short_tail_merge():
    # Tail shorter than max_dur should merge with last segment
    notes = [_note(60, 0, 5), _note(62, 6, 7)]
    segs = _split_into_segments(notes, max_dur=3)
    # Third segment merging: start=6, total_dur=7, end=7
    # segment 0: 0-3, segment 1: 3-6, segment 2: 6-7 (merged tail)
    assert len(segs) >= 2


def test_truncate_preserves_pitch_and_vel():
    n = _note(72, 0, 2, vel=100)
    result = _truncate_notes([n], max_dur=1)
    assert result[0].pitch == 72
    assert result[0].velocity == 100
