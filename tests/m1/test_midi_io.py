"""
Test Group B: MIDI parse and event integrity tests.

Fixtures:
    test/m1/Cmaj.mid        - generated MIDI reference
    test/m1/rec/in1.mid     - real performance recording

Assertions (both fixtures):
- Parse succeeds.
- All note_on events have MIDI note 0-127 and velocity 1-127.
- All note_off events have MIDI note 0-127.
- Event ordering by cumulative ticks is monotonic.

Additional assertions for test/m1/rec/in1.mid:
- Note-on sequence equals C4 D4 E4 F4 G4 F4 E4 D4 C4.
- Each note-on has a matching note-off for the same channel/note.
- Derived duration_ms for each pair is > 0.
"""

from __future__ import annotations

import pathlib
import tempfile

import pytest

from core.io.midi_io import load_midi, save_midi, pair_notes, MidiData
from core.models import MidiEvent
from tests.m1.helpers import fixture_path, note_on_sequence, midi_note_name

CMAJ_MID = fixture_path("Cmaj.mid")
IN1_MID = fixture_path("rec", "in1.mid")

# Expected note-on pitch names for the recorded fixture (MIDI note numbers)
# C4=60, D4=62, E4=64, F4=65, G4=67, F4=65, E4=64, D4=62, C4=60
EXPECTED_NOTE_NAMES = ["C4", "D4", "E4", "F4", "G4", "F4", "E4", "D4", "C4"]
EXPECTED_NOTES = [60, 62, 64, 65, 67, 65, 64, 62, 60]


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def assert_note_on_range(events: list[MidiEvent]) -> None:
    for e in events:
        if e.type == "note_on":
            assert e.note is not None
            assert 0 <= e.note <= 127, f"note_on note out of range: {e.note}"
            assert e.velocity is not None
            assert 1 <= e.velocity <= 127, f"note_on velocity must be 1-127, got {e.velocity}"


def assert_note_off_range(events: list[MidiEvent]) -> None:
    for e in events:
        if e.type == "note_off":
            assert e.note is not None
            assert 0 <= e.note <= 127, f"note_off note out of range: {e.note}"


def assert_monotonic_ticks(events: list[MidiEvent]) -> None:
    ticks = [e.timestamp_ticks for e in events]
    for i in range(1, len(ticks)):
        assert ticks[i] >= ticks[i - 1], (
            f"Tick ordering not monotonic at index {i}: "
            f"{ticks[i-1]} → {ticks[i]}"
        )


# ---------------------------------------------------------------------------
# Tests for Cmaj.mid
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def cmaj_data() -> MidiData:
    return load_midi(CMAJ_MID)


@pytest.fixture(scope="module")
def cmaj_events(cmaj_data) -> list[MidiEvent]:
    return cmaj_data.events


def test_cmaj_parse_succeeds(cmaj_data):
    assert isinstance(cmaj_data, MidiData)


def test_cmaj_has_events(cmaj_events):
    assert len(cmaj_events) > 0


def test_cmaj_note_on_range(cmaj_events):
    assert_note_on_range(cmaj_events)


def test_cmaj_note_off_range(cmaj_events):
    assert_note_off_range(cmaj_events)


def test_cmaj_monotonic_ticks(cmaj_events):
    assert_monotonic_ticks(cmaj_events)


# ---------------------------------------------------------------------------
# Tests for rec/in1.mid
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def in1_data() -> MidiData:
    return load_midi(IN1_MID)


@pytest.fixture(scope="module")
def in1_events(in1_data) -> list[MidiEvent]:
    return in1_data.events


def test_in1_parse_succeeds(in1_data):
    assert isinstance(in1_data, MidiData)


def test_in1_has_events(in1_events):
    assert len(in1_events) > 0


def test_in1_note_on_range(in1_events):
    assert_note_on_range(in1_events)


def test_in1_note_off_range(in1_events):
    assert_note_off_range(in1_events)


def test_in1_monotonic_ticks(in1_events):
    assert_monotonic_ticks(in1_events)


def test_in1_note_on_sequence(in1_events):
    """Note-on sequence must be C4 D4 E4 F4 G4 F4 E4 D4 C4."""
    seq = note_on_sequence(in1_events)
    actual_notes = [s.note for s in seq]
    assert actual_notes == EXPECTED_NOTES, (
        f"Note-on sequence mismatch.\n"
        f"  Expected: {[midi_note_name(n) for n in EXPECTED_NOTES]}\n"
        f"  Actual:   {[midi_note_name(n) for n in actual_notes]}"
    )


def test_in1_each_note_on_has_matching_note_off(in1_events):
    """Every note_on must have a subsequent note_off for the same channel/note."""
    pairs = pair_notes(in1_events)
    on_events = [e for e in in1_events if e.type == "note_on"]
    assert len(pairs) == len(on_events), (
        f"Paired {len(pairs)} notes but found {len(on_events)} note_on events; "
        "some note_on events are missing a note_off."
    )


def test_in1_positive_duration_ms(in1_events):
    """Derived duration_ms for every note pair must be > 0."""
    pairs = pair_notes(in1_events)
    assert len(pairs) > 0, "No note pairs found"
    for on_event, off_event in pairs:
        duration = off_event.timestamp_ms - on_event.timestamp_ms
        assert duration > 0, (
            f"Non-positive duration for note {on_event.note}: "
            f"on={on_event.timestamp_ms:.2f}ms off={off_event.timestamp_ms:.2f}ms"
        )


# ---------------------------------------------------------------------------
# MIDI round-trip (save + reload)
# ---------------------------------------------------------------------------

def test_midi_save_reload_preserves_note_events(cmaj_data):
    """Events written to a temp file and reloaded match the originals (note types only)."""
    with tempfile.NamedTemporaryFile(suffix=".mid", delete=False) as tmp:
        tmp_path = pathlib.Path(tmp.name)

    save_midi(cmaj_data.events, tmp_path, ticks_per_beat=cmaj_data.ticks_per_beat)
    reloaded = load_midi(tmp_path)
    tmp_path.unlink(missing_ok=True)

    orig_note_events = [(e.type, e.note, e.velocity) for e in cmaj_data.events if e.type in ("note_on", "note_off")]
    rt_note_events = [(e.type, e.note, e.velocity) for e in reloaded.events if e.type in ("note_on", "note_off")]
    assert orig_note_events == rt_note_events
