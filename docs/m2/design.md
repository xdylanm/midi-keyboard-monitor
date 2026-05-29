# Milestone M2 Design

## Purpose
This document defines the engineering design for Milestone M2 from the PRD: MIDI Ingestion Abstraction.

M2 objective:
- Define a single `MidiSource` abstract interface through which all upstream code receives MIDI events.
- Implement `UsbMidiAdapter` for class-compliant USB MIDI devices using `python-rtmidi`.
- Implement `BleAdapter` connecting to the project's BLE dongle using the standard BLE-MIDI 1.0 protocol.
- Verify that both adapters emit identical normalized `MidiEvent` streams for the same physical performance.

## Scope
In scope:
- `MidiSource` abstract base class and associated exception hierarchy.
- `UsbMidiAdapter` for real-time USB MIDI input.
- `BleAdapter` for real-time BLE-MIDI input from the project dongle.
- Device enumeration for USB ports; device discovery by service UUID for BLE.
- BLE-MIDI 1.0 packet parser.
- Automated tests using mock transport layers.
- Manual test procedures for real hardware.

Out of scope:
- FastAPI / REST server (M6).
- React / OSMD UI (M3).
- Quantization, transcription, or scoring (M4+).
- Performance capture session management (M4).
- Tauri packaging (M7).

---

## Architecture

### MidiSource Abstract Interface

`MidiSource` is an async-lifecycle abstract base class. All upstream code that consumes MIDI events (transcription, analytics, UI bridge) depends only on this interface and never on transport-specific adapters.

```
┌──────────────────────────────────────┐
│         MidiSource (ABC)             │
│                                      │
│  + connect() -> None (async)         │
│  + disconnect() -> None (async)      │
│  + is_connected() -> bool            │
│  + register_callback(fn)             │
│  + list_devices() -> list[DeviceInfo]│
│    (async instance method)           │
└──────────┬──────────────┬────────────┘
           │              │
┌──────────▼──────┐  ┌───▼────────────┐
│ UsbMidiAdapter  │  │   BleAdapter   │
│ (python-rtmidi) │  │   (bleak)      │
└─────────────────┘  └────────────────┘
```

#### Callback Protocol

After `connect()` returns successfully, the adapter invokes the registered callback for each received MIDI event:

```python
def on_event(event: MidiEvent) -> None: ...
```

The callback is always invoked on the event loop thread (adapters must bridge thread callbacks to async context where needed). The callback must not block; callers that require queuing should wrap it.

#### Lifecycle Contract

| State | Precondition | Postcondition |
|---|---|---|
| `connect()` success | Device reachable | `is_connected()` returns `True`; callbacks begin firing |
| `connect()` failure | Device not found or connection refused | Raises `MidiSourceError` subclass; `is_connected()` remains `False` |
| `disconnect()` | Any state | `is_connected()` returns `False`; no more callbacks |
| Device drops mid-session | Connected | Adapter fires disconnect callback if registered; `is_connected()` returns `False`; no crash |

#### DeviceInfo

`list_devices()` returns a list of `DeviceInfo` objects:

```python
@dataclass
class DeviceInfo:
    name: str            # device name; pass to connect() to select this device
    address: str | None  # Bluetooth MAC for BLE adapters; None for USB
```

Callers use `DeviceInfo.name` to identify and connect to a specific device. `DeviceInfo.address` provides the Bluetooth MAC address for BLE adapters (for display or logging); it is `None` for USB adapters, which use port indices rather than network addresses.

---

### UsbMidiAdapter

**Library**: `python-rtmidi`

#### Device Enumeration

```python
UsbMidiAdapter.enumerate_devices() -> list[str]  # static, synchronous
```

Returns the list of available USB MIDI input port names as reported by rtmidi. An empty list indicates no MIDI devices are connected or no driver is available.

