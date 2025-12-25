# MIDI Keyboard Monitor — Firmware Specification

Version: 0.2

Date: 2025-12-24

## Goal

Build a small, low-latency device based on the Raspberry Pi Pico W that connects to the MIDI output of a keyboard, monitors incoming MIDI messages (at least Note On / Note Off and velocity), and forwards them to a mobile app via BLE, which displays the velocity of key presses in real time to assist dynamic practice.

## Constraints and Assumptions

- Target hardware: Raspberry Pi Pico W
- Firmware language: MicroPython
- Physical MIDI input: standard 5‑pin DIN MIDI (31250 baud, coupled with H11L1 opto‑isolator to RX pin on the Pico W)
- Latency target: end-to-end (key press → UI update) < 20 ms if possible; acceptable up to ~50 ms.
- Network: BLE connectivity; device will support discovery, connection and MIDI message forwarding
- Target mobile platform: Android with development using Flutter (Dart language)

## Hardware Interface

1. MIDI Input (required)
   - Use the keyboard's MIDI OUT (5‑pin DIN) wired to an opto‑isolator (standard MIDI input circuit) and then to a UART RX on the Pico.
   - UART settings: 31250 baud, 8 data bits, 1 stop bit, no parity.
   - Connect the opto isolator (H11L1) output to the Pico UART0 RX on GP17.

2. Power
   - Pico W powered via USB or external 5 V regulator.

3. Status
  - Use the on-board LED indicator for network status and MIDI activity.
  - A dedicated blue status LED is connected to GPIO0. LED patterns:
    - "Searching/Pairing": slow blink (e.g. 200ms on / 800ms off).
    - "Connected": steady on (or gentle pulse in future revisions).

4. User Button (added)
  - A push-button is connected to GPIO15 and configured with an internal pull-up; the switch is active-low.
  - Behavior:
    - Short press (release within 5s): when BLE is connected this generates a simulated Note On followed by Note Off (useful for verification without a physical keyboard).
    - Long press (hold >= 5s): return device to pairing/searching state (restart BLE advertising).
  - The firmware should debounce the input and implement the 5s hold detection in software.

## Software Architecture

Requirements and preferences:

- Advertise the standard BLE-MIDI service only. Do not expose a custom characteristic for event transport.
- Single client support only.
- Forward a user-selected subset of MIDI channels (default to channel 1).
- Millisecond resolution timestamps.
- Store sequence statistics on the client device (last N sequences, user configurable, N < 20). Statistics include count, mean velocity and variance (or stdev).

Top-level components (files/modules):

- `main.py` — bootstrap, configuration load/save, task scheduler and watchdog. Initializes UART, BLE, and the main processing loop.
- `midi.py` — low-level UART receiver + MIDI parser. Implements a small ring buffer (max depth of 64 TX events), running-status handling, and emits parsed events (Note On/Off) with timestamps. Note sequences do not need to persist across power cycles.
- `ble_midi.py` — BLE GATT server and MIDI transport layer. Hosts the BLE MIDI Service (standard MIDI over GATT) and exposes a `midi_tx()` API to forward packets to a single connected client. Must support packing multiple parsed events into a single BLE‑MIDI notification (respecting MTU) to improve efficiency during bursts. Use the Device Information Service (DIS) to expose static device metadata (manufacturer, model, firmware revision).
- `config.py` — persistent settings (device name, advertise/visibility, practice thresholds, selected channel filter, sequence timeout) stored in flash as a small JSON file. Recommended safe defaults:
  - `device_name`: "MK Monitor"
  - `advertise`: true
  - `channel_filter`: [0]  # default to channel 1 (0 in zero-based)
  - `sequence_timeout_ms`: 4000
  - `max_ringbuf_bytes`: 256
  - `max_tx_queue_events`: 64
- `util/ringbuf.py` — tiny ring buffer helper used by UART IRQ-safe code. The buffer should have a maximum depth of 256 bytes.
- `tests/` (host Python) — parser unit tests and message format verification (run off-device during development).

Flow:

- Boot: `main.py` powers up, loads `config.py`, configures UART0 at 31250 baud and initializes BLE advertising as a MIDI-capable peripheral.
- UART ingest: `midi.py` reads raw bytes from UART into a small ring buffer. Reads are done in a non-blocking loop (or via lightweight IRQ) to minimize latency.
- Parsing: a dedicated parser consumes bytes from the ring buffer, handles running status and stream glitches, and produces canonical events: `{ type: "note_on"/"note_off", channel: 0-15, note: 0-127, velocity: 0-127, ts_ms: <millis> }`. Note On with velocity 0 is normalized to Note Off.
- Queueing: parsed events are enqueued to a short TX queue to decouple BLE transmission from UART parsing.
- Transport: `ble_midi.py` serializes events into BLE MIDI GATT packets and writes them to the MIDI Data Characteristic. To reduce overhead during bursts the implementation should pack multiple events into a single BLE-MIDI notification up to the MTU. Use the DIS for static metadata; optionally enable a debug-only diagnostics characteristic (compile-time/config flag) for runtime stats when troubleshooting (disabled in release builds).
- Client update: the mobile Flutter client receives BLE packets and updates the UI in real time. On disconnect, BLE advertising resumes and any unsent events are dropped or optionally buffered (configurable).

This flow prioritizes minimal buffering and a single-threaded event loop to keep end-to-end latency low.

## MIDI Parser Requirements

