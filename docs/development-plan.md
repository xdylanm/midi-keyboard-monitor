# Product Requirements Document — Core Music Trainer

> **Status**: Active — supersedes the previous "Dynamics Tracking" development plan (May 2026).
> The original dynamics-tracking spec ([docs/dynamics-tracking.md](docs/dynamics-tracking.md)) is retained as a historical implementation reference but is no longer the source of truth for product direction.

---

## 1. Product Overview

**Core Music Trainer** is a cross-platform desktop application for piano practice. It connects to a MIDI keyboard (via Bluetooth Low Energy dongle or USB MIDI), transcribes performances to standard notation, displays and lightly edits sheet music, and evaluates note accuracy, rhythm, and dynamics against a reference score.

A first-class agent interface — exposing well-documented data models and commands over both REST and MCP-compatible tool endpoints — allows an AI agent to act as a virtual instructor: adjusting exercises, tuning scoring tolerances, and providing feedback programmatically.

### 1.1 Product Goals

1. **Transcribe** performed MIDI into a standard score artifact, with best-effort quantization, hand separation, and optional metronome-driven tempo grid.
2. **Display and lightly edit** sheet music loaded from standard formats.
3. **Evaluate and visualize** playing accuracy across three axes: note pitch, rhythm timing, and dynamics (velocity/expression).
4. **Expose a clean data and command interface** for agents and external tooling — simple, well-documented, and format-agnostic.

### 1.2 Non-Goals (v1)

- Hardware or firmware modifications — the existing BLE dongle and firmware are unchanged.
- Full notation engraving parity (e.g. complex articulations, advanced layout engines).
- Intent-aware expressive alignment (rubato detection, phrase-shape analysis) — deferred to a later phase.
- Native Android or iOS applications — Android is an optional web-client target later.
- Cloud sync, multi-user accounts, or collaboration features.

---

## 2. Users and Context

**Primary user**: An adult intermediate-level pianist practicing on an Ubuntu or Windows desktop, connected to a MIDI keyboard via the project's BLE dongle or a standard USB MIDI cable.

**Secondary persona (agent instructor)**: An AI agent (e.g. a Claude-driven MCP client) that uses the agent interface to query performance data, adjust scoring parameters (tolerance windows, difficulty presets), and suggest exercises.

**Target platforms (v1)**:
- Ubuntu desktop (primary development environment)
- Windows 11 desktop/laptop

**Future platform (deferred)**:
- Android — via web browser client connecting to the same Python core service; no native app required in v1.

---

## 3. MIDI Input Abstraction

All MIDI events enter the system through a single abstract `MidiSource` interface regardless of physical transport. Two adapters are required in v1:

1. **BLE adapter** — connects to the existing BLE MIDI dongle using the existing firmware protocol (see [docs/firmware-spec.md](docs/firmware-spec.md)). Existing BLE-MIDI packet parsing logic from the Flutter prototype is a useful reference.
2. **USB MIDI adapter** — connects to any class-compliant USB MIDI device via `python-rtmidi`.

The normalized event emitted by both adapters is a `MidiEvent`:

```json
{
  "type": "note_on | note_off | control_change | ...",
  "channel": 0,
  "note": 60,
  "velocity": 95,
  "timestamp_ms": 1234567890
}
```

Downstream modules (transcription, scoring, UI) are coupled only to `MidiEvent`; they never reference transport-specific details.

---

## 4. Functional Requirements

### 4.1 Transcription (MIDI → Score)

| ID | Requirement |
|----|-------------|
| T-1 | Capture a real-time performance as a timestamped stream of `MidiEvent` records. |
| T-2 | Quantize note onsets and durations to the nearest grid position given a tempo (BPM), with configurable grid resolution (default: 16th note). |
| T-3 | Separate notes into left-hand (LH) and right-hand (RH) voices using a configurable pitch-split point (default: MIDI 60 / C4). |
| T-4 | Generate a MusicXML score artifact from the quantized, hand-split note sequence. |
| T-5 | Optionally drive quantization from a metronome click so the user's tempo is locked to a known grid rather than estimated. |
| T-6 | Assume "fairly basic pieces" in v1: 4/4 time, quarter/eighth note values, one or two hands, no complex polyrhythm. |