The `MidiSource.list_devices()` instance method wraps this and returns `list[DeviceInfo]` with `address=None` (USB ports have no network address). Callers that only need port names for display can use `enumerate_devices()` directly; callers working through the abstract interface use `list_devices()`.

#### Connection

```python
adapter = UsbMidiAdapter(port_name="My Keyboard")
await adapter.connect()
```

If `port_name` is `None`, the adapter selects the first available port. If no matching port exists, raises `DeviceNotFoundError`.

#### MIDI Message Parsing

rtmidi delivers raw MIDI bytes to a thread callback:

```python
def _rtmidi_callback(self, message_and_delta, data=None):
    message, delta_time_s = message_and_delta
    ...
```

The adapter converts raw bytes to `MidiEvent` as follows:

| MIDI Status | Event type | Data bytes |
|---|---|---|
| `0x8n` (Note Off) | `note_off` | note, velocity |
| `0x9n` + velocity > 0 | `note_on` | note, velocity |
| `0x9n` + velocity == 0 | `note_off` | note, velocity=0 |
| `0xAn` | `other` | — |
| `0xBn` | `control_change` | controller, value |
| `0xCn` | `program_change` | program, — |
| `0xDn` | `other` | — |
| `0xEn` | `pitch_bend` | LSB, MSB |
| All other status | `other` | — |

`timestamp_ms` is set from the adapter's monotonic clock at the moment the callback fires (not from the rtmidi delta-time accumulator, which can drift across long sessions).

`timestamp_ticks` is set to `0` for real-time events (no tick context exists; ticks are a file-based concept from M1 MIDI I/O).

#### Thread Safety

rtmidi fires callbacks on a background thread. The adapter bridges to the asyncio event loop using `loop.call_soon_threadsafe()` to enqueue events on an internal `asyncio.Queue`, which is then drained by an internal async task and passed to the registered callback on the event loop thread.

---

### BleAdapter

**Library**: `bleak` (cross-platform BLE for desktop Python — Linux/BlueZ, Windows/WinRT, macOS/CoreBluetooth)

#### Discovery

```python
BleAdapter.enumerate_devices(timeout_s=5.0) -> list[str]  # static async, names only
```

Scans for BLE advertisements containing the BLE-MIDI service UUID (`03B80E5A-EDE8-4B33-A751-6CE34EC4C700`) and returns a list of advertisement names.

The `MidiSource.list_devices()` instance method performs the same scan and returns `list[DeviceInfo]` with both `name` and `address` (Bluetooth MAC) populated. Use `enumerate_devices()` for a quick name list; use `list_devices()` when the address is needed for display or logging.

#### Connection

```python
adapter = BleAdapter(device_name="MK Monitor", require_midi_service=True)
await adapter.connect()
```

Connects to the first device whose advertisement name matches `device_name` (or, if `device_name` is `None`, to the first device found). By default (`require_midi_service=True`), only devices advertising the BLE-MIDI service UUID are considered during scanning; set `require_midi_service=False` to accept any device matching the name regardless of advertised services (useful for debugging non-standard firmware). Subscribes to MIDI characteristic notifications on `7772E5DB-3868-4112-A1A9-F2669D106BF3`. Raises `DeviceNotFoundError` if no matching device is found within the scan timeout.

#### BLE-MIDI 1.0 Packet Format

Each BLE notification is a variable-length BLE-MIDI packet containing one or more MIDI events. The packet layout follows the MIDI Association BLE-MIDI 1.0 specification.

```
Byte 0:  Header          [ 1 1 T12 T11 T10 T9 T8 T7 ]
                           ↑ ↑ └───── timestamp high (6 bits) ──┘
                           always set

For each event in the packet:
  Byte N:   Timestamp    [ 1 0 T6 T5 T4 T3 T2 T1 T0 ]
                           ↑ └───── timestamp low (7 bits) ────┘
                           always set
  Byte N+1: MIDI Status  (standard MIDI status byte, bit 7 = 1; may be omitted under running status)
  Byte N+2+: MIDI Data   (0–2 bytes depending on message type)
```

