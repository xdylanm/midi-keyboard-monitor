# Milestone M2 Tasks Checklist

Use this checklist to track implementation and validation progress for M2.

## 1) Project Structure and Dependencies

- [x] Create `tests/m2/` package: add `__init__.py`.
- [x] Add `python-rtmidi` to `requirements.txt`.
- [x] Add `bleak` to `requirements.txt`.
- [x] Add `pytest-asyncio` to `requirements.txt` (or test dependencies section).
- [ ] Confirm `libasound2-dev` is documented as a required system package for Linux (add to README or setup docs).
- [x] Create manual test script stubs in `test/m2/`: `usb_input_test.py`, `ble_input_test.py`.

## 2) MidiSource Abstract Interface and Exceptions

- [x] Create `core/io/midi_source.py`.
- [x] Define `MidiSourceError(RuntimeError)` base exception.
- [x] Define `DeviceNotFoundError(MidiSourceError)`.
- [x] Define `MidiConnectionError(MidiSourceError)`.
- [x] Define `PacketParseError(MidiSourceError)` (internal use only in BleAdapter).
- [x] Define `MidiSource` ABC with:
  - [x] `async def connect(self) -> None`
  - [x] `async def disconnect(self) -> None`
  - [x] `def is_connected(self) -> bool`
  - [x] `def register_callback(self, callback: Callable[[MidiEvent], None]) -> None`
  - [x] `async def list_devices(self) -> list[DeviceInfo]` (abstract instance method)
- [x] Define `DeviceInfo` dataclass (`name: str`, `address: str | None`).
- [x] Export `MidiSource`, `DeviceInfo`, and exception classes from `core/io/__init__.py`.

## 3) UsbMidiAdapter

- [x] Create `core/io/usb_midi_adapter.py`.
- [x] Implement `UsbMidiAdapter(MidiSource)` class.
- [x] Implement `enumerate_devices()` using `rtmidi.MidiIn().get_ports()`.
- [x] Implement `list_devices() -> list[DeviceInfo]`: wraps `enumerate_devices()`, sets `address=None` for each port.
- [x] Implement `connect(port_name=None)`:
  - [x] Resolve port name to port index; raise `DeviceNotFoundError` if not found.
  - [x] Open the rtmidi port.
  - [x] Register the internal rtmidi callback.
  - [x] Start the internal asyncio drain task.
  - [x] Set `_connected = True`.
- [x] Implement `disconnect()`:
  - [x] Cancel the drain task.
  - [x] Close and delete the rtmidi port.
  - [x] Set `_connected = False`.
- [x] Implement `is_connected()`.
- [x] Implement internal `_rtmidi_callback(message_and_delta, data)`:
  - [x] Bridge to asyncio event loop via `loop.call_soon_threadsafe`.
  - [x] Enqueue raw message bytes and local monotonic timestamp on `_queue`.
- [x] Implement internal `_parse_message(message_bytes, timestamp_ms) -> MidiEvent | None`:
  - [x] Handle `0x8n` → `note_off`.
  - [x] Handle `0x9n` velocity > 0 → `note_on`.
  - [x] Handle `0x9n` velocity == 0 → `note_off`.
  - [x] Handle `0xBn` → `control_change`.
  - [x] Handle `0xCn` → `program_change`.
  - [x] Handle `0xEn` → `pitch_bend`.
  - [x] Handle all other status → `other`.
  - [x] Set `timestamp_ticks = 0` for all real-time events.
- [x] Implement internal `_drain_task()` (async): drain `_queue`, parse messages, fire registered callback.
- [x] Guard all rtmidi imports behind a try/except so import failure produces a clear message.

## 4) BleAdapter

- [x] Create `core/io/ble_adapter.py`.
- [x] Implement `BleAdapter(MidiSource)` class.
- [x] Implement `enumerate_devices(timeout_s=5.0)` using `bleak.BleakScanner.discover()`, filtering by BLE-MIDI service UUID; returns advertisement names.
- [x] Implement `list_devices() -> list[DeviceInfo]`: async scan filtered by BLE-MIDI UUID; populates both `name` and `address` (Bluetooth MAC) in each `DeviceInfo`.
- [x] Implement `connect(device_name=None, timeout_s=10.0, require_midi_service=True)`:
  - [x] Scan for device; when `require_midi_service=True` (default), skip devices not advertising the BLE-MIDI service UUID.
  - [x] When `require_midi_service=False`, accept any device matching the name regardless of advertised UUIDs.
  - [x] Raise `DeviceNotFoundError` if no matching device is found.
  - [x] Create `bleak.BleakClient` and call `await client.connect()`.
  - [x] Subscribe to MIDI characteristic notifications: `await client.start_notify(MIDI_CHAR_UUID, _notification_handler)`.
  - [x] Register bleak disconnected callback.
  - [x] Set `_connected = True`.
