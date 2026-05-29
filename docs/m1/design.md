# Milestone M1 Design

## Purpose
This document defines the engineering design for Milestone M1 from the PRD: Core Data Models and Format I/O.

M1 objective:
- Define canonical core data models.
- Implement MusicXML load/edit/write round-trip.
- Implement MIDI load/write round-trip.
- Implement JSON sidecar schema and validation.

## Scope
In scope:
- Core Python domain models for M1 entities.
- File I/O for MusicXML, MIDI, and analysis sidecar JSON.
- Schema validation and deterministic serialization behavior.
- Automated tests using fixtures under test/m1.

Out of scope:
- Live MIDI device ingestion (M2).
- React/OSMD UI (M3).
- Quantization/transcription and scoring (M4+).
- Tauri packaging.

## M1 Fixture Inventory
All automated tests must use these fixtures:

| Fixture | Path | Purpose |
|---|---|---|
| MusicXML reference | test/m1/Cmaj.musicxml | MusicXML parse + round-trip equivalence tests |
| Generated MIDI reference | test/m1/Cmaj.mid | MIDI parser and canonical event extraction |
| Recorded MIDI reference | test/m1/rec/in1.mid | Real performance MIDI parser validation |

Recorded fixture behavioral expectation for note-on sequence:
- C4, D4, E4, F4, G4, F4, E4, D4, C4

## Architecture for M1
M1 should deliver a reusable engine-only core package. Suggested package layout:

- core/models.py
- core/adapters/score_dto.py
- core/io/musicxml_io.py
- core/io/midi_io.py
- core/io/sidecar_io.py
- core/schema/*.schema.json
- tests/m1/*

The core package must not depend on UI frameworks.

## Canonical Data Contracts (M1)

### MidiEvent
Required fields:
- type: note_on | note_off | control_change | program_change | pitch_bend | other
- channel: int (0-15)
- note: int (0-127, nullable for non-note events)
- velocity: int (0-127, nullable for non-note events)
- timestamp_ticks: int
- timestamp_ms: float (derived when tempo context exists)

### Canonical Score Representation (music21)
For M1, the canonical in-memory score representation is `music21.stream.Score` (and related music21 objects such as Part, Measure, Note, Rest, Dynamic).

M1 requirement:
- Do not implement a bespoke internal `ScoreModel` class as the primary score store.
- Use adapter DTOs only at integration boundaries (REST/MCP payloads, snapshots, test assertions).

Required score information exposed through adapters:
- metadata: title, composer (optional)
- time_signature
- key_signature
- tempo_bpm
- measures with staff/voice note and rest events
- dynamics markers attached to relevant notes/measures

### AnalysisResult (M1 placeholder)
M1 does not compute scoring, but the schema must exist.
Minimum fields:
- schema_version
- performance_id
- score_ref
- recorded_at
- notes[] (allowed empty in M1)
- summary (allowed null fields in M1)

### AppConfig
Minimum fields:
- schema_version
- default_paths for scores/performances
- logging level
- mapping defaults placeholder

## I/O Design

### MusicXML I/O
Library: music21.

Operations:
- load_musicxml(path) -> music21.stream.Score
- save_musicxml(score: music21.stream.Score, path)
- score_to_dto(score) -> dict (for API/testing boundaries)
- dto_to_score(dto) -> music21.stream.Score (only if needed by boundary workflows)

Round-trip requirement:
- Loaded and re-saved score must be notation-equivalent for note/rest pitch/duration, measure count, clefs, and dynamics.

### MIDI I/O
Library: mido.

Operations:
- load_midi(path) -> list[MidiEvent]
- save_midi(events, path)

Behavior:
- Preserve note on/off ordering.
- Preserve channel, note, and velocity values.
- Preserve time deltas/ticks for event ordering integrity.

### Sidecar JSON I/O
Operations:
- load_sidecar(path) -> AnalysisResult
- save_sidecar(result, path)
- validate_sidecar_json(obj) -> ValidationResult

Behavior:
- Strict schema validation.
- Clear error messages for missing and unexpected properties.

## Validation Rules
- Schema files are versioned and checked into source.
- JSON serialization is deterministic (sorted keys, stable formatting).
- Invalid inputs return structured exceptions with machine- and human-readable details.

## Automated Test Design (Required)

### Test Group A: MusicXML Round-trip
Fixture: test/m1/Cmaj.musicxml

Assertions:
- Parse succeeds without warnings promoted to errors.
- Measure count unchanged after save+reload.
- Note/rest count unchanged after save+reload.
- Dynamics markings preserved after save+reload.
- Key/time signatures preserved.

### Test Group B: MIDI Parse and Event Integrity
Fixtures:
- test/m1/Cmaj.mid
- test/m1/rec/in1.mid

Assertions for both fixtures:
- Parse succeeds.
- All note_on events have MIDI range 0-127 and velocity 1-127.
- All note_off events have MIDI range 0-127.
- Event ordering by cumulative ticks is monotonic.

Additional assertions for test/m1/rec/in1.mid:
- Note-on sequence equals C4 D4 E4 F4 G4 F4 E4 D4 C4.
- Each note-on has a matching subsequent note-off for same channel/note.
- Derived duration_ms for each pair is > 0.

### Test Group C: Sidecar Schema Validation
Provide local valid and invalid sidecar samples in tests/m1/fixtures/.

Assertions:
- Valid sidecar passes schema validation.
- Missing required fields fail with explicit field names.
- Additional unexpected fields fail when additionalProperties is false.

## Acceptance Mapping to PRD M1
PRD acceptance criterion -> M1 implementation evidence:

1) MusicXML notation-equivalent round-trip
- Evidence: automated test group A passing.

2) MIDI playable and expected events preserved
- Evidence: automated test group B passing and output MIDI playable in external tools.

3) Sidecar schema validation clear errors
- Evidence: automated test group C passing and error snapshots validated.

## Engineering Notes
- Keep module APIs pure and deterministic so they are reusable by REST/MCP layers in later milestones.
- Do not embed UI assumptions or MuseScore-specific runtime dependencies in core modules.
- Treat fixture files as immutable test contracts; if updated, update expected assertions in the same change.