### 4.2 Sheet Music Display and Light Editing

| ID | Requirement |
|----|-------------|
| S-1 | Load a MusicXML (`.musicxml` or `.mxl`) score and render it in the visualization frame. |
| S-2 | Render standard notation: treble and bass clef, key signature, time signature, notes, rests, basic dynamics markings. |
| S-3 | Support light editing operations: change a note's pitch, duration, or dynamic marking; insert or delete a note; add or remove a rest; split or merge measures. |
| S-4 | Persist edits back to the original MusicXML file or a new file. |
| S-5 | Export the score as a MIDI file for playback or further processing. |

### 4.3 Performance Accuracy Analytics

Three scoring dimensions are tracked per note:

**Note accuracy** — was the correct pitch played?
**Rhythm accuracy** — was the note played at the correct time?
**Dynamics accuracy** — was the velocity within the target intensity range?

| ID | Requirement |
|----|-------------|
| A-1 | Align a recorded performance to a reference score using timestamp matching against the tempo grid. |
| A-2 | Compute per-note pitch accuracy: MIDI note match (binary) |
| A-3 | Compute per-note rhythm accuracy: onset time offset from expected beat position in milliseconds. |
| A-4 | Compute per-note dynamics accuracy: mapped velocity (0.0–1.0) vs. target intensity band (derived from score dynamics markings). |
| A-5 | Aggregate accuracy scores per dimension (note, rhythm, dynamics) over a session or selected range. |
| A-6 | Store per-note accuracy results in the JSON sidecar alongside the performance MIDI file. |
| A-7 | Display accuracy results as overlays on the score (color-coded per note) and as summary metrics in the visualization frame. |

#### 4.3.1 Timing Model

**Strict mode (default)**:
The expected beat onset for each note is computed from the score tempo and meter. A note is scored as within tolerance if:

```
|onset_actual_ms - onset_expected_ms| ≤ window_ms
```

`window_ms` is configurable (default: 80 ms, approximately a 16th note at 120 BPM).

**Expressive (hybrid) mode** (configurable):
Adds wider and optionally asymmetric tolerance windows:

```
-window_early_ms ≤ (onset_actual_ms - onset_expected_ms) ≤ window_late_ms
```

`window_early_ms` and `window_late_ms` are independently configurable, so an agent can model anticipatory playing or late-release tendencies. The agent interface exposes both parameters directly.

Intent-aware alignment (tempo-curve estimation, DTW-based rubato detection) is explicitly deferred to a later release.

### 4.4 Agent Interface

The agent interface provides programmatic access to the same core functionality available in the UI. All operations go through a single **internal service contract**; two protocol adapters expose it externally.

#### 4.4.1 Internal Service Contract

The service contract defines typed operations on three resource domains:

**Score resources**
- `GetScore(id)` → MusicXML content + parsed note list
- `ListScores()` → inventory of available scores
- `UpdateNote(score_id, note_id, patch)` → light edit operation
- `ExportMidi(score_id)` → MIDI bytes

**Performance resources**
- `StartCapture(config)` → begin recording MIDI input
- `StopCapture()` → finalize recording, return performance id
- `GetPerformance(id)` → timestamped MidiEvent list + metadata
- `ListPerformances()` → inventory
- `Transcribe(performance_id, config)` → quantize and export to MusicXML

**Analytics resources**
- `AnalyzePerformance(performance_id, score_id, config)` → accuracy report
- `GetAnalysis(analysis_id)` → full per-note accuracy data
- `SetScoringConfig(config)` → update timing windows, intensity mapping, expressive mode toggle

#### 4.4.2 REST API Adapter

