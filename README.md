# MKM — Core Music Trainer

A cross-platform piano practice application with MIDI transcription, sheet music display and light editing, performance accuracy analytics, and a dual agent interface (REST + MCP-compatible tools).

## Platform targets

- **Ubuntu desktop** and **Windows 11 desktop/laptop** — browser-first, later packaged with Tauri.
- **Android** — optional web-browser client in a future release; no native app in v1.

## Architecture summary

- **Core**: Python 3.11 service layer (FastAPI, music21, mido, librosa, python-rtmidi).
- **UI**: React frontend served locally; score rendering via OpenSheetMusicDisplay (VexFlow/MusicXML).
- **Packaging**: browser-first → Tauri desktop shell once workflows stabilize.
- **Agent interfaces**: REST API (OpenAPI) and MCP-compatible tool adapter over the same internal service contract.
- **MIDI input**: abstract `MidiSource` interface supports the project's BLE dongle and any USB class-compliant MIDI device.
- **Future**: Rust core replacement via stable API contract; UI and agent interfaces unchanged.

## Hardware and firmware

The hardware (KiCad PCB) and firmware (MicroPython BLE MIDI dongle) are unchanged and out of scope for this development track. See [docs/assembly.md](docs/assembly.md) and [docs/firmware-spec.md](docs/firmware-spec.md).

## Documentation

- **[docs/development-plan.md](docs/development-plan.md)** — Product Requirements Document (authoritative).
- [docs/dynamics-tracking.md](docs/dynamics-tracking.md) — Legacy dynamics-tracking spec (historical reference only).
- [docs/design.md](docs/design.md) — Hardware design notes.
- [docs/firmware-spec.md](docs/firmware-spec.md) — BLE MIDI firmware specification.

## Flutter prototype (legacy)

The `app/` directory contains a Flutter/Android prototype from the earlier dynamics-tracking phase. It is retained as a reference for BLE-MIDI packet parsing and dynamics scoring logic but is not the active development path. See [app/README.md](app/README.md).
