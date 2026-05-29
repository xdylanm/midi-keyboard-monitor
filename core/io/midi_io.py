"""
MIDI file I/O using mido.

Operations:
    load_midi(path)           -> MidiData (events + ticks_per_beat)
    save_midi(events, path)   -> None
    pair_notes(events)        -> list[tuple[MidiEvent, MidiEvent]]
"""

from __future__ import annotations

import pathlib
from typing import NamedTuple, Union

import mido

from core.models import MidiEvent

# Default tempo assumed when no tempo message exists in the file (120 BPM).
_DEFAULT_TEMPO_US = 500_000  # microseconds per beat (120 BPM)


class MidiData(NamedTuple):
    """Return value of load_midi: parsed events plus the file's tick resolution.

    Keeping ``ticks_per_beat`` alongside events avoids information loss when
    the caller needs to write the events back to a file at the same resolution
    (e.g. round-trip through save_midi).

    Because this is a NamedTuple it unpacks like a 2-tuple::

        events, tpb = load_midi(path)
        # or
        data = load_midi(path)
        data.events, data.ticks_per_beat
    """
    events: list[MidiEvent]
    ticks_per_beat: int


def load_midi(path: Union[str, pathlib.Path]) -> MidiData:
    """Parse a MIDI file and return a MidiData with events and tick resolution.

    Absolute timestamps in milliseconds are derived from the file's tempo map.
    Tempo changes in the file are respected.

    Args:
        path: Path to a .mid file.

    Returns:
        MidiData(events, ticks_per_beat). Unpacks as a 2-tuple.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    path = pathlib.Path(path)
    if not path.exists():
        raise FileNotFoundError(f"MIDI file not found: {path}")

    mid = mido.MidiFile(str(path))
    ticks_per_beat = mid.ticks_per_beat

    events: list[MidiEvent] = []

    # Merge all tracks into a single time-ordered sequence using mido's helper.
    current_tempo = _DEFAULT_TEMPO_US
    absolute_ticks = 0
    elapsed_ms = 0.0

    for msg in mido.merge_tracks(mid.tracks):
        # Advance time
        delta_ticks = msg.time
        if delta_ticks > 0:
            tick_duration_ms = (
                current_tempo / ticks_per_beat / 1000.0 * delta_ticks
            )
            elapsed_ms += tick_duration_ms
        absolute_ticks += delta_ticks

        if msg.type == "set_tempo":
            current_tempo = msg.tempo
            continue

        midi_event = _msg_to_event(msg, absolute_ticks, elapsed_ms)
        if midi_event is not None:
            events.append(midi_event)

    return MidiData(events=events, ticks_per_beat=ticks_per_beat)


def _msg_to_event(
    msg: mido.Message, ticks: int, ms: float
) -> MidiEvent | None:
    """Convert a mido message to a MidiEvent, or return None for meta messages."""
    if msg.is_meta:
        return None

    if msg.type == "note_on":
        # MIDI convention: note_on with velocity=0 is equivalent to note_off
        event_type = "note_on" if msg.velocity > 0 else "note_off"
        return MidiEvent(
            type=event_type,
            channel=msg.channel,
            note=msg.note,
            velocity=msg.velocity,
            timestamp_ticks=ticks,
            timestamp_ms=ms,
        )
    elif msg.type == "note_off":
        return MidiEvent(
            type="note_off",
            channel=msg.channel,
            note=msg.note,
            velocity=msg.velocity,
            timestamp_ticks=ticks,
            timestamp_ms=ms,
        )
    elif msg.type == "control_change":
        return MidiEvent(
            type="control_change",
            channel=msg.channel,
            note=None,
            velocity=None,
            timestamp_ticks=ticks,
            timestamp_ms=ms,
        )
    elif msg.type == "program_change":
        return MidiEvent(
            type="program_change",
            channel=msg.channel,
            note=None,
            velocity=None,
            timestamp_ticks=ticks,
            timestamp_ms=ms,
        )
    elif msg.type == "pitchwheel":
        return MidiEvent(
            type="pitch_bend",
            channel=msg.channel,
            note=None,
            velocity=None,
            timestamp_ticks=ticks,
            timestamp_ms=ms,
        )
    else:
        return MidiEvent(
            type="other",
            channel=msg.channel if hasattr(msg, "channel") else 0,
            note=None,
            velocity=None,
            timestamp_ticks=ticks,
            timestamp_ms=ms,
        )


def save_midi(
    events: list[MidiEvent],
    path: Union[str, pathlib.Path],
    ticks_per_beat: int = 480,
    tempo: int = _DEFAULT_TEMPO_US,
) -> None:
    """Write a list of MidiEvent objects to a MIDI file (single-track, type 0).

    Timestamps from ``MidiEvent.timestamp_ticks`` are used directly as
    absolute tick positions. Delta times are computed from the sorted sequence.

    Args:
        events:         List of MidiEvent records. Must carry valid timestamp_ticks.
        path:           Destination .mid file path.
        ticks_per_beat: MIDI ticks per beat (default 480).
        tempo:          Tempo in microseconds per beat (default 500 000 = 120 BPM).
    """
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    mid = mido.MidiFile(type=0, ticks_per_beat=ticks_per_beat)
    track = mido.MidiTrack()
    mid.tracks.append(track)

    track.append(mido.MetaMessage("set_tempo", tempo=tempo, time=0))

    # Sort by tick to ensure correct ordering
    sorted_events = sorted(events, key=lambda e: e.timestamp_ticks)

    prev_ticks = 0
    for event in sorted_events:
        delta = event.timestamp_ticks - prev_ticks
        prev_ticks = event.timestamp_ticks

        if event.type in ("note_on", "note_off"):
            msg = mido.Message(
                event.type,
                channel=event.channel,
                note=event.note or 0,
                velocity=event.velocity or 0,
                time=delta,
            )
            track.append(msg)
        elif event.type == "control_change":
            track.append(
                mido.Message("control_change", channel=event.channel, control=0, value=0, time=delta)
            )
        elif event.type == "program_change":
            track.append(
                mido.Message("program_change", channel=event.channel, program=0, time=delta)
            )

    track.append(mido.MetaMessage("end_of_track", time=0))
    mid.save(str(path))


def pair_notes(events: list[MidiEvent]) -> list[tuple[MidiEvent, MidiEvent]]:
    """Pair note_on events with their subsequent note_off events.

    Matching is per (channel, note). The first note_off after a note_on for
    the same (channel, note) closes the pair.

    Args:
        events: Time-ordered list of MidiEvent records.

    Returns:
        List of (note_on_event, note_off_event) pairs. Unpaired events are
        silently omitted (they can be inspected separately).
    """
    # pending[channel][note] = note_on event
    pending: dict[int, dict[int, MidiEvent]] = {}
    pairs: list[tuple[MidiEvent, MidiEvent]] = []

    for event in events:
        if event.type == "note_on" and event.note is not None:
            pending.setdefault(event.channel, {})[event.note] = event
        elif event.type == "note_off" and event.note is not None:
            ch_map = pending.get(event.channel, {})
            on_event = ch_map.pop(event.note, None)
            if on_event is not None:
                pairs.append((on_event, event))

    return pairs