- HTTP/JSON, served locally (default `localhost:7432`)
- Endpoints map 1:1 to service contract operations
- OpenAPI schema published at `/openapi.json`
- Used by the browser UI and any HTTP-capable client

#### 4.4.3 MCP-Compatible Tool Adapter

- Exposed as a local MCP server (stdio transport for agent processes; SSE/HTTP transport optional)
- MCP tools map 1:1 to service contract operations
- Tool schemas and descriptions documented in `docs/mcp-tools.md`
- Enables direct integration with agent frameworks (Claude Desktop, custom MCP clients)

---

## 5. Data Formats and Storage

### 5.1 Required Formats (v1)

| Format | Use |
|--------|-----|
| MIDI (`.mid` / Standard MIDI Files) | Performance recording output; score playback export |
| MusicXML (`.musicxml` / `.mxl`) | Canonical score format for import, export, and editing |
| JSON sidecar (`.analysis.json`) | Per-session accuracy results, alignment metadata, scoring configuration |

### 5.2 JSON Sidecar Schema (minimum v1 fields)

```json
{
  "schema_version": "1.0",
  "performance_id": "uuid",
  "score_ref": "path/to/score.musicxml",
  "recorded_at": "ISO8601",
  "tempo_bpm": 120,
  "scoring_config": {
    "mode": "strict | expressive",
    "window_ms": 80,
    "window_early_ms": 80,
    "window_late_ms": 120,
    "intensity_mapping": "linear | square_root | logarithmic",
    "calibration": { "min": 0.0, "max": 1.0 }
  },
  "notes": [
    {
      "note_id": "m1b1n0",
      "expected_pitch": 60,
      "performed_pitch": 60,
      "expected_onset_ms": 500,
      "performed_onset_ms": 512,
      "expected_duration_ms": 500,
      "performed_duration_ms": 490,
      "expected_intensity": 0.57,
      "performed_velocity": 82,
      "performed_intensity": 0.56,
      "pitch_correct": true,
      "rhythm_error_ms": 12,
      "rhythm_in_window": true,
      "dynamics_in_range": true
    }
  ],
  "summary": {
    "note_accuracy": 0.95,
    "rhythm_accuracy": 0.88,
    "dynamics_accuracy": 0.91
  }
}
```

### 5.3 Persistence

- Scores: stored as MusicXML files in a configurable scores directory.
- Performances: stored as MIDI files + JSON sidecars in a configurable performances directory.
- Application configuration (MIDI source, scoring defaults, UI preferences): single JSON config file.
- v1 uses file-based storage only. SQLite for history queries and richer agent workflows is a v1.1 enhancement.

---

## 6. Architecture and Technology Decisions

### 6.1 Selected Architecture

```
┌──────────────────────────────────────────────────────────┐
│                  Browser UI (React)                       │
│   Visualization Frame     │     Score Frame               │
│   (analytics overlays,    │     (OSMD notation render,    │
│    metrics dashboard)     │      light editing toolbar)   │
└───────────────┬──────────────────────────┬───────────────┘
                │ HTTP / WebSocket          │
┌───────────────▼──────────────────────────▼───────────────┐
│                Python Core Service (FastAPI)               │
│                                                            │
│  MIDI Adapter Layer       Score Service                    │
│  ├─ BleAdapter            ├─ MusicXML parser / writer      │
│  └─ UsbMidiAdapter        └─ Score model (music21)         │
│                                                            │
│  Transcription Engine     Analytics Engine                 │
│  ├─ Quantizer             ├─ Alignment                     │
│  ├─ HandSplitter          ├─ Pitch / rhythm / dynamics     │
│  └─ MusicXML exporter     └─ Sidecar writer                │
│                                                            │
│  API Adapter Layer                                         │
│  ├─ REST adapter (OpenAPI)                                 │
│  └─ MCP-compatible tool adapter                            │
└──────────────────────────────────────────────────────────┘
```