**Full 13-bit timestamp reconstruction**:

```python
timestamp_high = header_byte & 0x3F          # bits 5-0 of header
timestamp_low  = timestamp_byte & 0x7F       # bits 6-0 of timestamp byte
timestamp_13bit = (timestamp_high << 7) | timestamp_low   # milliseconds, wraps at 8192 ms
```

This 13-bit timestamp is used to order multiple events within a single notification (if the packet is packed with more than one event). The adapter assigns `timestamp_ms` from the local monotonic clock at the time the notification arrives, adjusted by the intra-packet relative offset when multiple events are packed together.

**Running status**: Within a single BLE-MIDI packet, the MIDI status byte may be omitted for successive events with the same status. The parser tracks the last seen status byte and applies it when the next byte is a timestamp byte (bit 7 = 1, bit 6 = 0) rather than a status byte (bit 7 = 1, bit 6 = 1 is a new header — invalid mid-packet; any value with bit 7 = 0 is data).

**Malformed packets**: If a packet cannot be parsed (unexpected byte sequence, truncation), the adapter logs a warning and discards the packet. It does not raise an exception or halt the event stream.

#### Disconnect Handling

The adapter monitors the BLE connection via bleak's disconnected callback. On unexpected disconnect:
- `is_connected()` immediately returns `False`.
- An optional disconnect callback (registered separately) is invoked.
- The adapter does not attempt automatic reconnection in M2; callers must call `connect()` again.

---

### Exception Hierarchy

```
MidiSourceError (base, RuntimeError)
├── DeviceNotFoundError   — no port/device matching the request
├── MidiConnectionError   — device found but connection failed or was refused
└── PacketParseError      — BLE packet malformed (logged, not propagated to caller)
```

`PacketParseError` is caught internally in `BleAdapter` and logged; it is not propagated to the caller's callback. The other two are raised from `connect()`.

---

### Package Layout

New files added in M2:

```
core/
  io/
    midi_source.py          # MidiSource ABC + exception hierarchy
    usb_midi_adapter.py     # UsbMidiAdapter
    ble_adapter.py          # BleAdapter
tests/
  m2/
    __init__.py
    helpers.py              # shared mock helpers (fake rtmidi, fake bleak client)
    test_usb_adapter.py     # USB adapter unit tests
    test_ble_adapter.py     # BLE adapter unit tests
    test_midi_source_contract.py  # shared interface contract tests, parametrized
```

Existing files modified in M2:

- `requirements.txt` — add `python-rtmidi`, `bleak`
- `core/io/__init__.py` — export new symbols

---

## Async Design Notes

Both adapters implement the same `async def connect()` / `async def disconnect()` lifecycle so callers do not need to know which transport is active. Internally:

- **UsbMidiAdapter**: rtmidi is thread-based. The adapter spawns no threads explicitly; rtmidi manages its own callback thread. Events are bridged to asyncio via `loop.call_soon_threadsafe` into an internal `asyncio.Queue`, then drained by a long-running `asyncio.Task` started in `connect()` and cancelled in `disconnect()`.

- **BleAdapter**: bleak is natively async. The GATT notification callback fires on the asyncio event loop. No additional threading bridge is required.

UsbMidiAdapter captures the running event loop at `connect()` time via `asyncio.get_running_loop()`, which raises `RuntimeError` immediately if called outside an async context, making misuse obvious rather than silent. BleAdapter does not capture the loop explicitly — bleak manages its own async context.

---

## Automated Test Design

Tests must not require physical hardware. All hardware interaction is replaced by mock objects.

### Test Group A: UsbMidiAdapter — MIDI Byte Parsing

Inject raw MIDI byte sequences directly into the adapter's internal `_parse_message()` method and assert correct `MidiEvent` output.

