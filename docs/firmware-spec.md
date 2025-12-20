# MIDI Keyboard Monitor — Firmware Specification

Version: 0.1

Date: 2025-12-19

Author: Drafted for Raspberry Pi Pico W implementation

## Goal

Build a small, low-latency device based on the Raspberry Pi Pico W that connects to the MIDI output of a keyboard, monitors incoming MIDI messages (at least Note On / Note Off and velocity), and hosts a web application which displays the velocity of key presses in real time to assist dynamic practice.

## Constraints and Assumptions
- Target hardware: Raspberry Pi Pico W (RP2040 + CYW43439 Wi‑Fi)
- Firmware language: MicroPython
- Physical MIDI input: standard 5‑pin DIN MIDI (31250 baud, coupled with H11L1 opto‑isolator to RX pin on the Pico W)
- Latency target: end-to-end (key press → web UI update) < 20 ms if possible; acceptable up to ~50 ms.
- Network: Wi‑Fi connectivity; device will host an HTTP server and a WebSocket endpoint for real‑time updates.

## Hardware Interface

1. MIDI Input (required)
   - Use the keyboard's MIDI OUT (5‑pin DIN) wired to an opto‑isolator (standard MIDI input circuit) and then to a UART RX on the Pico.
   - UART settings: 31250 baud, 8 data bits, 1 stop bit, no parity.
   - Connect the opto isolator (H11L1) output to the Pico UART0 RX on GP17.

2. Power
   - Pico W powered via USB or external 5 V regulator.

3. Status
   - Use the on-board LED indicator for network status and MIDI activity.

## Software Architecture

Top-level components (files/modules):
- `main.py` — boot, configuration loader, application orchestrator, fallback AP provisioning.
- `midi.py` — UART interface and MIDI parser. Emits parsed events to an internal queue or callback.
- `webserver.py` — HTTP static file server and WebSocket server for real-time events, plus minimal REST endpoints for status and configuration.
- `config.json` — persistent settings (Wi‑Fi SSID, password, MIDI channel, smoothing settings, server port, calibration).
- `www/` — static web app (HTML/CSS/JS) served by the device.

Flow:
- On boot, `main.py` loads `config.json`. If no Wi‑Fi configured, start AP mode for setup (SSID: `mkm-setup`).
- Start `midi.py` to open UART and begin parsing incoming bytes.
- Start `webserver.py` to host static files and open a WebSocket endpoint `/ws`.
- When `midi.py` emits Note On/Off, create a JSON message and push to connected WebSocket clients.

## MIDI Parser Requirements
- Accept raw MIDI bytes and parse into messages per the MIDI spec (handle running status, 0x80..0xEF channel messages).
- At minimum, support Note On (0x9n) and Note Off (0x8n). Interpret Note On with velocity 0 as Note Off.
- Extract channel (0–15), note number (0–127), and velocity (0–127).
- Timestamp each event (millisecond resolution if available).
- Provide a simple API/callback:
  - on_note_event({type: "note_on"|"note_off", channel, note, velocity, ts})

## Message Format (device → web client)

Send JSON objects over WebSocket with this schema:

{
  "type": "note",
  "event": "note_on" | "note_off",
  "channel": 0,
  "note": 60,
  "velocity": 100,
  "ts": 1700000000
}

Also expose lightweight REST endpoints:
- `GET /api/status` → {wifi: "connected"|"ap", ip: "x.x.x.x", clients: N}
- `GET /api/config` → current config JSON
- `POST /api/config` → update and persist config (Wi‑Fi credentials, MIDI channel filters, smoothing)

## Web App (UI) Requirements
- Real-time velocity display for every Note On received.
- Visualizations:
  - Big numeric velocity and bar that animates with key presses.
  - Rolling graph or sparkline of recent velocities (last N presses).
  - Optional per-note indicator or piano keyboard graphic showing velocities per key.
- Practice features (initial):
  - Target velocity band visualization (user sets dynamics target like "pp", "p", "mp", etc. and sees whether each press is inside the band).
  - Sequence logging: have a mode to start a sequence collection on first key press, then stop when no key has been pressed for 4 seconds, then collect and display stats (count, mean, stdev of velocities).
- Client connects to WebSocket `/ws` for live updates. On connect, optionally request recent history via `GET /api/history` (if implemented).

Web client tech notes:
- Keep client lightweight: vanilla JS or minimal framework. Use WebSocket API in browser.
- Keep assets small for embedded environment.

## Configuration and Calibration
- Configurable items:
  - `wifi.ssid`, `wifi.password`
  - `midi.channel` (0–15) or `all`
  - `smoothing.window` (number of samples for velocity smoothing)
  - `practice.target_level`, `practice.target_accuracy`
  - `server.port`
- Provide UI page to set these and POST `/api/config` to save.

## Persistence
- Store `config.json` in the device filesystem (Flash). Keep size small.
- Optional: store recent session logs (append-only file with timestamped events) with rotation.

## Security
- If device runs in station mode, use WPA2 credentials for joining the user's Wi‑Fi.
- Web UI: no auth initially, but device is only reachable on local network. Consider adding a simple token-based auth if needed later.

## Reliability and Edge Cases
- Handle MIDI byte stream glitches and running status.
- Gracefully handle Wi‑Fi disconnects: try reconnect; if cannot, fallback to AP mode for setup.
- Handle multiple WebSocket clients — broadcast events to all.

## Performance Considerations
- Use buffering for UART reads (small ring buffer). Process MIDI bytes in an interrupt-safe or non-blocking loop.
- Keep message serialization fast; send compact JSON.

## Testing Plan
- Unit test MIDI parser logic in host Python (simulate byte streams). Verify running status, Note On with velocity 0 as Note Off, and channel filtering. Test a synthetic sequence of key presses with velocities within the target band and outside the band.
- Integration test on Pico W: connect a known MIDI source (keyboard) and verify messages appear on a browser client.

## Acceptance Criteria (for v0.1)
- Device reliably parses Note On/Off and sends JSON messages to connected web clients.
- Web UI displays velocity in real time with an updating bar and numeric velocity.
- Wi‑Fi provisioning available via AP fallback.

## File/Directory Layout (recommended)

- `firmware/`
  - `main.py` — bootstrap and orchestrator
  - `midi.py` — UART + MIDI parser
  - `webserver.py` — HTTP + WebSocket server
  - `config.json` — persistent config
  - `www/` — static web app
    - `index.html`
    - `app.js`
    - `styles.css`

## Next Steps
1. Review this specification and provide edits or approval.
2. After approval, scaffold the firmware files and minimal web UI (serve a static page and open `/ws`).
3. Implement and test `midi.py` with simulated MIDI streams, then with the keyboard through the proper opto‑isolator input.

---
End of spec (draft)
