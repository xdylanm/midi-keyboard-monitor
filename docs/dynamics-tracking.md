# Dynamics Tracking (legacy reference — superseded)

> **Status**: This document was the authoritative spec for the Flutter/Android prototype phase. It is retained as a historical implementation reference for dynamics scoring, velocity mapping, and practice plan concepts.
> The active product requirements are in [docs/development-plan.md](development-plan.md).

## Practice Modes

The user should have a choice of two basic modes for practice: constant or variable dynamics. 
 
### Common Settings

The user should select

- the key for a major or minor scale 
- if minor, choose natural, harmonic or melodic
- one octave or two octave scale
- LH, RH, or HT (see Hand Split rules below)
- tempo (as BPM relative to the quarter note)
- accuracy target range: a number from 10-100 representing a percentage of the fixed band width around the target

Notes on accuracy semantics
- The target bands are fixed-width: each band spans 0.14 centered on the target intensity. The accuracy target percentage scales that band. Example:
  - 10% → ±0.007 (0.14 * 0.10 / 2)
  - 50% → ±0.035
  - 100% → ±0.07
- The numeric target intensities (see Dynamics Frame) are absolute positions in 0..1; the accuracy percentage defines the half-width applied to the 0.14 band around that target.

The RH scale should start as close as possible to C4, and the LH an octave below. Each scale should ascend by one or two octaves, depending on the user config, and then return to the root note and should be scored in 4/4 time using quarter notes. 

### Constant Mode