### 6.2 Core Runtime

**v1: Python 3.11+**

Selected for its comprehensive music-analysis ecosystem:
- `music21` — score model, MusicXML I/O, music theory analysis
- `mido` / `python-rtmidi` — MIDI file I/O and real-time device access
- `librosa` — beat tracking, onset detection, quantization support
- `FastAPI` — REST API and WebSocket server
- `mir_eval` — note-level accuracy evaluation metrics

**Migration path to Rust core**: The internal service contract (Section 4.4.1) defines typed boundaries between all modules. These boundaries are designed to allow substituting a Rust implementation of any module — particularly the MIDI adapter layer and analytics engine — without changing the REST/MCP interfaces or the React frontend.

### 6.3 UI Layer

The UI decision sequence and rationale:

**Step 1 — Browser-first (initial MVP delivery)**
- Python core runs locally (FastAPI, default `localhost:7432`)
- React frontend served from the same process or a dev server
- User opens the app in browser; no desktop packaging complexity
- Works identically on Ubuntu and Windows from day one
- Android: same URL in mobile browser as a future low-effort path

**Step 2 — Tauri desktop packaging (once workflows stabilize)**
- Wraps the React frontend in a native desktop shell
- Uses OS webview (WebView2 on Windows, WebKitGTK on Linux): small binary, low memory overhead
- Python core runs as a sidecar process managed by Tauri
- Ubuntu + Windows desktop apps from a single codebase

**Step 3 — Electron (fallback, if needed)**
- Bundles Chromium: larger and higher memory, but rendering is fully predictable across OS versions
- Drop-in replacement for Tauri if WebView2/WebKitGTK compatibility issues arise
- Same React frontend, same Python core, same API contract

Native desktop GUI stacks (Qt/PySide, wxPython, Tkinter) are not selected for v1. They offer weaker interactive score editing options and do not provide a natural path to Android browser support later.

**Notation rendering**: OpenSheetMusicDisplay (OSMD, TypeScript/npm) renders MusicXML to SVG in the browser. It wraps VexFlow and supports the MusicXML features required for basic piano scores. Light editing gestures are handled via OSMD's API plus custom React state.

### 6.4 MuseScore Compatibility and UI Reference

MuseScore is a key compatibility target for v1 and beyond.

- **Compatibility target**: The product must maintain strong MusicXML and MIDI interoperability with MuseScore so users can open, edit, and validate scores in either tool.
- **Reference UI direction**: The base score interaction model should follow MuseScore conventions for viewing, direct editing, and playback workflows where practical, to reduce user learning friction.
- **Analytics overlay model**: The product adds a distinct analytics layer on top of a familiar notation-editing experience (for example, note-level pitch/rhythm/dynamics feedback overlays and summary panels).
- **Validation workflow**: MuseScore remains the default external validator for round-trip MusicXML and MIDI behavior during development milestones.

Architectural boundary (required):

- The application core is an independent, reusable engine and is not implemented as a MuseScore plugin or extension.
- UI concerns (rendering and interaction) are separated from engine concerns (MIDI capture, transcription, alignment, scoring, persistence).
- User and agent interactions both target the same internal service contract; neither is allowed to depend on MuseScore internals.

### 6.5 Technology Summary

| Layer | v1 Choice | Future Option |
|-------|-----------|---------------|
| Core language | Python 3.11 | Rust (drop-in via API contract) |
| MIDI real-time | python-rtmidi | rtmidi C++ direct / Rust crate |
| Score model | music21 | music21 → custom Rust model |
| Quantization | librosa + music21 | custom DSP in Rust |
| REST API | FastAPI + uvicorn | Axum (Rust) |
| MCP adapter | Python MCP SDK | Rust MCP SDK |
| UI framework | React (TypeScript) | unchanged |
| Score rendering | OSMD (VexFlow) | Verovio (if MEI added later) |
| Desktop packaging | Browser → Tauri | Electron fallback |
| Storage | JSON files | SQLite (v1.1+) |

