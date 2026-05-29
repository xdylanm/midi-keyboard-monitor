"""
Helper utilities for M1 test modules.

- Fixture path resolution.
- Event summary helpers for readable assertions.
"""

from __future__ import annotations

import pathlib
from typing import NamedTuple

from core.models import MidiEvent

# Root of the repository (two levels up from tests/m1/)
_REPO_ROOT = pathlib.Path(__file__).parent.parent.parent


def fixture_path(*parts: str) -> pathlib.Path:
    """Return an absolute path to a file under test/m1/."""
    return _REPO_ROOT / "test" / "m1" / pathlib.Path(*parts)


def local_fixture_path(*parts: str) -> pathlib.Path:
    """Return an absolute path to a file under tests/m1/fixtures/."""
    return _REPO_ROOT / "tests" / "m1" / "fixtures" / pathlib.Path(*parts)


class NoteOnSummary(NamedTuple):
    """Compact summary of a note_on event for assertion readability."""
    note: int
    channel: int
    velocity: int


def note_on_sequence(events: list[MidiEvent]) -> list[NoteOnSummary]:
    """Return NoteOnSummary for every note_on event in order."""
    return [
        NoteOnSummary(note=e.note, channel=e.channel, velocity=e.velocity)
        for e in events
        if e.type == "note_on" and e.note is not None
    ]


def midi_note_name(midi_note: int) -> str:
    """Convert a MIDI note number to a name like 'C4'."""
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    octave = (midi_note // 12) - 1
    name = names[midi_note % 12]
    return f"{name}{octave}"