The user picks a target intensity (pp, p, mp, mf, f, ff) for each octave (just one choice if there's only one octave)

### Variable Mode

The user picks crescendo or decresendo for each octave and a target intensity at the beginning and end of each octave.

Notes on variable-mode targets
- For `variable` mode the target intensity for each note in the octave is computed by linear interpolation between the octave's `startIntensity` and `endIntensity` across the sequence of notes in that octave. Let M be the number of notes in the octave sequence and i be the zero-based index of the current note (0..M-1). The per-note target is:

  target(i) = startIntensity + (endIntensity - startIntensity) * (i / max(1, M-1))

- If M == 1 the target equals `startIntensity`. For two-octave plans compute targets separately per octave. When `chordMode == "per-voice"` compute interpolation using the note order in each voice independently so each voice's target line follows its own linear ramp.

## UI Design

The overall UI should be split into two frames that are simultaneously visible

- if the screen is vertical, show them on top of one another
- if the screen is horizonal, show them side by side

The user should not have to scroll to see anything. The first frame (dynamics) contains the setup and visualization. The second frame will show the sheet music (score).

The UI for the dynamics frame should consist of two views: 

1. configure practice or load a saved practice plan
2. visualize the practice  

When the user presses a "Start" button on the configuration screen, the view switches to the visualization screen.

The UI should also have a global configuration menu (gear button) visible when configuring the practice plan. 

### Dynamics Frame

#### Global Configuration

Accessed through a gear button. 

- Configure the mapping of MIDI velocity to dynamics: choice of "linear", "square_root" and "logarithmic". Default is "linear".
- Mapping is global-only (cannot be overridden per-plan or per-hand).

#### Pracitce Configuration 

This view represents the settings described in the Practice Modes section. The collection of parameters and values is a Practice Plan.

- option to name a plan and save it
- option to load a named plan 
- chord handling option when HT (hands together): "mean" or "per-voice"
  - "mean": average velocity of all simultaneously played notes → single graph
  - "per-voice": compute average velocity per hand and show two graphs (LH / RH)
- default hand-splitting: automatic pitch-based split with a configurable split point; default split so RH starts near C4 (MIDI 60)
- button to Start practice

Storage & Calibration (global)
- Calibration: default is "none". Optional "manual" calibration exposes global sliders for min/max of the intensity range (defaults min=0, max=1). Calibration is stored in the global profile (not in each plan).
- Persistence: Practice Plans and global config are saved as JSON files in the app's internal documents directory. Recommend enabling Android Auto Backup (android:allowBackup="true" + backup rules) and providing Import/Export (share) actions for manual backups.

#### Practice Visualization

This view shows the bar with the velocity of the last note mapped to an intensity.

- Use the global mapping function to scale the MIDI velocity (0-127) to a float on 0..1. For example, for logarithmic mapping add 1 to velocity (1-128), take base-2 logarithm (0..7) and divide by log2(128) to normalize to 0..1.
- show a fixed line across the bar at the location of the target intensity
  - pp = 0.15
  - p = 0.29
  - mp = 0.43
  - mf = 0.57
  - f = 0.71
  - ff = 0.85
- show a semitransparent rectangle across the bar (behind the target line) to indicate the target range. It should be grey when idle, then green or red when playing to indicate if the key press was in range or not. The band half-width is derived from the accuracy percentage applied to the fixed 0.14 span (see Common Settings).
- sampling & smoothing: sample on each note-on event (no interpolation). The displayed bar applies exponential smoothing to reduce flicker with a default smoothing factor alpha = 0.35. The raw mapped value used for scoring is the immediate note-on value; smoothing affects only the visual bar.
- numeric readout: display the current mapped intensity (0.00–1.00) adjacent to each bar.
- chord behavior: when practicing HT and chord_mode="mean", the visualization is a single instantaneous bar showing the mean intensity. When chord_mode="per-voice", show two instantaneous bars (LH/RH) computed from notes assigned to each hand.

- accuracy bar: visualizes cumulative accuracy over the piece as a progress/score bar. Initialize the accuracy bar at 1.0 (100%). Let N be the total number of notes in the active practice sequence; for each note evaluated as "error" (mapped intensity outside the target band) subtract 1/N from the accuracy bar. For HT pieces with `chordMode == "per-voice"`, show a separate accuracy bar for each voice (LH and RH), each initialized to 1.0 and decremented by 1/(notes_in_voice) for errors in that voice. The accuracy bar is updated on each evaluated note-on and provides an at-a-glance summary of remaining accuracy.

Scoring rules (initial version)
- Scoring is velocity-only (no timing penalty).
- Each note-on event that maps to an intensity is evaluated as "in-range" if its mapped intensity lies within target ± (0.14 * accuracy_percent / 100 / 2).
- For per-voice scoring count per-hand notes separately when chord_mode="per-voice".
- Aggregate score = (notes in-range) / (total notes) over the practice session. This same calculation determines whether a note decrements the accuracy bar.
- Accuracy bar behavior: the accuracy bar starts at 1.0 and is decremented by 1/N for each error, where N is the number of notes in the active sequence (or notes in that voice for per-voice accuracy). This provides a running, visual representation of accuracy remaining as the piece is played.
- Future refinements: optionally weight errors by magnitude (distance from target) or add timing-based penalties; these are deferred to later versions.

Edge cases & input handling
- velocity=0 is treated as a note-on with velocity 0 only if the device sends it; otherwise typical note-off handling applies (ignore for intensity).
- sustain pedal and aftertouch are not considered in initial scoring.
- multi-channel input: notes from any MIDI channel are considered; hand-splitting is pitch-based by default.

There should be a button at the bottom labeled "Done" that returns the user to the practice configuration.

### Accessibility & Color

- Use a color-blind-friendly palette for all success/failure and status colors. Recommended palette (Okabe–Ito / colorblind-safe): `#000000` (black / neutral), `#E69F00` (orange), `#56B4E9` (sky blue), `#009E73` (green), `#F0E442` (yellow), `#0072B2` (blue), `#D55E00` (vermillion), `#CC79A7` (purple). Prefer `#0072B2` for success/positive and `#D55E00` for error/negative when a two-color mapping is needed.
- Do not rely on color alone to convey status. Always include a numeric readout of the mapped intensity (0.00–1.00) next to each instantaneous bar and a short textual status ("In range" / "Out of range") that updates on each evaluated note.
- Provide a high-contrast mode toggle in Global Configuration to increase contrast and enlarge UI elements for low-vision users.
- Use icons/patterns or outlines in addition to color for the target band and accuracy bar (e.g., hatch pattern or dotted outline) so color-blind users can distinguish states.
- Ensure all dynamic feedback is exposed to accessibility APIs / screen readers: announce note evaluations (e.g., "C4: in range, 0.57") when enabled.

### Metronome & Latency

- Include a simple metronome control visible in the practice view so the user knows the intended timing. The metronome should be optional and configurable with the following minimal features:
  - Play/Pause toggle.
  - Tempo display (tempo comes from practice plan settings).
  - Visual beat indicator: a small dot or LED that blinks on each beat; accent the downbeat (first beat of the measure) with a larger or differently colored blink.
  - Optional click sound: short audible tick on each beat, with a volume control and mute toggle. Option to accent the downbeat with a harder sound.

- Placement & behavior: place the metronome controls compactly near the top of the Dynamics Frame so it is visible without scrolling. The visual dot should be driven by the same tempo state as the audio click.

- Implementation notes: use a precise scheduling mechanism for the click (audio thread or scheduling API) when audio click is enabled; visual blinking can be driven by the same scheduler or an animation timer. Latency compensation for key input is not required for the first version — the metronome is advisory only.

### Score Frame

This frame shows the music score for the current practice plan. 

- If a one octave plan is active, split the score into four measures. 
- If a two octave plan is active, split the score into eight measures. 
- Pad with rests at the end
- adjust the size of the music score to fit four measures (including clef, timing and key signature, dynamics, etc.) across the panel. For two octaves, continue the last four measures below. 
- The user should not have to scroll to see everything.
- Implementation notes: use VexFlow in a WebView to display the music score. Be careful to adjust the scaling so that the score fits within the frame in both horizonatal and vertical orientations of the phone or tablet. 

## Persistence and formats

- Practice Plans: saved as JSON files under the app documents directory (example path returned by path_provider on each platform).
- Global config (mapping, calibration, app prefs): saved as a single JSON file in the same app documents directory.
- Recommend Android Auto Backup + explicit Import/Export UI for user-driven backup/restore.

