"""
Test Group A: MusicXML round-trip tests.

Fixture: test/m1/Cmaj.musicxml

Assertions:
- Parse succeeds without exceptions.
- Measure count unchanged after save + reload.
- Note/rest count unchanged after save + reload.
- Key/time signatures preserved after save + reload.
- Dynamics markings present in original are preserved after round-trip.
"""

from __future__ import annotations

import pathlib
import tempfile

import pytest
import music21.stream
import music21.dynamics
import music21.note
import music21.meter
import music21.key

from core.io.musicxml_io import load_musicxml, save_musicxml
from core.adapters.score_dto import score_to_dto
from tests.m1.helpers import fixture_path


MUSICXML_FIXTURE = fixture_path("Cmaj.musicxml")


@pytest.fixture(scope="module")
def original_score() -> music21.stream.Score:
    """Load the Cmaj.musicxml fixture once for the module."""
    return load_musicxml(MUSICXML_FIXTURE)


@pytest.fixture(scope="module")
def roundtrip_score(original_score: music21.stream.Score) -> music21.stream.Score:
    """Save the original score to a temp file and reload it."""
    with tempfile.NamedTemporaryFile(suffix=".musicxml", delete=False) as tmp:
        tmp_path = pathlib.Path(tmp.name)
    save_musicxml(original_score, tmp_path)
    reloaded = load_musicxml(tmp_path)
    tmp_path.unlink(missing_ok=True)
    return reloaded


# ---------------------------------------------------------------------------
# Parse smoke test
# ---------------------------------------------------------------------------

def test_load_musicxml_succeeds():
    """Fixture parses without raising an exception."""
    score = load_musicxml(MUSICXML_FIXTURE)
    assert isinstance(score, music21.stream.Score)


def test_fixture_has_parts(original_score):
    """Score contains at least one part."""
    assert len(original_score.parts) >= 1


# ---------------------------------------------------------------------------
# Measure count
# ---------------------------------------------------------------------------

def _count_measures(score: music21.stream.Score) -> int:
    total = 0
    for part in score.parts:
        total += len(list(part.getElementsByClass(music21.stream.Measure)))
    return total


def test_measure_count_preserved(original_score, roundtrip_score):
    """Measure count is unchanged after save + reload."""
    orig = _count_measures(original_score)
    rt = _count_measures(roundtrip_score)
    assert orig > 0, "Fixture must have at least one measure"
    assert orig == rt, f"Measure count changed: {orig} → {rt}"


# ---------------------------------------------------------------------------
# Note / rest count
# ---------------------------------------------------------------------------

def _count_notes_and_rests(score: music21.stream.Score) -> tuple[int, int]:
    notes = 0
    rests = 0
    for el in score.recurse():
        if isinstance(el, music21.note.Note):
            notes += 1
        elif isinstance(el, music21.note.Rest):
            rests += 1
    return notes, rests


def test_note_count_preserved(original_score, roundtrip_score):
    """Note count is unchanged after save + reload."""
    orig_notes, _ = _count_notes_and_rests(original_score)
    rt_notes, _ = _count_notes_and_rests(roundtrip_score)
    assert orig_notes > 0, "Fixture must contain notes"
    assert orig_notes == rt_notes, f"Note count changed: {orig_notes} → {rt_notes}"


def test_rest_count_preserved(original_score, roundtrip_score):
    """Rest count is unchanged after save + reload."""
    _, orig_rests = _count_notes_and_rests(original_score)
    _, rt_rests = _count_notes_and_rests(roundtrip_score)
    assert orig_rests == rt_rests, f"Rest count changed: {orig_rests} → {rt_rests}"


# ---------------------------------------------------------------------------
# Key / time signatures
# ---------------------------------------------------------------------------

def _collect_time_sigs(score: music21.stream.Score) -> list[str]:
    return [
        el.ratioString
        for el in score.recurse()
        if isinstance(el, music21.meter.TimeSignature)
    ]


def _collect_key_sigs(score: music21.stream.Score) -> list[int]:
    return [
        el.sharps
        for el in score.recurse()
        if isinstance(el, music21.key.KeySignature)
    ]


def test_time_signatures_preserved(original_score, roundtrip_score):
    """Time signature(s) are preserved after round-trip."""
    orig = _collect_time_sigs(original_score)
    rt = _collect_time_sigs(roundtrip_score)
    assert orig, "Fixture must contain a time signature"
    assert orig == rt, f"Time signatures differ: {orig} vs {rt}"


def test_key_signatures_preserved(original_score, roundtrip_score):
    """Key signature(s) are preserved after round-trip."""
    orig = _collect_key_sigs(original_score)
    rt = _collect_key_sigs(roundtrip_score)
    assert orig == rt, f"Key signatures differ: {orig} vs {rt}"


# ---------------------------------------------------------------------------
# Dynamics
# ---------------------------------------------------------------------------

def _collect_dynamics(score: music21.stream.Score) -> list[str]:
    return [
        el.value
        for el in score.recurse()
        if isinstance(el, music21.dynamics.Dynamic)
    ]


def test_dynamics_preserved(original_score, roundtrip_score):
    """Dynamics markings present in original are preserved after round-trip."""
    orig = _collect_dynamics(original_score)
    rt = _collect_dynamics(roundtrip_score)
    assert orig == rt, f"Dynamics differ: {orig} vs {rt}"


# ---------------------------------------------------------------------------
# DTO adapter smoke test
# ---------------------------------------------------------------------------

def test_score_to_dto_has_required_keys(original_score):
    """score_to_dto produces a dict with all required top-level keys."""
    dto = score_to_dto(original_score)
    for key in ("metadata", "time_signature", "key_signature", "tempo_bpm", "parts"):
        assert key in dto, f"Missing key in DTO: {key}"


def test_score_to_dto_parts_non_empty(original_score):
    """DTO parts list is non-empty."""
    dto = score_to_dto(original_score)
    assert len(dto["parts"]) >= 1