| Test case | Input bytes | Expected MidiEvent |
|---|---|---|
| Note On | `[0x90, 60, 80]` | type=note_on, channel=0, note=60, velocity=80 |
| Note Off explicit | `[0x80, 62, 0]` | type=note_off, channel=0, note=62, velocity=0 |
| Note On vel=0 → Note Off | `[0x90, 64, 0]` | type=note_off, channel=0, note=64, velocity=0 |
| Control Change | `[0xB0, 7, 100]` | type=control_change, channel=0, note=None, velocity=None |
| Pitch Bend | `[0xE0, 0, 64]` | type=pitch_bend, channel=0, note=None, velocity=None |
| Channel 3 Note On | `[0x93, 48, 64]` | type=note_on, channel=3, note=48, velocity=64 |
| Unknown status | `[0xF0, ...]` | type=other |

### Test Group B: UsbMidiAdapter — Lifecycle

Mock `rtmidi.MidiIn` to control port enumeration and open/close behavior.

| Test case | Setup | Expected outcome |
|---|---|---|
| enumerate_devices returns port names | Mock reports 2 ports | Returns list of 2 strings |
| list_devices returns DeviceInfo objects | Mock reports 2 ports | Returns list of 2 `DeviceInfo` with `address=None` |
| connect to named port | Port exists in mock | `is_connected()` = True after await |
| connect to missing port | No ports in mock | Raises `DeviceNotFoundError` |
| disconnect stops events | Connected, then disconnect | Callback not called after disconnect |
| connect None → first port | Multiple ports in mock | Connects to first available |

### Test Group C: BleAdapter — Packet Parser

Test the BLE-MIDI packet parsing function in isolation with raw byte sequences.

| Test case | Packet bytes | Expected MidiEvents |
|---|---|---|
| Single Note On | `[0xC0, 0x80, 0x90, 60, 80]` | 1×note_on ch=0 note=60 vel=80 |
| Single Note Off | `[0xC0, 0x80, 0x80, 60, 0]` | 1×note_off ch=0 note=60 vel=0 |
| Packed two events | `[0xC0, 0x80, 0x90, 60, 80, 0x81, 0x90, 62, 64]` | note_on ch=0 note=60, note_on ch=0 note=62 |
| Running status | `[0xC0, 0x80, 0x90, 60, 80, 0x81, 62, 64]` | note_on ch=0 note=60, note_on ch=0 note=62 (status omitted) |
| Timestamp reconstruction | Header bits 5-0=1, TS bits 6-0=5 | 13-bit ts = (1<<7)\|5 = 133 ms |
| Malformed (truncated) | `[0xC0, 0x80, 0x90]` | No events emitted; no exception raised |

### Test Group D: BleAdapter — Lifecycle

Mock `bleak.BleakClient` and `bleak.BleakScanner`.

| Test case | Setup | Expected outcome |
|---|---|---|
| enumerate_devices finds dongle | Scanner reports one BLE-MIDI device | Returns list with device name |
| list_devices returns DeviceInfo with address | Scanner reports one BLE-MIDI device | Returns `DeviceInfo` with name and Bluetooth MAC |
| connect by name | Scanner finds "MK Monitor" | `is_connected()` = True after await |
| connect device not found | Scanner finds nothing | Raises `DeviceNotFoundError` |
| connect skips non-BLE-MIDI device (require_midi_service=True) | Scanner finds device without BLE-MIDI UUID | Raises `DeviceNotFoundError` |
| connect accepts any device (require_midi_service=False) | `require_midi_service=False`, scanner finds non-MIDI device | `is_connected()` = True |
| notification → MidiEvent | Inject notification bytes via mock | Callback receives correct `MidiEvent` |
| unexpected disconnect | Trigger bleak disconnected callback | `is_connected()` = False; disconnect callback fired |

### Test Group E: MidiSource Contract (Parametrized)

Both `UsbMidiAdapter` and `BleAdapter` must satisfy the shared `MidiSource` interface contract. Parametrize the following tests over both adapter types using a mock transport:

