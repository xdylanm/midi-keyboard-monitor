"""
Score DTO adapter: converts between music21.stream.Score and plain-dict DTOs.

Used at API/test boundaries — never as the primary in-memory representation.

Operations:
    score_to_dto(score)  -> dict
    dto_to_score(dto)    -> music21.stream.Score  (basic reconstruction)
"""

from __future__ import annotations

from typing import Optional

import music21.stream
import music21.note
import music21.chord
import music21.dynamics
import music21.meter
import music21.key
import music21.tempo


def score_to_dto(score: music21.stream.Score) -> dict:
    """Flatten a music21 Score into a plain-dict DTO for API/test use.

    The DTO contains just enough information to assert notation equivalence
    across a round-trip (load → save → reload).

    Returns a dict with shape::

        {
            "metadata": {"title": str | None, "composer": str | None},
            "time_signature": str | None,
            "key_signature": str | None,
            "tempo_bpm": float | None,
            "parts": [
                {
                    "part_id": str,
                    "measures": [
                        {
                            "measure_number": int,
                            "events": [
                                {
                                    "kind": "note" | "rest" | "chord",
                                    "pitches": [str],   # e.g. ["C4", "E4"]
                                    "duration_type": str,
                                    "dynamics": str | None,
                                }
                            ],
                        }
                    ],
                }
            ],
        }
    """
    dto: dict = {
        "metadata": _extract_metadata(score),
        "time_signature": _extract_time_signature(score),
        "key_signature": _extract_key_signature(score),
        "tempo_bpm": _extract_tempo(score),
        "parts": [],
    }

    for part in score.parts:
        part_dto = {"part_id": part.id, "measures": []}
        for measure in part.getElementsByClass(music21.stream.Measure):
            measure_dto = {"measure_number": measure.number, "events": []}
            # Track current dynamic for inheritance within the measure
            current_dynamic: Optional[str] = None
            for el in measure.recurse():
                if isinstance(el, music21.dynamics.Dynamic):
                    current_dynamic = el.value
                elif isinstance(el, music21.note.Note):
                    measure_dto["events"].append(
                        {
                            "kind": "note",
                            "pitches": [el.pitch.nameWithOctave],
                            "duration_type": el.duration.type,
                            "dynamics": current_dynamic,
                        }
                    )
                elif isinstance(el, music21.chord.Chord):
                    measure_dto["events"].append(
                        {
                            "kind": "chord",
                            "pitches": [p.nameWithOctave for p in el.pitches],
                            "duration_type": el.duration.type,
                            "dynamics": current_dynamic,
                        }
                    )
                elif isinstance(el, music21.note.Rest):
                    measure_dto["events"].append(
                        {
                            "kind": "rest",
                            "pitches": [],
                            "duration_type": el.duration.type,
                            "dynamics": None,
                        }
                    )
            part_dto["measures"].append(measure_dto)
        dto["parts"].append(part_dto)

    return dto


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_metadata(score: music21.stream.Score) -> dict:
    md = score.metadata
    if md is None:
        return {"title": None, "composer": None}
    return {
        "title": md.title,
        "composer": md.composer,
    }


def _extract_time_signature(score: music21.stream.Score) -> Optional[str]:
    for el in score.recurse():
        if isinstance(el, music21.meter.TimeSignature):
            return el.ratioString
    return None


def _extract_key_signature(score: music21.stream.Score) -> Optional[str]:
    for el in score.recurse():
        if isinstance(el, music21.key.KeySignature):
            if isinstance(el, music21.key.Key):
                return el.tonicPitchNameWithCase
            return f"{el.sharps} sharps"
    return None


def _extract_tempo(score: music21.stream.Score) -> Optional[float]:
    for el in score.recurse():
        if isinstance(el, music21.tempo.MetronomeMark):
            return float(el.number) if el.number is not None else None
    return None