---

## 7. Delivery Milestones

Each milestone has explicit acceptance criteria. Milestones are ordered to produce a working feedback loop early.

### M1 — Core Data Models and Format I/O

**Goal**: Establish the canonical data layer all other modules depend on.

Tasks:
- Define and validate JSON schemas for `MidiEvent`, `Score`, `Performance`, `AnalysisResult`, `AppConfig`.
- Implement MusicXML round-trip (load → parse → edit → write) using music21.
- Implement MIDI file read/write (performed note list → .mid) using mido.
- Implement JSON sidecar schema (Section 5.2) with serialization and validation.

Acceptance:
- A MusicXML file loaded and re-exported is notation-equivalent (same notes, durations, dynamics).
- A MIDI file written from a note list is playable and contains expected events.
- JSON sidecar validates against schema; missing/extra fields produce clear errors.

#### M1 Acceptance Test Fixtures

Use the following small fixtures to validate the M1 I/O pipeline before any UI work begins:

| Fixture | Input | Expected output | External validation |
|---------|-------|-----------------|----------------------|
| MusicXML round-trip | 2-staff piano excerpt, 12 measures, 4/4, C major, quarter/half notes, a few rests, and at least one dynamic marking (`p`/`mf`/`f`) | Parsed score preserves note/rest count, clefs, measure count, pitch, duration, and dynamics; re-exported MusicXML is notation-equivalent | Open original and exported files in a score editor and confirm the same notation appears |
| MIDI capture import | Short USB MIDI keyboard performance: C4-D4-E4-F4-G4 then back to C4, played as eigth notes or quarter notes with distinct velocities (for example 48, 56, 64, 72, 80) | Loader emits the same note-on/note-off pairs, note numbers, velocities, and timestamps in order; sidecar can summarize the performance without errors | Record with `arecordmidi` or the app's capture path, then inspect the result with a MIDI player |
| MIDI export/playback | Programmatically generated 1-bar MIDI file using a piano program change and a simple ascending scale | Exported file contains the expected note list and velocity values; playback uses a piano-like soft synth without manual remapping | Play back with `aplaymidi` against a soft synth or load into a notation app and verify audible output |

Recommended external tools for validation:

- **MusicXML editing/inspection**: **MuseScore Studio** is the best free/open-source round-trip validator for editing and re-saving MusicXML. If a browser-based view is sufficient, use an OSMD- or Verovio-based local viewer to confirm rendering. If you need true browser-based editing, a hosted editor such as Flat.io is the closest practical option, but it is not open source.
- **MIDI recording on Ubuntu**: `arecordmidi` is a simple ALSA utility for capturing a short performance from your USB MIDI keyboard into a `.mid` file.
- **MIDI playback on Ubuntu**: `aplaymidi` plus a software synth such as `fluidsynth` or `qsynth` and a General MIDI soundfont gives a straightforward piano playback path; `timidity` is a simple alternative for quick command-line playback.
- **MIDI generation without hardware**: `vmpk` (Virtual MIDI Piano Keyboard) is a lightweight free/open-source tool for generating MIDI notes from the computer keyboard or mouse.

### M2 — MIDI Ingestion Abstraction

**Goal**: A single event stream regardless of MIDI source.

Tasks:
- Implement `MidiSource` abstract interface.
- Implement `UsbMidiAdapter` using python-rtmidi; enumerate connected USB MIDI devices.
- Implement `BleAdapter` connecting to the existing BLE dongle using the BLE-MIDI protocol (reference: existing Flutter `ble_service.dart` parser).
- Emit normalized `MidiEvent` records from both adapters; verify identical downstream behavior.

Acceptance:
- Playing the same notes on the same keyboard via USB and BLE produces `MidiEvent` streams that are note-for-note equivalent (within expected timestamp tolerance).
- Disconnecting or failing to connect a source produces a clear error without crashing the service.