- [x] Implement `disconnect()`:
  - [x] Unsubscribe notifications and call `await client.disconnect()`.
  - [x] Set `_connected = False`.
- [x] Implement `is_connected()`.
- [x] Implement `_notification_handler(handle, data: bytearray)`:
  - [x] Record monotonic timestamp at entry.
  - [x] Call `_parse_ble_midi_packet(data, base_timestamp_ms)`.
  - [x] For each resulting `MidiEvent`, invoke the registered callback.
- [x] Implement `_parse_ble_midi_packet(data, base_timestamp_ms) -> list[MidiEvent]`:
  - [x] Read header byte; validate bit 7 = 1 and bit 6 = 1; extract timestamp high bits.
  - [x] Iterate remaining bytes:
    - [x] Detect timestamp bytes (bit 7 = 1, bit 6 = 0); extract timestamp low bits; reconstruct 13-bit packet timestamp.
    - [x] Detect status bytes (bit 7 = 1, bit 6 not flagging timestamp); apply running status.
    - [x] Collect data bytes (bit 7 = 0).
    - [x] When a complete message (status + correct number of data bytes) is assembled, emit a `MidiEvent` with `timestamp_ms = base_timestamp_ms`.
  - [x] On parse error: catch internally, log warning, return events collected so far (do not raise).
  - [x] Apply same `note_on` / `note_off` / `control_change` / `pitch_bend` / `program_change` / `other` mapping as `UsbMidiAdapter`.
  - [x] Set `timestamp_ticks = 0` for all real-time events.
- [x] Implement `_on_disconnect(client)`:
  - [x] Set `_connected = False`.
  - [x] Invoke disconnect callback if registered (optional disconnect callback hook).
- [x] Guard all bleak imports behind a try/except so import failure produces a clear message.

## 5) Automated Test Suite

### Test module: `tests/m2/helpers.py`
- [x] Implement `FakeRtMidiIn` mock class:
  - [x] `get_ports()` returns a configurable list.
  - [x] `open_port()` records the opened port index.
  - [x] `set_callback()` stores the callback.
  - [x] `inject_message(bytes, delta_time)` manually fires the stored callback.
  - [x] `close_port()` marks port closed.
- [x] Implement `FakeBleakScanner` mock:
  - [x] `discover()` returns a configurable list of `BLEDevice`-like objects.
- [x] Implement `FakeBleakClient` mock:
  - [x] `connect()` / `disconnect()` set connected flag.
  - [x] `start_notify()` stores the notification handler.
  - [x] `inject_notification(data: bytearray)` fires the stored handler.
  - [x] `is_connected` property.

### Test module: `tests/m2/test_usb_adapter.py`
- [x] Test Group A — MIDI byte parsing (all cases from design doc).
  - [x] Note On `[0x90, 60, 80]` → `MidiEvent(type="note_on", channel=0, note=60, velocity=80)`.
  - [x] Note Off explicit `[0x80, 62, 0]` → `MidiEvent(type="note_off", ...)`.
  - [x] Note On velocity=0 → `note_off`.
  - [x] Control Change `[0xB0, 7, 100]` → `MidiEvent(type="control_change", note=None, velocity=None)`.
  - [x] Pitch Bend `[0xE0, 0, 64]` → `MidiEvent(type="pitch_bend", note=None, velocity=None)`.
  - [x] Channel 3 Note On `[0x93, 48, 64]` → channel=3.
  - [x] Unknown status `[0xF0]` → `MidiEvent(type="other")`.
- [x] Test Group B — Lifecycle (all cases from design doc).
  - [x] `enumerate_devices` returns port names from mock.
  - [x] `list_devices` returns `DeviceInfo` objects with `address=None`.
  - [x] `connect` to named port succeeds → `is_connected()` = True.
  - [x] `connect` with no matching port → `DeviceNotFoundError`.
  - [x] Callback fires after connect when message injected.
  - [x] Callback does not fire after disconnect.
  - [x] `connect(None)` selects first available port.