| Contract test | Assertion |
|---|---|
| Interface completeness | Adapter exposes `connect`, `disconnect`, `is_connected`, `register_callback`, `list_devices` |
| `list_devices` returns DeviceInfo | Call before connect → returns `list[DeviceInfo]` with at least one entry |
| Callback fires after connect | Note On injected → callback called with `MidiEvent(type="note_on")` |
| Callback not fired before connect | Injected message before `connect()` → callback not called |
| Callback not fired after disconnect | Connect → disconnect → inject message → callback not called |
| `is_connected` accurate | Reflects connection state through full lifecycle |

---

## Manual Test Procedures

### Manual Test 1 — USB MIDI Input (Real Keyboard)

**Goal**: Verify `UsbMidiAdapter` receives note events from a real USB MIDI keyboard.

**Setup**: Plug a USB MIDI keyboard into the development machine. Ensure `python-rtmidi` is installed and the device appears in `UsbMidiAdapter.enumerate_devices()`.

**Steps**:
1. Run the manual test script `test/m2/usb_input_test.py` (to be created in M2).
2. The script calls `enumerate_devices()` and prints the port list.
3. It connects to the first port and prints each `MidiEvent` as it arrives.
4. Play a C major scale (C4–G4–C5) with distinct velocities.
5. Press Ctrl+C to stop.

**Expected output**:
- Port list is non-empty and includes the keyboard name.
- Each key press produces a `MidiEvent` with type `note_on`, correct MIDI note number, and a non-zero velocity.
- Each key release produces a matching `note_off` event.
- No crashes or unhandled exceptions.

**Acceptance evidence**: Paste the printed event log (first ~20 events) into the PR notes.

---

### Manual Test 2 — BLE MIDI Input (Dongle)

**Goal**: Verify `BleAdapter` receives note events from the BLE dongle.

**Setup**: Power on the BLE dongle (Raspberry Pi Pico W running the project firmware). Confirm it advertises "MK Monitor". Ensure `bleak` is installed.

**Steps**:
1. Run `test/m2/ble_input_test.py`.
2. The script calls `enumerate_devices()` and prints discovered BLE-MIDI devices.
3. It connects to "MK Monitor" and prints each `MidiEvent` as it arrives.
4. Play the same C major scale used in Manual Test 1.
5. Press Ctrl+C to stop.

**Expected output**:
- "MK Monitor" appears in the device list.
- `MidiEvent` note numbers and velocities match those recorded in Manual Test 1 within the expected timestamp tolerance (no tolerance constraint on absolute `timestamp_ms`, but event ordering must be preserved).
- No crashes or unhandled exceptions on connect or on CTRL+C disconnect.

**Acceptance evidence**: Paste the printed event log into the PR notes alongside Manual Test 1 output to confirm note-for-note equivalence.

---

### Manual Test 3 — Disconnect Resilience

**Goal**: Confirm the adapter handles unexpected disconnect gracefully.

**Steps**:
1. Connect via BLE adapter (as in Manual Test 2) and verify events are flowing.
2. Power off the BLE dongle while the script is running.
3. Observe that the adapter logs a disconnect message and `is_connected()` returns `False`.
4. Confirm the script does not crash or raise an unhandled exception.

**Expected output**:
- Disconnect event is printed.
- Script exits cleanly or prompts the user.
- No traceback.

---

## Dependencies

New runtime dependencies introduced in M2:

| Package | Purpose | Min version |
|---|---|---|
| `python-rtmidi` | Real-time USB MIDI input | 1.5+ |
| `bleak` | Cross-platform BLE client | 0.21+ |

New test dependencies:

| Package | Purpose |
|---|---|
| `pytest-asyncio` | `async def` test functions in pytest |

`python-rtmidi` requires system-level ALSA headers on Linux (`libasound2-dev`) and is a pre-built wheel on Windows.