### M3 — Score Display and Light Editing

**Goal**: A working visualization frame for score viewing and editing.

Tasks:
- Scaffold React app with two-panel layout (score frame + visualization frame).
- Integrate OSMD for MusicXML rendering; display treble + bass clef, key/time signatures, notes, dynamics.
- Implement light editing toolbar: change pitch, change duration, change dynamic marking, insert note, delete note, insert/delete rest.
- Wire editing actions to REST API `UpdateNote` and `ExportMidi` endpoints.
- Save-as and export controls.

Acceptance:
- A MusicXML file loads and renders correctly for a simple 8-measure piano piece (both clefs).
- Each light editing operation is reflected in the rendered score and persisted to the file.
- Export produces a MIDI file playable in an external player.

### M4 — Transcription Pipeline

**Goal**: Record a live performance and produce a MusicXML score.

Tasks:
- Implement `StartCapture` / `StopCapture` service operations.
- Implement quantizer: snap note onsets and durations to grid given BPM and grid resolution.
- Implement hand splitter: assign notes to LH/RH by configurable pitch threshold.
- Implement MusicXML export from quantized note list.
- Implement optional metronome for grid-locked recording (visual + audio click in UI).

Acceptance:
- Playing a simple C major scale at a steady tempo produces a correctly quantized MusicXML output with notes on the correct beats.
- Hand splitting correctly assigns notes below/above the threshold to LH/RH staves.
- Metronome-driven recording produces tighter quantization than free-tempo recording.

### M5 — Performance Accuracy Analytics

**Goal**: Score a recorded performance against a reference and display results.

Tasks:
- Implement `AnalyzePerformance`: align performed notes to reference score by beat position.
- Compute per-note pitch accuracy (binary match in v1).
- Compute per-note rhythm accuracy (onset offset in ms; strict and expressive modes).
- Compute per-note dynamics accuracy (mapped velocity vs. intensity band from score dynamics markings).
- Write JSON sidecar with per-note results and summary metrics.
- Render accuracy overlays on score (color-coded notes) and summary metrics in visualization frame.
- Expose `SetScoringConfig` to allow agent to adjust timing windows (strict / expressive with early/late asymmetry).

Acceptance:
- A perfect performance (using simulated MIDI input) scores 1.0 on all three dimensions.
- A performance with deliberate timing errors reports per-note rhythm errors within ±5 ms of actual offset.
- Changing `window_ms` via agent interface immediately affects subsequent analyses without restart.
- Summary metrics match manual calculation against JSON sidecar note list.

### M6 — Agent Interfaces (REST + MCP)

**Goal**: Full dual-protocol agent interface over the shared service contract.

Tasks:
- Complete REST API with OpenAPI schema; all service contract operations covered.
- Implement MCP-compatible tool adapter (stdio transport); tool schemas documented in `docs/mcp-tools.md`.
- End-to-end test: drive a complete workflow (load score → start capture → stop capture → transcribe → analyze → adjust scoring config) via MCP tools.
- End-to-end test: same workflow via REST.

Acceptance:
- All service contract operations are reachable via both REST and MCP tools.
- REST and MCP end-to-end tests produce identical analysis results for the same input.
- `docs/mcp-tools.md` is complete and accurate enough for a new agent client to integrate without reading source code.

### M7 — Desktop Packaging (Tauri)

**Goal**: Single-click desktop applications for Ubuntu and Windows.

Tasks:
- Package React frontend and Python core as a Tauri application.
- Python core runs as a managed sidecar process; Tauri handles lifecycle.
- Test on Ubuntu and Windows 11.
- Installer/update path defined.

Acceptance:
- App launches from desktop shortcut without requiring a pre-installed Python environment.
- All M1–M6 functionality works identically packaged vs. browser-first mode.
- App starts in under 5 seconds on reference hardware.

### M8 — Rust Migration Readiness