- Accept raw MIDI bytes and parse into messages per the MIDI spec (handle running status, 0x80..0xEF channel messages).
- At minimum, support Note On (0x9n) and Note Off (0x8n). Interpret Note On with velocity 0 as Note Off.
- Extract channel (0–15), note number (0–127), and velocity (0–127).
- Timestamp each event (millisecond resolution if available).

## Message Format (device → BLE client)

Primary (recommended): BLE MIDI (MIDI over GATT)

- Use the standard BLE MIDI Service UUID (03B80E5A-EDE8-4B33-A751-6CE34EC4C700) and the MIDI Data Characteristic (7772E5DB-3868-4112-A1A9-F2669D106BF3). Packets conform to the BLE MIDI spec so compatible MIDI-over-BLE clients can interoperate.
- Pack a parsed event as a minimal MIDI message inside a BLE-MIDI event packet so the mobile client can consume it with existing BLE MIDI decoding logic.

Optional formats are intentionally omitted for event transport to maintain BLE-MIDI compatibility. Use the BLE-MIDI GATT transport exclusively for parsed events. For debugging only, JSON payloads may be available via a debug endpoint over USB-serial or a debug BLE characteristic when compiled with debugging enabled.

## Mobile App (UI) Requirements

- Show connection status to BLE MIDI device
- Real-time velocity display for every Note On received.
- Visualizations:
  - Big numeric velocity and bar that animates with key presses.
  - Rolling graph or sparkline of recent velocities (last N presses).
  - Optional per-note indicator or piano keyboard graphic showing velocities per key.
- Practice features (initial):
  - Target velocity band visualization (user sets dynamics target like "pp", "p", "mp", etc. and sees whether each press is inside the band).
  - Sequence logging: have a mode to start a sequence collection on first key press, then stop when no key has been pressed for 4 seconds, then collect and display stats (count, mean, stdev of velocities).
- Settings and configuration:
  - separate settings page to update configuration
  - store the user preferences on the device, no network connection required

Mobile client tech notes:

- Use Flutter / Dart for development.
- BLE library recommendation: `flutter_reactive_ble` (robust Android BLE behavior and MTU/notification control).
- Implement canonical BLE‑MIDI parsing in the app to remain compatible with other BLE MIDI devices; additionally provide a thin wrapper to map parsed MIDI events into the velocity model used by the UI.
- Use `music_notes` (or equivalent) for storing/manipulating musical note data.
- Use a WebView with VexFlow only for optional sheet-music rendering; prefer native Flutter widgets for the real-time velocity views for lowest UI latency.

## Reliability and Edge Cases

- Handle MIDI byte stream glitches and running status.
- Gracefully handle BLE disconnects and resume advertising.
- Avoid large persistent buffers on the device; drop oldest events when TX queue is full to keep latency predictable.
- Provide a debug build mode that exposes additional diagnostics (uptime, free heap, queue depths) over USB-serial and optionally a debug BLE characteristic (disabled in production).

## Performance Considerations

- Use buffering for UART reads (small ring buffer). Process MIDI bytes in an interrupt-safe or non-blocking loop.

## Testing Plan

- Test the mobile app with dummy data (no BLE connection required) to show a simulated stream of key presses with different velocities.
- Unit test MIDI parser logic in host Python (simulate byte streams). Verify running status, Note On with velocity 0 as Note Off, channel filtering, and timestamping. Add a host-side harness to feed raw byte sequences and verify canonical events and ordering.
- Integration test on Pico W: connect a known MIDI source (keyboard) and verify messages appear on a mobile client.
- Latency measurement: add an optional round-trip ping test (app sends a timestamped ping, device echoes; app measures RTT) to quantify end-to-end latency on target Android devices.
- Stress test: simulate bursty input (e.g., dense chords) and confirm the device packs multiple events per BLE notification, maintains predictable latency, and drops oldest events if queues fill.

## Acceptance Criteria (for v0.2)

- Device reliably parses Note On/Off and sends MIDI over BLE to connected clients.
- Device is discoverable and connectable as a BLE MIDI device
- Mobile UI displays velocity in real time with an updating bar and numeric velocity.

## File/Directory Layout (recommended)

- `firmware/`
  - `main.py` — bootstrap and orchestrator
  - `midi.py` — UART + MIDI parser
  - `ble_midi.py` — BLE GATT server and MIDI transport layer
  - `config.py` — persistent device settings and defaults
  - `util/`
    - `ringbuf.py` — small IRQ-safe ring buffer used by UART ingest
  - `tests/` — parser unit tests and integration helpers (host-side and device-side where possible)
- `app/`
  - `pubspec.yaml` — Flutter package manifest
  - `lib/main.dart` — app entry and route setup
  - `lib/ble_service.dart` — BLE scanning, connection, and characteristic handling (supports BLE-MIDI and custom compact characteristic)
  - `lib/velocity_view.dart` — velocity bar, numeric display, sparkline and per-note visualization widgets
  - `lib/models.dart` — simple data models for parsed events and sequences
  - `test/` — Flutter widget/unit tests and a dummy BLE stream simulator

## Next Steps

1. Review this specification and provide edits or approval.
2. After approval, scaffold the app files and minimal UI.
3. Implement and test the mobile client with simulated data. Review and modify design elements as required and get approval before continuing.
4. Implement and test `midi.py` with simulated MIDI streams, then with the keyboard through the proper opto‑isolator input.

---
End of spec (draft)
