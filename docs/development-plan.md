# Development Plan — Dynamics Tracking

This document defines an incremental plan to implement the features described in the practice dynamics spec: [docs/dynamics-tracking.md](docs/dynamics-tracking.md).

**Overview**

- Goal: Deliver a mobile practice feature set that maps BLE MIDI velocity to a visual intensity, supports constant/variable practice plans, scores performance, and provides accessible, persistent UI.
- Approach: Implement in small, testable milestones. Each milestone has clear acceptance criteria so progress is verifiable.

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