**Goal**: Verify the service contract and API layer are stable enough to support a future Rust core replacement.

Tasks:
- Write API contract tests covering all service operations; tests are transport-agnostic (can run against Python or future Rust implementation).
- Document per-module performance baselines (latency, throughput) for MIDI ingestion and analytics.
- Identify any Python-specific implementation details leaking through the API contract and fix them.

Acceptance:
- Contract test suite passes 100% against Python core.
- No Python-specific types or behaviors required by any client (UI or agent).

---

## 8. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| BLE adapter latency on desktop (Linux BlueZ / Windows BT stack) | Medium | High | Measure early in M2; USB MIDI adapter is primary path for latency-sensitive use |
| OSMD editing API insufficient for all required light editing operations | Medium | Medium | Prototype all editing operations in M3 before committing; fallback: custom SVG manipulation or alphaTab |
| music21 performance for large scores | Low | Low | Acceptable for practice-sized pieces; profile in M1 if scores exceed 100 measures |
| MCP protocol evolution (pre-1.0 changes) | Low | Medium | Pin SDK version; abstract MCP adapter so transport can be replaced |
| Python startup latency in packaged app (M7) | Medium | Medium | Use PyInstaller one-file bundle; explore uv for fast venv; measure against 5 s target |
| Tauri/WebKitGTK rendering differences on Linux | Low | Medium | Test early on Ubuntu target; Electron is explicit fallback |

---

## 9. Deferred Roadmap

The following items are explicitly out of scope for v1 and should be revisited in future phases:

| Item | Notes |
|------|-------|
| Intent-aware expressive alignment | Rubato detection, DTW-based alignment, phrase-shape analysis |
| MEI format support | Richer scholarly encoding; add when OSMD/Verovio migration is considered |
| SQLite performance history | Enables richer agent queries across sessions; v1.1 target |
| Android native app | Low priority; web browser client is the path |
| Audio transcription (AMT) | Using basic-pitch or similar to transcribe from audio rather than MIDI |
| Cloud sync and multi-user | Deferred indefinitely; local-first is the design goal |
| Cents-level pitch accuracy | v1 uses binary pitch match; cents deviation requires pitch-bend tracking |
| Playback of recorded sessions | Re-play via MIDI output or internal synthesizer |
| Collaborative practice | Real-time multi-user sessions |

**Milestones**

- **1. Data Model & Persistence**:
  - Tasks: Define JSON schemas for `PracticePlan` and `GlobalConfig`; implement save/load to app documents directory; add import/export UI hooks.
  - Acceptance: Plans and config persist across app restarts; Save creates JSON files in the documents directory; Import/Export opens share sheet.
  - Notes: Start in [app/lib/models.dart](app/lib/models.dart) and add persistence helpers under [app/lib/].

  - Testing with simulated notes: implement a simple simulated MIDI provider (e.g. `app/lib/testing/simulated_midi.dart`) that can emit deterministic note-on events and velocities so persistence behavior can be validated without BLE.

- **2. MIDI Mapping Pipeline & Calibration**:
  - Tasks: Implement mapping functions (linear, square_root, logarithmic); implement global calibration sliders for min/max; wire mapping to BLE input pipeline.
  - Acceptance: Test notes show mapped intensity (0.00–1.00) matching formulas; calibration sliders change mapping; mapping setting persists in global config.
  - Files: Integrate with MIDI input code (e.g., [app/lib/ble_service.dart](app/lib/ble_service.dart)).

  - Testing with simulated notes: the mapping pipeline must accept input from the simulated provider and expose a test harness that can feed velocities and assert mapped intensities.

- **3. Dynamics UI Scaffold**:
  - Tasks: Build the Dynamics Frame with two subviews: Configuration and Visualization. Implement responsive layout (vertical/horizontal), Start and Done controls, and gear button for global config.
  - Acceptance: Configuration screen can name/save a plan and start practice; visualization screen is reachable and returns on Done; layout fits without scrolling.

  - Testing with simulated notes: add a developer option to run the UI with the simulated MIDI provider so the full UI flow can be exercised without hardware.