### Test module: `tests/m2/test_ble_adapter.py`
- [x] Test Group C — BLE-MIDI packet parsing (all cases from design doc).
  - [x] Single Note On packet → 1 `MidiEvent(type="note_on")`.
  - [x] Single Note Off packet → 1 `MidiEvent(type="note_off")`.
  - [x] Packed two-event packet → 2 `MidiEvent` instances in order.
  - [x] Running status packet → status applied to second event.
  - [x] Timestamp reconstruction: header bits and timestamp byte combine correctly to 13-bit value.
  - [x] Truncated/malformed packet → no exception; no events (or partial events up to the error).
- [x] Test Group D — BLE lifecycle (all cases from design doc).
  - [x] `enumerate_devices` returns device name from mock scanner.
  - [x] `list_devices` returns `DeviceInfo` with name and Bluetooth MAC.
  - [x] `list_devices` excludes devices without BLE-MIDI UUID.
  - [x] `connect` by name succeeds → `is_connected()` = True.
  - [x] `connect` with no device found → `DeviceNotFoundError`.
  - [x] `connect` skips non-BLE-MIDI device when `require_midi_service=True` (default) → `DeviceNotFoundError`.
  - [x] `connect` accepts non-BLE-MIDI device when `require_midi_service=False` → `is_connected()` = True.
  - [x] Notification injected → callback receives correct `MidiEvent`.
  - [x] Bleak disconnect callback → `is_connected()` = False; disconnect callback fired.

### Test module: `tests/m2/test_midi_source_contract.py`
- [x] Parametrize over `(UsbMidiAdapter + FakeRtMidi, BleAdapter + FakeBleakClient)`.
- [x] Contract: adapter exposes all required interface members including `list_devices`.
- [x] Contract: `list_devices()` returns `list[DeviceInfo]` with at least one entry.
- [x] Contract: callback fires with `MidiEvent(type="note_on")` after connect and message injection.
- [x] Contract: callback does not fire before `connect()` is called.
- [x] Contract: callback does not fire after `disconnect()`.
- [x] Contract: `is_connected()` is `False` before connect, `True` after connect, `False` after disconnect.

## 6) Manual Validation (Real Hardware)

### Manual Test Script: `test/m2/usb_input_test.py`
- [x] Script prints available USB MIDI ports.
- [x] Script connects to the first port (or a named port from CLI arg).
- [x] Script prints each received `MidiEvent` as it arrives.
- [x] Script handles KeyboardInterrupt cleanly (calls `disconnect()` on exit).

### Manual Test Script: `test/m2/ble_input_test.py`
- [x] Script prints discovered BLE-MIDI devices.
- [x] Script connects to "MK Monitor" (or a name from CLI arg).
- [x] Script prints each received `MidiEvent` as it arrives.
- [x] Script handles KeyboardInterrupt cleanly (calls `disconnect()` on exit).

### Validation Steps
- [x] **Manual Test 1 — USB MIDI**: Connect a USB keyboard, run `usb_input_test.py`, play C major scale, confirm note-on/note-off events appear with correct note numbers and non-zero velocities. Paste event log (≥20 events) in PR notes.
- [ ] **Manual Test 2 — BLE MIDI**: Power on BLE dongle, run `ble_input_test.py`, play the same C major scale, confirm note-for-note equivalent events. Paste event log alongside USB log in PR notes.
- [ ] **Manual Test 3 — Disconnect resilience**: While BLE test script is running, power off the dongle. Confirm disconnect is logged, `is_connected()` returns `False`, and no traceback is printed.

## 7) PRD Acceptance Sign-off for M2

- [ ] **Acceptance #1**: USB and BLE adapters produce note-for-note equivalent `MidiEvent` streams for the same physical performance (verified via Manual Tests 1 and 2, event logs in PR notes).
- [ ] **Acceptance #2**: Disconnecting or failing to connect produces a clear `MidiSourceError` subclass exception without crashing the service (verified via automated lifecycle tests + Manual Test 3).
- [x] All automated tests pass: `pytest tests/m2 -q` — **69 passed in 0.53 s** (May 28 2026).
- [ ] Record final evidence (test output + manual event logs) in PR/commit notes.

---

Recommended test commands:
```
pytest tests/m2 -q
pytest tests/m2/test_usb_adapter.py -q
pytest tests/m2/test_ble_adapter.py -q
pytest tests/m2/test_midi_source_contract.py -q
```
