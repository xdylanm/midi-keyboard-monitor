# Milestone M1 Tasks Checklist

Use this checklist to track implementation and validation progress for M1.

## 1) Project Structure and Baseline
- [x] Create core package layout for M1 modules.
- [x] Add schema directory for JSON schemas.
- [x] Add test package layout for M1 automated tests.
- [x] Ensure dependencies for M1 are declared (music21, mido, jsonschema, pytest).

## 2) Data Models
- [x] Implement MidiEvent model.
- [x] Adopt music21.stream.Score as canonical in-memory score model.
- [x] Implement score DTO adapter for boundary payloads (REST/MCP/tests).
- [x] Implement AnalysisResult model (M1 placeholder shape).
- [x] Implement AppConfig model.
- [x] Add serialization and deserialization tests for all models.

## 3) MusicXML I/O
- [x] Implement load_musicxml(path) -> music21.stream.Score.
- [x] Implement save_musicxml(score, path) for music21.stream.Score.
- [x] Implement score_to_dto(score) helper for test and API boundary assertions.
- [x] Implement canonicalization/comparison helper for notation-equivalence checks.
- [x] Add fixture test using test/m1/Cmaj.musicxml.
- [x] Assert measure, note/rest, key/time signature, and dynamics preservation.

## 4) MIDI I/O
- [x] Implement load_midi(path) -> list[MidiEvent].
- [x] Implement save_midi(events, path).
- [x] Implement note-on/off pairing helper (for validation and diagnostics).
- [x] Add fixture parse test for test/m1/Cmaj.mid.
- [x] Add fixture parse test for test/m1/rec/in1.mid.
- [x] Assert note-on sequence for recorded fixture: C4 D4 E4 F4 G4 F4 E4 D4 C4.
- [x] Assert each note-on in recorded fixture has a matching note-off.
- [x] Assert positive derived duration_ms for all paired notes.

## 5) Sidecar Schema
- [x] Author AnalysisResult JSON schema (v1.0) under core/schema/.
- [x] Add valid sidecar sample fixture.
- [x] Add invalid sidecar sample fixtures (missing required fields, unknown fields).
- [x] Implement validate_sidecar_json(obj).
- [x] Add tests for pass/fail schema outcomes with clear error messages.

## 6) Automated Test Suite
- [x] Create pytest test module: tests/m1/test_musicxml_roundtrip.py.
- [x] Create pytest test module: tests/m1/test_midi_io.py.
- [x] Create pytest test module: tests/m1/test_sidecar_schema.py.
- [x] Add helper utilities for fixture loading and event summaries.
- [x] Add command entry in project docs for running only M1 tests.

Recommended test commands:
- pytest tests/m1 -q
- pytest tests/m1/test_midi_io.py -q
- pytest tests/m1/test_musicxml_roundtrip.py -q
- pytest tests/m1/test_sidecar_schema.py -q

## 7) Manual Validation (External Tools)
- [x] Open original and round-tripped MusicXML in MuseScore and visually confirm notation equivalence.
- [x] Play generated MIDI and recorded MIDI using a desktop player/synth to confirm audible output.
- [x] Spot-check recorded fixture timing and velocity summary from parser output.

## 8) PRD Acceptance Sign-off for M1
- [x] Acceptance #1 complete: MusicXML round-trip notation-equivalent.
- [x] Acceptance #2 complete: MIDI read/write preserves expected events and is playable.
- [x] Acceptance #3 complete: sidecar validation enforces schema with clear errors.
- [x] Record final evidence links in PR/commit notes.

