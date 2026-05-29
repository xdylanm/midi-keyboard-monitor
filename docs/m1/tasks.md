# Milestone M1 Tasks Checklist

Use this checklist to track implementation and validation progress for M1.

## 1) Project Structure and Baseline
- [ ] Create core package layout for M1 modules.
- [ ] Add schema directory for JSON schemas.
- [ ] Add test package layout for M1 automated tests.
- [ ] Ensure dependencies for M1 are declared (music21, mido, jsonschema, pytest).

## 2) Data Models
- [ ] Implement MidiEvent model.
- [ ] Adopt music21.stream.Score as canonical in-memory score model.
- [ ] Implement score DTO adapter for boundary payloads (REST/MCP/tests).
- [ ] Implement AnalysisResult model (M1 placeholder shape).
- [ ] Implement AppConfig model.
- [ ] Add serialization and deserialization tests for all models.

## 3) MusicXML I/O
- [ ] Implement load_musicxml(path) -> music21.stream.Score.
- [ ] Implement save_musicxml(score, path) for music21.stream.Score.
- [ ] Implement score_to_dto(score) helper for test and API boundary assertions.
- [ ] Implement canonicalization/comparison helper for notation-equivalence checks.
- [ ] Add fixture test using test/m1/Cmaj.musicxml.
- [ ] Assert measure, note/rest, key/time signature, and dynamics preservation.

## 4) MIDI I/O
- [ ] Implement load_midi(path) -> list[MidiEvent].
- [ ] Implement save_midi(events, path).
- [ ] Implement note-on/off pairing helper (for validation and diagnostics).
- [ ] Add fixture parse test for test/m1/Cmaj.mid.
- [ ] Add fixture parse test for test/m1/rec/in1.mid.
- [ ] Assert note-on sequence for recorded fixture: C4 D4 E4 F4 G4 F4 E4 D4 C4.
- [ ] Assert each note-on in recorded fixture has a matching note-off.
- [ ] Assert positive derived duration_ms for all paired notes.

## 5) Sidecar Schema
- [ ] Author AnalysisResult JSON schema (v1.0) under core/schema/.
- [ ] Add valid sidecar sample fixture.
- [ ] Add invalid sidecar sample fixtures (missing required fields, unknown fields).
- [ ] Implement validate_sidecar_json(obj).
- [ ] Add tests for pass/fail schema outcomes with clear error messages.

## 6) Automated Test Suite
- [ ] Create pytest test module: tests/m1/test_musicxml_roundtrip.py.
- [ ] Create pytest test module: tests/m1/test_midi_io.py.
- [ ] Create pytest test module: tests/m1/test_sidecar_schema.py.
- [ ] Add helper utilities for fixture loading and event summaries.
- [ ] Add command entry in project docs for running only M1 tests.

Recommended test commands:
- pytest tests/m1 -q
- pytest tests/m1/test_midi_io.py -q
- pytest tests/m1/test_musicxml_roundtrip.py -q
- pytest tests/m1/test_sidecar_schema.py -q

## 7) Manual Validation (External Tools)
- [ ] Open original and round-tripped MusicXML in MuseScore and visually confirm notation equivalence.
- [ ] Play generated MIDI and recorded MIDI using a desktop player/synth to confirm audible output.
- [ ] Spot-check recorded fixture timing and velocity summary from parser output.

## 8) PRD Acceptance Sign-off for M1
- [ ] Acceptance #1 complete: MusicXML round-trip notation-equivalent.
- [ ] Acceptance #2 complete: MIDI read/write preserves expected events and is playable.
- [ ] Acceptance #3 complete: sidecar validation enforces schema with clear errors.
- [ ] Record final evidence links in PR/commit notes.

## 9) Notes and Risks
- [ ] Track any fixture anomalies (for example stray note_off events) in test comments.
- [ ] Keep fixture files immutable unless intentionally re-baselining tests.
- [ ] If fixture expectations change, update this checklist and design doc in the same PR.