- **4. Practice Plan Generator**:
  - Tasks: Generate note sequences for major/minor (natural/harmonic/melodic), one/two octaves, and apply hand split rules (default RH at MIDI 60). Support chord modes `mean` and `per-voice`.
  - Acceptance: Generated sequence length matches expected measures (4 measures for 1-octave, 8 for 2-octave); hand-splitting yields LH/RH assignments.

  - Testing with simulated notes: include a deterministic simulated sequence generator that can drive the visualization and scoring logic using the generated plan's expected notes and velocities.

- **5. Real-time Visualization & Scoring**:
  - Tasks: Implement instantaneous bars, mapping visualization, target line and fixed 0.14 band, exponential smoothing (alpha=0.35) for visuals, numeric readouts, in-range/out-of-range text, accuracy bar(s), per-voice scoring.
  - Acceptance: Note-on events are evaluated immediately; bars update visually and numerically; accuracy bar decrements by 1/N on errors; per-voice mode shows separate bars and accuracy.

  - Testing with simulated notes: provide simulation scenarios (perfect play, consistent errors, random noise) that can be replayed to validate scoring, smoothing, and accuracy-bar behavior.

- **6. Metronome**:
  - Tasks: Add visual beat indicator, tempo display and controls, optional click sound with mute/volume and downbeat accent.
  - Acceptance: Visual indicator resynchronizes to tempo changes from the plan; click plays when enabled; controls accessible without scrolling.

  - Testing with simulated notes: when simulation is active allow the metronome to drive simulated note timestamps so timing-related behaviors (visual alignment) can be observed.

- **7. Score Rendering (VexFlow)**:
  - Tasks: Embed a WebView with VexFlow to render the practice score; scale layout to fit four measures across the view and handle two-octave layouts.
  - Acceptance: One- and two-octave plans render correctly and fit within the Score Frame without scrolling.

  - Testing with simulated notes: hook the simulated sequence to the WebView so the rendered score can be validated against the simulated note playback.

- **8. Accessibility & Color**:
  - Tasks: Apply color-blind-friendly palette (Okabe–Ito recommendations), add high-contrast mode, ensure text status + numeric readouts, add screen-reader announcements for note evaluations, and include non-color indicators (patterns/outlines).
  - Acceptance: High-contrast toggle changes UI; in-range/out-of-range is conveyed by text and pattern; accessibility APIs expose note evaluation messages.

  - Testing with simulated notes: use simulated note events to trigger screen-reader announcements and verify text/pattern changes without hardware.

- **9. Tests & Polishing**:
  - Tasks: Add unit tests for mapping, plan generation, and scoring; add an integration smoke test for BLE note flow; update README/docs; propose CI steps.
  - Acceptance: Unit tests for core algorithms pass locally; docs updated with usage and backup/import instructions.

  - Testing with simulated notes: add automated unit/integration tests that use the simulated provider to validate mapping, scoring, plan generation, and a smoke test of the visualization pipeline.

**Implementation notes & priorities**
- Priority order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9. This gives a working loop early (MIDI input → mapping → visualization) before adding score rendering and accessibility polish.
- Keep persistence and global config backward-compatible; store version in config JSON to allow migration.
- For the metronome audio click, start with an OS-level audio API and keep the visual indicator driven from the same scheduler.
- Use a single central data model to drive both visualization and scoring to avoid duplication and timing bugs.

**Acceptance testing suggestions**
- Manual scenarios: connect a BLE keyboard, choose a 1-octave C major plan, select `mp`, start practice, play each note; verify numeric intensity and accuracy bar.
- Unit tests: mapping functions with known velocities; scoring tests with deterministic sequences and expected accuracy outcomes.

---
Generated from: [docs/dynamics-tracking.md](docs/dynamics-tracking.md)
